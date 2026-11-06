"""Linha de comando do pipeline ETL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from etl_santander.pipeline import AVISO_MODO, EtlError, run


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etl_santander",
        description=(
            "Lê um CSV com Nome, Conta e Cartão, monta uma mensagem educativa "
            "por pessoa e grava outro CSV. "
            + AVISO_MODO
        ),
        epilog=(
            "Exemplo: python -m etl_santander "
            "--entrada dados/clientes_exemplo.csv "
            "--saida exemplos/mensagens_exemplo.csv"
        ),
    )
    parser.add_argument(
        "-e",
        "--entrada",
        required=True,
        help="CSV de entrada em UTF-8, com as colunas Nome, Conta e Cartão.",
    )
    parser.add_argument(
        "-s",
        "--saida",
        required=True,
        help="CSV de saída. A pasta é criada se ainda não existir. O arquivo é substituído.",
    )
    return parser


def _preferir_utf8(fluxo: object) -> None:
    reconfigure = getattr(fluxo, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8")
    except (OSError, ValueError):
        return


def main(argv: list[str] | None = None) -> int:
    """Executa o ETL e devolve o código de saída do processo."""
    _preferir_utf8(sys.stdout)
    _preferir_utf8(sys.stderr)
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        registros = run(Path(args.entrada), Path(args.saida))
    except EtlError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    print(AVISO_MODO)
    print(f"Registros processados: {len(registros)}")
    print(f"Arquivo de saída: {Path(args.saida)}")
    return 0
