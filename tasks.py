"""
Casos de teste pros dois agentes.

A task é extrair informacoes estruturadas de descricoes
de vagas de emprego escritas em texto cru.
"""

TASKS = [
    {
        "input": "Procuramos engenheira de dados pleno, remoto, faixa de 12k a 16k. Stack: Python, dbt, Snowflake.",
        "expected": {
            "cargo": "engenheira de dados",
            "nivel": "pleno",
            "modalidade": "remoto",
            "salario_min": 12000,
            "salario_max": 16000,
            "stack": ["Python", "dbt", "Snowflake"],
        },
    },
    {
        "input": "Vaga: Tech Lead backend. Hibrido SP, 2x na semana. Salario entre R$ 20.000 e R$ 25.000. Go, Kafka, Postgres.",
        "expected": {
            "cargo": "Tech Lead backend",
            "nivel": "lead",
            "modalidade": "hibrido",
            "salario_min": 20000,
            "salario_max": 25000,
            "stack": ["Go", "Kafka", "Postgres"],
        },
    },
    {
        "input": "Estamos contratando dev frontend junior presencial em Floripa, 5k fixos. React e TypeScript.",
        "expected": {
            "cargo": "dev frontend",
            "nivel": "junior",
            "modalidade": "presencial",
            "salario_min": 5000,
            "salario_max": 5000,
            "stack": ["React", "TypeScript"],
        },
    },
    {
        "input": "Oportunidade: SRE senior, full remote, ate 18k. Kubernetes, Terraform, AWS, observabilidade.",
        "expected": {
            "cargo": "SRE",
            "nivel": "senior",
            "modalidade": "remoto",
            "salario_min": None,
            "salario_max": 18000,
            "stack": ["Kubernetes", "Terraform", "AWS"],
        },
    },
    {
        "input": "Cientista de dados pleno/senior, remoto Brasil, 15-22k. Python, SQL, ML, experiencia com LLMs e um diferencial.",
        "expected": {
            "cargo": "Cientista de dados",
            "nivel": "pleno/senior",
            "modalidade": "remoto",
            "salario_min": 15000,
            "salario_max": 22000,
            "stack": ["Python", "SQL", "ML"],
        },
    },
]


SCHEMA = {
    "type": "object",
    "required": ["cargo", "nivel", "modalidade", "salario_min", "salario_max", "stack"],
    "properties": {
        "cargo": {"type": "string"},
        "nivel": {"type": "string"},
        "modalidade": {"type": "string", "enum": ["remoto", "hibrido", "presencial"]},
        "salario_min": {"type": ["number", "null"]},
        "salario_max": {"type": ["number", "null"]},
        "stack": {"type": "array", "items": {"type": "string"}},
    },
}


def task_ok(got: dict, expected: dict) -> bool:
    """Comparacao tolerante: nao precisa bater 100%, so o essencial."""
    if not isinstance(got, dict):
        return False

    if got.get("modalidade") != expected["modalidade"]:
        return False

    if got.get("salario_min") != expected["salario_min"]:
        return False
    if got.get("salario_max") != expected["salario_max"]:
        return False

    got_stack = {s.lower() for s in got.get("stack", [])}
    exp_stack = {s.lower() for s in expected["stack"]}
    if not exp_stack.issubset(got_stack):
        return False

    return True
