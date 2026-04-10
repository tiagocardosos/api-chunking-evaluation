"""Analyze golden question datasets and output summary metrics."""

import json
import sys
from pathlib import Path
from collections import Counter

DATASETS = {
    "Regimento Comitê de Conduta Ética": "regimento_comite_conduta_etica_46.json",
    "Código de Ética (ago/2019)": "codigo_etica_agosto_2019_35.json",
    "Manual de Operação EMBRAPII v6": "manual_EMBRAPII_v6_20102020_150.json",
}

GQ_DIR = Path(__file__).resolve().parent.parent / "data" / "golden_questions"


def load_dataset(filename: str) -> list[dict]:
    filepath = GQ_DIR / filename
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def analyze_dataset(name: str, data: list[dict]) -> dict:
    total = len(data)
    type_counts = Counter(item.get("question_type", "unknown") for item in data)
    with_answer = sum(1 for item in data if item.get("expected_answer"))
    return {
        "name": name,
        "total": total,
        "with_expected_answer": with_answer,
        "question_types": dict(type_counts),
    }


def main() -> None:
    all_stats: list[dict] = []
    grand_total = 0
    grand_types: Counter = Counter()
    grand_with_answer = 0

    print("=" * 70)
    print("ANÁLISE DOS DATASETS DE GOLDEN QUESTIONS")
    print("=" * 70)

    for name, filename in DATASETS.items():
        data = load_dataset(filename)
        stats = analyze_dataset(name, data)
        all_stats.append(stats)

        grand_total += stats["total"]
        grand_with_answer += stats["with_expected_answer"]
        grand_types.update(stats["question_types"])

        print(f"\n--- {name} ({filename}) ---")
        print(f"  Total de perguntas: {stats['total']}")
        print(f"  Com expected_answer: {stats['with_expected_answer']}")
        print("  Distribuição por question_type:")
        for qtype, count in sorted(stats["question_types"].items()):
            pct = count / stats["total"] * 100
            print(f"    - {qtype}: {count} ({pct:.1f}%)")

    print("\n" + "=" * 70)
    print("RESUMO CONSOLIDADO")
    print("=" * 70)
    print(f"  Total de perguntas: {grand_total}")
    print(f"  Com expected_answer: {grand_with_answer}")
    print("  Distribuição por question_type:")
    for qtype, count in sorted(grand_types.items()):
        pct = count / grand_total * 100
        print(f"    - {qtype}: {count} ({pct:.1f}%)")

    print("\n--- Tabela Markdown ---\n")
    print("| Dataset | Total | Factual | Inferential | Com Resposta |")
    print("|:---|:---:|:---:|:---:|:---:|")
    for s in all_stats:
        factual = s["question_types"].get("factual", 0)
        inferential = s["question_types"].get("inferential", 0)
        print(
            f"| {s['name']} | {s['total']} | "
            f"{factual} ({factual/s['total']*100:.0f}%) | "
            f"{inferential} ({inferential/s['total']*100:.0f}%) | "
            f"{s['with_expected_answer']} |"
        )
    factual_total = grand_types.get("factual", 0)
    inferential_total = grand_types.get("inferential", 0)
    print(
        f"| **Total** | **{grand_total}** | "
        f"**{factual_total} ({factual_total/grand_total*100:.0f}%)** | "
        f"**{inferential_total} ({inferential_total/grand_total*100:.0f}%)** | "
        f"**{grand_with_answer}** |"
    )


if __name__ == "__main__":
    main()
