"""Funções extract, transform e load.

O modo de transformação é template de texto, determinístico e offline.
Não é inteligência artificial e não consulta a API da Santander Dev Week.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

AVISO_MODO = (
    "Modo: templates de texto (não é inteligência artificial). "
    "Nenhuma API é chamada."
)

COLUNAS_OBRIGATORIAS = ("Nome", "Conta", "Cartão")
COLUNA_ORIGEM = "Origem"
COLUNA_MODELO = "Modelo"
COLUNA_MENSAGEM = "Mensagem"
ORIGEM_TEMPLATE = "template_de_texto_nao_e_ia"
COLUNAS_SAIDA = (
    *COLUNAS_OBRIGATORIAS,
    COLUNA_ORIGEM,
    COLUNA_MODELO,
    COLUNA_MENSAGEM,
)

# (código estável, texto com o marcador {nome})
# A linha 0 usa o primeiro item, a linha 1 o segundo, e depois a lista recomeça.
MODELOS: tuple[tuple[str, str], ...] = (
    (
        "template_reserva",
        "{nome}, separe um valor fixo no início do mês para uma reserva de emergência. "
        "Planejar o básico, com calma, reduz o impacto de imprevistos.",
    ),
    (
        "template_orcamento",
        "{nome}, anote entradas e saídas durante uma semana. "
        "Enxergar o orçamento ajuda a decidir os próximos gastos com mais clareza.",
    ),
    (
        "template_meta",
        "{nome}, escolha uma meta simples de economia e revise o progresso no fim do mês. "
        "A diferença aparece na constância, não na pressa.",
    ),
    (
        "template_pausa",
        "{nome}, antes de uma compra grande, espere dois dias e compare o valor com a sua reserva. "
        "Essa pausa ajuda a gastar de acordo com o que você já planejou.",
    ),
)


class EtlError(Exception):
    """Erro de arquivo ou de validação no pipeline ETL."""


def extract(caminho: str | Path) -> list[dict[str, str]]:
    """Lê o CSV e devolve cada linha como dicionário de texto.

    Conta, Cartão e qualquer outro identificador permanecem string.
    Zeros à esquerda não são removidos, porque nada é convertido em número.
    """
    _exigir_python_310()
    origem = _exigir_arquivo_de_entrada(caminho)
    try:
        with origem.open(encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.reader(arquivo)
            linhas = list(leitor)
    except UnicodeDecodeError as erro:
        raise EtlError(
            f"O arquivo '{origem}' não está em UTF-8. "
            "Salve o CSV como UTF-8 e tente de novo."
        ) from erro
    except csv.Error as erro:
        raise EtlError(f"Não foi possível ler o CSV '{origem}': {erro}") from erro
    except OSError as erro:
        raise EtlError(f"Não foi possível ler '{origem}': {erro}") from erro

    if not linhas or not any(celula.strip() for celula in linhas[0]):
        raise EtlError(
            "A primeira linha do CSV precisa ser o cabeçalho "
            "com as colunas Nome, Conta e Cartão."
        )

    cabecalho = [celula.strip() for celula in linhas[0]]
    _validar_cabecalho(cabecalho)
    registros: list[dict[str, str]] = []

    for deslocamento, bruta in enumerate(linhas[1:], start=2):
        if not bruta or not any(celula.strip() for celula in bruta):
            continue
        if len(bruta) > len(cabecalho):
            raise EtlError(
                f"A linha {deslocamento} tem {len(bruta)} valores, "
                f"mas o cabeçalho tem {len(cabecalho)} colunas."
            )
        celulas = [celula.strip() for celula in bruta]
        if len(celulas) < len(cabecalho):
            celulas.extend([""] * (len(cabecalho) - len(celulas)))
        registro = dict(zip(cabecalho, celulas, strict=True))
        for coluna in COLUNAS_OBRIGATORIAS:
            if registro[coluna] == "":
                raise EtlError(
                    f"Valor ausente na coluna '{coluna}' (linha {deslocamento} do arquivo)."
                )
        registros.append(registro)

    if not registros:
        raise EtlError(
            "O CSV não tem registros. Inclua ao menos uma linha além do cabeçalho."
        )
    return registros


def transform(registros: list[dict[str, str]]) -> list[dict[str, str]]:
    """Acrescenta origem, modelo e mensagem educativa a cada registro.

    A escolha do template depende só da posição da linha. O mesmo CSV
    produz sempre as mesmas frases. Nenhuma rede é acessada.
    """
    _exigir_python_310()
    transformados: list[dict[str, str]] = []
    for indice, registro in enumerate(registros):
        faltando = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in registro]
        if faltando:
            raise EtlError(
                "transform() recebeu um registro sem "
                + ", ".join(faltando)
                + ". Esses campos vêm de extract()."
            )
        codigo, texto = MODELOS[indice % len(MODELOS)]
        novo = dict(registro)
        novo[COLUNA_ORIGEM] = ORIGEM_TEMPLATE
        novo[COLUNA_MODELO] = codigo
        novo[COLUNA_MENSAGEM] = texto.replace("{nome}", registro["Nome"])
        transformados.append(novo)
    return transformados


def load(registros: list[dict[str, str]], caminho: str | Path) -> None:
    """Grava os registros em CSV UTF-8, com quebra de linha LF.

    O arquivo temporário só substitui o destino quando a escrita termina.
    """
    _exigir_python_310()
    for indice, registro in enumerate(registros, start=1):
        faltando = [coluna for coluna in COLUNAS_SAIDA if coluna not in registro]
        if faltando:
            raise EtlError(
                f"O registro {indice} não tem "
                + ", ".join(faltando)
                + ". Use transform() antes de load(), ou run() para o fluxo completo."
            )

    destino = Path(caminho)
    if destino.exists() and destino.is_dir():
        raise EtlError(f"O caminho de saída é uma pasta, não um arquivo: {destino}")
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        raise EtlError(f"Não foi possível criar a pasta de '{destino}': {erro}") from erro

    campos = list(COLUNAS_SAIDA)
    for registro in registros:
        for chave in registro:
            if chave not in campos:
                campos.append(chave)

    temporario = destino.with_name(destino.name + ".tmp")
    try:
        with temporario.open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.DictWriter(
                arquivo,
                fieldnames=campos,
                lineterminator="\n",
                extrasaction="ignore",
            )
            escritor.writeheader()
            for registro in registros:
                escritor.writerow({campo: registro.get(campo, "") for campo in campos})
        temporario.replace(destino)
    except OSError as erro:
        temporario.unlink(missing_ok=True)
        raise EtlError(f"Não foi possível gravar '{destino}': {erro}") from erro


def run(entrada: str | Path, saida: str | Path) -> list[dict[str, str]]:
    """Executa extract, transform e load, nesta ordem."""
    _exigir_python_310()
    origem = Path(entrada)
    destino = Path(saida)
    if origem.resolve() == destino.resolve():
        raise EtlError("O arquivo de entrada e o de saída precisam ser caminhos diferentes.")
    registros = extract(origem)
    transformados = transform(registros)
    load(transformados, destino)
    return transformados


def _exigir_python_310() -> None:
    if sys.version_info < (3, 10):
        raise EtlError("Este projeto requer Python 3.10 ou superior.")


def _exigir_arquivo_de_entrada(caminho: str | Path) -> Path:
    origem = Path(caminho)
    if not origem.exists():
        raise EtlError(f"Arquivo de entrada não encontrado: {origem}")
    if not origem.is_file():
        raise EtlError(f"O caminho de entrada não é um arquivo: {origem}")
    return origem


def _validar_cabecalho(cabecalho: list[str]) -> None:
    if any(coluna == "" for coluna in cabecalho):
        raise EtlError("O cabeçalho tem uma coluna sem nome.")
    if len(cabecalho) != len(set(cabecalho)):
        repetidas = sorted({coluna for coluna in cabecalho if cabecalho.count(coluna) > 1})
        raise EtlError(
            "O cabeçalho tem colunas repetidas: " + ", ".join(repetidas) + "."
        )
    faltando = [coluna for coluna in COLUNAS_OBRIGATORIAS if coluna not in cabecalho]
    if faltando:
        encontradas = ", ".join(cabecalho) if cabecalho else "(nenhuma)"
        raise EtlError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(faltando)
            + f". Encontradas: {encontradas}. "
            "O CSV precisa das colunas Nome, Conta e Cartão."
            + _dicas_cabecalho(cabecalho)
        )


def _dicas_cabecalho(encontradas: list[str]) -> str:
    dicas: list[str] = []
    por_minusculo = {coluna.casefold(): coluna for coluna in encontradas}
    for chave, oficial in (("nome", "Nome"), ("conta", "Conta")):
        if oficial not in encontradas and chave in por_minusculo:
            dicas.append(
                f"Encontramos '{por_minusculo[chave]}'; use exatamente '{oficial}'."
            )
    if "Cartão" not in encontradas:
        for coluna in encontradas:
            if coluna.casefold() in {"cartao", "cartão"}:
                dicas.append(f"Encontramos '{coluna}'; use exatamente 'Cartão'.")
    if len(encontradas) == 1 and ";" in encontradas[0]:
        dicas.append(
            "O cabeçalho parece separado por ponto e vírgula. "
            "Use vírgula, como em dados/clientes_exemplo.csv."
        )
    if not dicas:
        return ""
    return " " + " ".join(dicas)
