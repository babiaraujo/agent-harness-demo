"""
Agente com harness: Planner / Generator / Evaluator separados,
validacao de schema, retry com feedback estruturado.

Mesmo modelo, mesma task. A diferenca esta toda na arquitetura
em volta da chamada do LLM.
"""

import json
from anthropic import Anthropic
from jsonschema import validate, ValidationError
from rich.console import Console
from rich.table import Table

from tasks import TASKS, SCHEMA, task_ok

client = Anthropic()
MODEL = "claude-haiku-4-5"
MAX_RETRIES = 2
console = Console()


# ----------------------------- planner ------------------------------
def planner(text: str) -> str:
    """
    Traduz o pedido vago num plano explicito.

    Nao gera o output ainda. A separacao importa porque obriga o LLM
    a tornar explicita a ambiguidade ANTES de comprometer com um JSON,
    reduzindo a chance dele "decidir errado em silencio" la na frente.
    """
    msg = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "Voce e um planejador. Dada a descricao de uma vaga, "
                    "liste em bullets o que precisa ser extraido e onde voce "
                    "ve ambiguidade (ex: salario unico vs faixa, cargo composto, "
                    "modalidade implicita). NAO gere o JSON final.\n\n"
                    f"Vaga: {text}"
                ),
            }
        ],
    )
    return msg.content[0].text.strip()


# ----------------------------- generator ----------------------------
def generator(text: str, plan: str, feedback: str = "") -> dict:
    """
    Gera o JSON seguindo o plano. Se ja teve falha numa tentativa
    anterior, recebe o feedback do evaluator pra corrigir.

    O feedback nao e um "tenta de novo": e uma descricao concreta
    do que falhou (schema, regra de negocio, ou verdict do QA),
    o que muda completamente a qualidade da segunda tentativa.
    """
    user_prompt = (
        f"Vaga: {text}\n\n"
        f"Plano: {plan}\n\n"
        "Gere APENAS um JSON com as chaves: cargo, nivel, modalidade, "
        "salario_min, salario_max, stack. Modalidade deve ser exatamente "
        "'remoto', 'hibrido' ou 'presencial'. Salarios em numero (sem 'R$', "
        "sem 'k'), ou null se nao informado."
    )
    if feedback:
        user_prompt += f"\n\nTentativa anterior falhou: {feedback}. Corrija."

    msg = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = msg.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {}


# ----------------------------- evaluator ----------------------------
def evaluator(got: dict, original_text: str) -> tuple[bool, str]:
    """
    Valida o output em tres niveis e retorna (passou, feedback).

    Camada 1 — schema deterministico: barato e infalivel.
    Camada 2 — regras de negocio: o que schema nao pega.
    Camada 3 — QA com LLM contra o texto ORIGINAL, nao contra o que
               o generator alegou ter feito. Esse detalhe e o que
               evita o vies otimista classico de "agente que aprova
               o proprio trabalho".
    """
    # 1. validacao deterministica de schema
    try:
        validate(instance=got, schema=SCHEMA)
    except ValidationError as e:
        return False, f"schema invalido: {e.message}"

    # 2. regra de negocio: salario_min <= salario_max quando ambos existem
    sm, sM = got.get("salario_min"), got.get("salario_max")
    if sm is not None and sM is not None and sm > sM:
        return False, "salario_min maior que salario_max"

    # 3. segunda opiniao do LLM, contra o texto original
    msg = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": (
                    "Voce e um QA independente. Compare o JSON extraido com "
                    "o texto original da vaga e responda APENAS 'OK' se estiver "
                    "fiel, ou 'ERRO: <motivo curto>' se tiver algo errado.\n\n"
                    f"Texto: {original_text}\n\n"
                    f"JSON: {json.dumps(got, ensure_ascii=False)}"
                ),
            }
        ],
    )
    verdict = msg.content[0].text.strip()
    if verdict.upper().startswith("OK"):
        return True, ""
    return False, verdict


# ----------------------------- orquestracao -------------------------
def run(text: str) -> tuple[dict, bool]:
    """
    Roda o ciclo planner -> generator -> evaluator com retry.

    Retorna (dado_extraido, agente_declarou_sucesso). Diferente do
    naive, o harness sabe quando falhou: se estourou MAX_RETRIES sem
    o evaluator aprovar, devolve declared_ok=False. Isso e o ponto:
    um agente de producao TEM que saber quando errou, e nao sair
    declarando sucesso com confianca total.
    """
    plan = planner(text)
    feedback = ""
    got: dict = {}
    for _ in range(MAX_RETRIES + 1):
        got = generator(text, plan, feedback)
        ok, feedback = evaluator(got, text)
        if ok:
            return got, True
    return got, False


def main() -> None:
    console.rule("[bold]harness agent[/bold] — planner / generator / evaluator + retry")

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", justify="right", width=3)
    table.add_column("agente disse")
    table.add_column("realidade")
    table.add_column("detalhe")

    acertos = 0
    falsos_sucessos = 0
    for i, t in enumerate(TASKS, 1):
        got, declared_ok = run(t["input"])
        actual_ok = task_ok(got, t["expected"])
        acertos += int(actual_ok)
        if declared_ok and not actual_ok:
            falsos_sucessos += 1

        disse = "[green]OK[/green]" if declared_ok else "[red]FAIL[/red]"
        real = "[green]OK[/green]" if actual_ok else "[red]FAIL[/red]"
        detalhe = "" if actual_ok else f"esperado={t['expected']} | obtido={got}"
        table.add_row(str(i), disse, real, detalhe)

    console.print(table)
    total = len(TASKS)
    console.print(
        f"\ntaxa de sucesso real: [bold]{acertos}/{total}[/bold] ({100*acertos/total:.0f}%)"
    )
    console.print(
        f"falsos sucessos (agente declarou OK e errou): [bold red]{falsos_sucessos}[/bold red]"
    )


if __name__ == "__main__":
    main()
