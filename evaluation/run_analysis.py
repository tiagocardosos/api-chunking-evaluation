"""
run_analysis.py
===============
Script CLI de entrada para a análise estatística completa.

Uso (dentro do container ou com Python local):

    # Dentro do container postgres (ou com acesso direto):
    docker exec -it <container_fastapi> python evaluation/run_analysis.py

    # Com URL explícita:
    python run_analysis.py --postgres-url postgresql://rag:rag123@localhost:5432/rag_eval

    # Só PDF:
    python run_analysis.py --doc-type pdf --output-dir outputs/pdf

    # Só inferencial:
    python run_analysis.py --question-type inferential

Outputs em outputs/ (ou --output-dir):
    summary.{csv,md,tex}           → Tabela 1 do artigo
    pvalues_<metric>.{csv,md,tex}  → Tabelas de p-values por métrica
    ranking.{csv,md,tex}           → Ranking de estratégias
    all_comparisons.csv            → Dados brutos de todas as comparações
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Análise estatística dos experimentos de chunking RAG."
    )
    parser.add_argument(
        "--postgres-url",
        default=None,
        help="URL do PostgreSQL (default: variável POSTGRES_URL ou localhost).",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Diretório de saída para as tabelas (default: outputs/).",
    )
    parser.add_argument(
        "--doc-type",
        choices=["pdf", "xml_lattes"],
        default=None,
        help="Filtra análise por tipo de documento.",
    )
    parser.add_argument(
        "--question-type",
        choices=["factual", "inferential"],
        default=None,
        help="Filtra análise por tipo de pergunta.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Nível de significância (default: 0.05).",
    )
    parser.add_argument(
        "--min-pairs",
        type=int,
        default=10,
        help="Mínimo de pares válidos para rodar o Wilcoxon (default: 10).",
    )
    args = parser.parse_args()

    # Adiciona o diretório evaluation/ ao path para imports relativos
    sys.path.insert(0, str(Path(__file__).parent))

    from results_loader import ResultsLoader
    from wilcoxon import run_all_comparisons, results_to_dataframe
    from tables import save_all

    # ── 1. Carrega resultados ─────────────────────────────────────────────────
    print("Carregando resultados do PostgreSQL...")
    loader = ResultsLoader(postgres_url=args.postgres_url) if args.postgres_url else ResultsLoader()

    # Lista experimentos disponíveis
    experiments_df = loader.list_experiments()
    if experiments_df.empty:
        print("[ERRO] Nenhum experimento encontrado no banco de dados.")
        print("       Execute pelo menos um experimento via POST /experiments/run antes.")
        sys.exit(1)

    print(f"\nExperimentos encontrados: {len(experiments_df)}")
    completed = experiments_df[experiments_df["status"] == "completed"]
    print(f"  Concluídos : {len(completed)}")
    print(f"  Em execução: {len(experiments_df[experiments_df['status'] == 'running'])}")
    print(f"  Pendentes  : {len(experiments_df[experiments_df['status'] == 'pending'])}")

    if completed.empty:
        print("\n[ERRO] Nenhum experimento concluído. Aguarde a conclusão e tente novamente.")
        sys.exit(1)

    print("\nEstratégias disponíveis:")
    for strategy, count in completed.groupby("chunking_strategy")["id"].count().items():
        print(f"  {strategy}: {count} experimento(s)")

    # Carrega resultados filtrados
    results = loader.load_all(
        doc_type_filter=args.doc_type,
        question_type_filter=args.question_type,
    )

    if not results:
        print("\n[ERRO] Nenhum resultado após aplicar os filtros.")
        sys.exit(1)

    print(f"\nDados carregados: {len(results)} estratégias")
    for strategy, df in results.items():
        n_valid = df.notna().sum().sum()
        print(f"  {strategy}: {len(df)} perguntas, {n_valid} scores válidos")

    if len(results) < 2:
        print("\n[AVISO] Menos de 2 estratégias carregadas. Wilcoxon requer ao menos 2.")
        print("         Salvando apenas a tabela resumo.")
        from tables import summary_table, _save_table  # noqa: PLC0415
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        _save_table(summary_table(results), out / "summary", "Resumo")
        sys.exit(0)

    # ── 2. Teste de Wilcoxon ──────────────────────────────────────────────────
    print(f"\nExecutando Wilcoxon (α={args.alpha}, min_pairs={args.min_pairs})...")
    comparisons = run_all_comparisons(results, alpha=args.alpha, min_pairs=args.min_pairs)

    n_significant = sum(1 for c in comparisons if c.significant)
    print(f"  Comparações totais  : {len(comparisons)}")
    print(f"  Significativas (✓)  : {n_significant}")
    print(f"  Não significativas  : {len(comparisons) - n_significant}")

    # ── 3. Exibe resultado do critério de sucesso do experimento ──────────────
    _print_success_criteria(comparisons, results, args.alpha)

    # ── 4. Salva todas as tabelas ─────────────────────────────────────────────
    print(f"\nSalvando tabelas em '{args.output_dir}'...")
    save_all(results, comparisons, output_dir=args.output_dir, alpha=args.alpha)


def _print_success_criteria(
    comparisons: list,
    results: dict,
    alpha: float,
) -> None:
    """
    Verifica os critérios de sucesso do EXPERIMENT-SPEC §7:
        1. Diferença estatística significativa entre pelo menos um par.
        2. Structure-aware vence em XMLs Lattes (se dados disponíveis).
    """
    print("\n" + "="*60)
    print("CRITÉRIOS DE SUCESSO (EXPERIMENT-SPEC §7)")
    print("="*60)

    # Critério 1: alguma diferença significativa?
    sig_comparisons = [c for c in comparisons if c.significant]
    if sig_comparisons:
        print(f"✓ Critério 1: {len(sig_comparisons)} comparações significativas encontradas.")
    else:
        print("✗ Critério 1: Nenhuma diferença significativa. Aumentar o golden set.")

    # Critério 2: structure_aware vence em XML?
    from wilcoxon import ComparisonResult  # noqa: PLC0415
    sa_wins = [
        c for c in sig_comparisons
        if c.winner == "structure_aware"
    ]
    if "structure_aware" in results:
        if sa_wins:
            metrics_won = {c.metric for c in sa_wins}
            print(f"✓ Critério 2: structure_aware venceu em: {', '.join(metrics_won)}")
        else:
            print("✗ Critério 2: structure_aware não venceu nenhuma comparação significativa.")
    else:
        print("~ Critério 2: estratégia structure_aware não está nos dados carregados.")

    print("="*60)


if __name__ == "__main__":
    main()
