"""Testes do ETL: acentos, validação, identificadores e ida e volta do CSV."""

from __future__ import annotations

import csv
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl_santander.pipeline import (  # noqa: E402
    AVISO_MODO,
    MODELOS,
    ORIGEM_TEMPLATE,
    EtlError,
    extract,
    load,
    run,
    transform,
)
from etl_santander.cli import main  # noqa: E402

EXEMPLO_ENTRADA = ROOT / "dados" / "clientes_exemplo.csv"
EXEMPLO_SAIDA = ROOT / "exemplos" / "mensagens_exemplo.csv"


@contextmanager
def pasta_temporaria():
    with tempfile.TemporaryDirectory() as nome:
        yield Path(nome)

TERMOS_FORA_DO_ESCOPO = (
    "garantid",
    "rentabilidade",
    "lucro",
    "invista",
    "investimento",
    "rendimento",
    "openai",
    "gpt",
)


class TestExtract(unittest.TestCase):
    def test_exemplo_preserva_acentos_e_identificadores(self) -> None:
        registros = extract(EXEMPLO_ENTRADA)
        self.assertEqual(len(registros), 4)
        self.assertEqual(registros[1]["Nome"], "João Conceição (nome fictício)")
        self.assertEqual(registros[2]["Nome"], "Márcia Álvarez (nome fictício)")
        self.assertEqual(registros[3]["Nome"], "Lúcia d'Ávila (nome fictício)")
        self.assertEqual(registros[0]["Conta"], "CONTA-FICTICIA-00012340")
        self.assertEqual(registros[1]["Conta"], "CONTA-FICTICIA-00002-2")
        self.assertEqual(registros[3]["Cartão"], "CARTAO-FICTICIO-****-0090")
        self.assertTrue(all(item["Aviso"] == "REGISTRO_FICTICIO" for item in registros))

    def test_zeros_a_esquerda_e_espacos_internos_permanecem(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            origem.write_text(
                "Nome,Conta,Cartão\n"
                "  João Conceição  ,  00012340  ,CARTAO-FICTICIO  ****  0007\n",
                encoding="utf-8",
                newline="\n",
            )
            registro = extract(origem)[0]
        self.assertEqual(registro["Nome"], "João Conceição")
        self.assertEqual(registro["Conta"], "00012340")
        self.assertTrue(registro["Conta"].startswith("000"))
        self.assertEqual(registro["Cartão"], "CARTAO-FICTICIO  ****  0007")

    def test_aceita_bom_e_quebra_de_linha_windows(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            origem.write_bytes(
                "Nome,Conta,Cartão\r\n"
                "Ana (nome fictício),00090-0,CARTAO-FICTICIO-****-0007\r\n".encode("utf-8-sig")
            )
            registro = extract(origem)[0]
        self.assertEqual(registro["Nome"], "Ana (nome fictício)")
        self.assertEqual(registro["Conta"], "00090-0")
        self.assertEqual(registro["Cartão"], "CARTAO-FICTICIO-****-0007")

    def test_ignora_linha_em_branco_e_recusa_valor_ausente(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            origem.write_text(
                "Nome,Conta,Cartão\n"
                "\n"
                "Ana (nome fictício),00012340,CARTAO-FICTICIO-****-0001\n"
                ",00002-2,CARTAO-FICTICIO-****-0002\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(EtlError) as contexto:
                extract(origem)
        self.assertIn("linha 4", str(contexto.exception))
        self.assertIn("Nome", str(contexto.exception))

    def test_coluna_ausente(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            origem.write_text(
                "Nome,Conta\nAna (nome fictício),00012340\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(EtlError) as contexto:
                extract(origem)
        mensagem = str(contexto.exception)
        self.assertIn("Cartão", mensagem)
        self.assertIn("Nome, Conta", mensagem)

    def test_cartao_sem_til_explica_o_nome_esperado(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            origem.write_text(
                "Nome,Conta,Cartao\nAna,00012340,CARTAO-FICTICIO-****-0001\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(EtlError) as contexto:
                extract(origem)
        self.assertIn("use exatamente 'Cartão'", str(contexto.exception))

    def test_ponto_e_virgula_gera_dica(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            origem.write_text(
                "Nome;Conta;Cartão\nAna;00012340;CARTAO-FICTICIO-****-0001\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(EtlError) as contexto:
                extract(origem)
        self.assertIn("ponto e vírgula", str(contexto.exception))

    def test_arquivo_inexistente_pasta_e_utf8_invalido(self) -> None:
        with pasta_temporaria() as pasta:
            with self.assertRaises(EtlError) as ausente:
                extract(pasta / "nao_existe.csv")
            self.assertIn("não encontrado", str(ausente.exception))

            with self.assertRaises(EtlError) as diretorio:
                extract(pasta)
            self.assertIn("não é um arquivo", str(diretorio.exception))

            invalido = pasta / "latin1.csv"
            invalido.write_bytes("Nome,Conta,Cartão\nJosé,0001,CARTAO\n".encode("latin-1"))
            with self.assertRaises(EtlError) as codificacao:
                extract(invalido)
            self.assertIn("UTF-8", str(codificacao.exception))

    def test_so_cabecalho_e_coluna_repetida(self) -> None:
        with pasta_temporaria() as pasta:
            vazio = pasta / "vazio.csv"
            vazio.write_text("Nome,Conta,Cartão\n", encoding="utf-8", newline="\n")
            with self.assertRaises(EtlError) as sem_dados:
                extract(vazio)
            self.assertIn("não tem registros", str(sem_dados.exception))

            repetido = pasta / "repetido.csv"
            repetido.write_text(
                "Nome,Conta,Cartão,Conta\nAna,00012340,CARTAO-FICTICIO-****-0001,00012340\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(EtlError) as colunas:
                extract(repetido)
            self.assertIn("repetidas", str(colunas.exception))
            self.assertIn("Conta", str(colunas.exception))

class TestTransform(unittest.TestCase):
    def test_personaliza_nome_com_acento_sem_alterar_o_original(self) -> None:
        original = {
            "Nome": "João Conceição (nome fictício)",
            "Conta": "00012340",
            "Cartão": "CARTAO-FICTICIO-****-0007",
            "Aviso": "REGISTRO_FICTICIO",
        }
        resultado = transform([original])[0]
        self.assertNotIn("Mensagem", original)
        self.assertEqual(resultado["Conta"], "00012340")
        self.assertEqual(resultado["Cartão"], "CARTAO-FICTICIO-****-0007")
        self.assertEqual(resultado["Aviso"], "REGISTRO_FICTICIO")
        self.assertEqual(resultado["Origem"], ORIGEM_TEMPLATE)
        self.assertEqual(resultado["Modelo"], "template_reserva")
        self.assertIn("João Conceição (nome fictício)", resultado["Mensagem"])
        self.assertNotIn("{nome}", resultado["Mensagem"])

    def test_rotacao_deterministica_dos_modelos(self) -> None:
        registros = [
            {
                "Nome": f"Pessoa fictícia {indice}",
                "Conta": f"000{indice}",
                "Cartão": "CARTAO-FICTICIO-****-0001",
            }
            for indice in range(5)
        ]
        saida = transform(registros)
        codigos = [item["Modelo"] for item in saida]
        self.assertEqual(
            codigos,
            [
                "template_reserva",
                "template_orcamento",
                "template_meta",
                "template_pausa",
                "template_reserva",
            ],
        )
        self.assertEqual(saida[0]["Mensagem"].split(",", 1)[0], "Pessoa fictícia 0")
        self.assertTrue(saida[4]["Mensagem"].startswith("Pessoa fictícia 4, separe um valor"))
        self.assertTrue(all(item["Origem"] == ORIGEM_TEMPLATE for item in saida))

    def test_textos_sao_educativos_e_nao_prometem_retorno(self) -> None:
        for _codigo, texto in MODELOS:
            reduzido = texto.casefold()
            for termo in TERMOS_FORA_DO_ESCOPO:
                self.assertNotIn(termo, reduzido)
            self.assertIn("{nome}", texto)


class TestLoadERun(unittest.TestCase):
    def test_roundtrip_preserva_identificadores_e_mensagem(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "clientes.csv"
            destino = pasta / "saida" / "mensagens.csv"
            origem.write_text(
                "Nome,Conta,Cartão\n"
                "Márcia Álvarez (nome fictício),00012340,CARTAO-FICTICIO-****-0007\n",
                encoding="utf-8",
                newline="\n",
            )
            gerados = run(origem, destino)
            self.assertFalse((pasta / "saida" / "mensagens.csv.tmp").exists())

            with destino.open(encoding="utf-8", newline="") as arquivo:
                lidos = list(csv.DictReader(arquivo))
            self.assertEqual(len(lidos), 1)
            self.assertEqual(lidos[0]["Nome"], "Márcia Álvarez (nome fictício)")
            self.assertEqual(lidos[0]["Conta"], "00012340")
            self.assertTrue(lidos[0]["Conta"].startswith("000"))
            self.assertEqual(lidos[0]["Cartão"], "CARTAO-FICTICIO-****-0007")
            self.assertEqual(lidos[0]["Mensagem"], gerados[0]["Mensagem"])
            self.assertIn("Márcia Álvarez (nome fictício)", lidos[0]["Mensagem"])
            self.assertNotIn("\r\n", destino.read_bytes().decode("utf-8"))

            de_novo = extract(destino)
            self.assertEqual(de_novo[0]["Conta"], "00012340")
            self.assertEqual(de_novo[0]["Cartão"], "CARTAO-FICTICIO-****-0007")
            self.assertEqual(de_novo[0]["Mensagem"], lidos[0]["Mensagem"])

            copia = pasta / "copia.csv"
            load(de_novo, copia)
            self.assertEqual(destino.read_bytes(), copia.read_bytes())

    def test_entrada_invalida_nao_cria_saida_e_recusa_mesmo_arquivo(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "ruim.csv"
            destino = pasta / "saida.csv"
            origem.write_text("Nome,Conta\nAna,0001\n", encoding="utf-8", newline="\n")
            with self.assertRaises(EtlError):
                run(origem, destino)
            self.assertFalse(destino.exists())

            valido = pasta / "ok.csv"
            valido.write_text(
                "Nome,Conta,Cartão\nAna (nome fictício),00012340,CARTAO-FICTICIO-****-0001\n",
                encoding="utf-8",
                newline="\n",
            )
            with self.assertRaises(EtlError) as mesmo:
                run(valido, valido)
            self.assertIn("caminhos diferentes", str(mesmo.exception))

    def test_duas_execucoes_geram_os_mesmos_bytes(self) -> None:
        with pasta_temporaria() as pasta:
            primeira = pasta / "a.csv"
            segunda = pasta / "b.csv"
            run(EXEMPLO_ENTRADA, primeira)
            run(EXEMPLO_ENTRADA, segunda)
            self.assertEqual(primeira.read_bytes(), segunda.read_bytes())

    def test_load_sem_transform_explica_o_que_falta(self) -> None:
        with pasta_temporaria() as pasta:
            with self.assertRaises(EtlError) as contexto:
                load(
                    [
                        {
                            "Nome": "Ana (nome fictício)",
                            "Conta": "00012340",
                            "Cartão": "CARTAO-FICTICIO-****-0001",
                        }
                    ],
                    pasta / "saida.csv",
                )
        self.assertIn("transform()", str(contexto.exception))
        self.assertIn("Mensagem", str(contexto.exception))

    def test_exemplo_versionado_reproduz_a_execucao(self) -> None:
        self.assertTrue(EXEMPLO_SAIDA.is_file(), "Gere exemplos/mensagens_exemplo.csv com o CLI.")
        with pasta_temporaria() as pasta:
            gerado = pasta / "mensagens.csv"
            run(EXEMPLO_ENTRADA, gerado)
            self.assertEqual(gerado.read_bytes(), EXEMPLO_SAIDA.read_bytes())
        texto = EXEMPLO_SAIDA.read_text(encoding="utf-8")
        self.assertIn("João Conceição (nome fictício)", texto)
        self.assertIn("CONTA-FICTICIA-00012340", texto)
        self.assertIn("CARTAO-FICTICIO-****-0001", texto)
        self.assertIn(ORIGEM_TEMPLATE, texto)
        self.assertIn("template_reserva", texto)
        for termo in TERMOS_FORA_DO_ESCOPO:
            self.assertNotIn(termo, texto.casefold())


class TestCli(unittest.TestCase):
    def test_sucesso_informa_que_nao_e_ia(self) -> None:
        with pasta_temporaria() as pasta:
            destino = pasta / "mensagens.csv"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                codigo = main(["--entrada", str(EXEMPLO_ENTRADA), "--saida", str(destino)])
            self.assertEqual(codigo, 0)
            self.assertIn("não é inteligência artificial", stdout.getvalue())
            self.assertIn("Registros processados: 4", stdout.getvalue())
            self.assertTrue(destino.is_file())
            self.assertIn("não é inteligência artificial", AVISO_MODO)

    def test_erro_de_validacao_vai_para_stderr(self) -> None:
        with pasta_temporaria() as pasta:
            origem = pasta / "ruim.csv"
            origem.write_text("Nome,Conta\nAna,1\n", encoding="utf-8", newline="\n")
            destino = pasta / "saida.csv"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                codigo = main(["-e", str(origem), "-s", str(destino)])
            mensagem = stderr.getvalue()
            self.assertEqual(codigo, 1)
            self.assertIn("Cartão", mensagem)
            self.assertFalse(destino.exists())

    def test_ajuda_e_modulo(self) -> None:
        ajuda = subprocess.run(
            [sys.executable, "-m", "etl_santander", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(ajuda.returncode, 0)
        self.assertIn("não é inteligência artificial", ajuda.stdout)
        self.assertIn("Nome, Conta e Cartão", ajuda.stdout)

        faltou = subprocess.run(
            [sys.executable, "-m", "etl_santander"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(faltou.returncode, 2)

        with pasta_temporaria() as pasta:
            destino = pasta / "mensagens.csv"
            completo = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "etl_santander",
                    "--entrada",
                    str(EXEMPLO_ENTRADA),
                    "--saida",
                    str(destino),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completo.returncode, 0, completo.stderr)
            self.assertIn("não é inteligência artificial", completo.stdout)
            self.assertIn("Registros processados: 4", completo.stdout)
            self.assertTrue(destino.read_text(encoding="utf-8").startswith("Nome,Conta,Cartão"))


if __name__ == "__main__":
    unittest.main()
