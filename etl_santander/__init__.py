"""Pipeline ETL didático: CSV fictício, modelos de texto e um novo arquivo.

As mensagens saem de templates fixos. Este pacote não chama inteligência
artificial nem a API da Santander Dev Week.
"""

from etl_santander.pipeline import (
    AVISO_MODO,
    COLUNAS_OBRIGATORIAS,
    EtlError,
    extract,
    load,
    run,
    transform,
)

__all__ = [
    "AVISO_MODO",
    "COLUNAS_OBRIGATORIAS",
    "EtlError",
    "extract",
    "load",
    "run",
    "transform",
]
