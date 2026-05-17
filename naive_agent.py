"""
Agente naive: uma chamada ao LLM resolve tudo.

Sem validacao, sem retry, sem evaluator independente. O modelo
fala que terminou, a gente acredita. Esse arquivo existe como
baseline pra comparacao com o harness_agent.py.
"""

import json
from anthropic import Anthropic
from rich.console import Console
from rich.table import Table

from tasks import TASKS, task_ok

client = Anthropic()
MODEL = "claude-haiku-4-5"
console = Console()


def run(text: str) -> tuple[dict, bool]:
    """
    Retorna (dado_extraido, agente_declarou_sucesso).

    O naive nao tem como saber de verdade se acertou: a unica
    coisa que ele consegue checar e se o JSON parseou. Por isso
    declared_ok aqui e quase sempre True, mesmo quando o conteudo
    esta errado. Esse e justamente o ponto da comparacao com o
    harness, que tem um evaluator de verdade.
    """
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extraia as informacoes da vaga abaixo e responda APENAS um JSON "
                    "com as chaves: cargo, nivel, modalidade, salario_min, salario_max, stack.\n\n"
                    f"Vaga: {text}"
                ),
            }
        ],
    )

    raw = msg.content[0].text.strip()
    # tentativa otimista de parsear, sem rede de seguranca
    try:
        return json.loads(raw), True
    except json.JSONDecodeError:
        # fallback ingenuo: tenta achar o primeiro { e o ultimo }
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end]), True
        except Exception:
            return {}, False


def main() -> None:
    console.rule("[bold]naive agent[/bold] — sem harness")

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
