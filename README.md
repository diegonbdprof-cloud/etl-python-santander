# Pipeline ETL em Python — mensagens educativas com templates

> **Isto não é inteligência artificial.**
> O modo deste projeto — o único modo, e o padrão — monta as mensagens com **modelos de texto (templates)** fixos. A mesma planilha produz sempre o mesmo arquivo. Não há chave, não há rede e não há modelo generativo. A coluna `Origem` de cada linha sai com o valor `template_de_texto_nao_e_ia`.
>
> O objetivo do desafio é o fluxo **ETL** (extrair, transformar, carregar).

Projeto de portfólio em Python 3.10+ inspirado no laboratório de ETL da Santander Dev Week 2023 (DIO). Ele lê um CSV fictício com `Nome`, `Conta` e `Cartão`, escreve uma frase educativa de planejamento financeiro para cada pessoa e grava um CSV novo.

As frases falam de reserva, orçamento e pausa antes de uma compra grande. Elas **não** prometem rendimento, **não** recomendam produto e **não** são consultoria. Os nomes, as contas e os cartões do exemplo são **fictícios**.

## Crédito

O roteiro original está no notebook de [falvojr/santander-dev-week-2023](https://github.com/falvojr/santander-dev-week-2023/blob/master/SantanderDevWeek2023.ipynb):

1. um CSV só com `UserID`;
2. `GET` na API pública para buscar nome, conta e cartão;
3. uma frase via API da OpenAI;
4. `PUT` de volta na API, no campo `news`.

A API de demonstração (`sdw-2023-prd.up.railway.app`) foi descontinuada. O próprio notebook avisa isso e autoriza trocar a extração e gravar o resultado localmente. O repositório da API, [digitalinnovationone/santander-dev-week-2023-api](https://github.com/digitalinnovationone/santander-dev-week-2023-api), fica só como referência. **Este projeto não chama essa API e não chama a OpenAI.** Nenhuma das duas foi exercitada aqui.

## Por que o CSV (alternativa 2)

O notebook oferece duas saídas quando a API não responde:

- opção 1: dados escritos direto no código;
- opção 2: ler um arquivo e seguir com a transformação.

Este repositório segue a **opção 2**, com uma planilha que já traz o que o `GET` devolveria: nome, conta e cartão. A carga, que no notebook era um `PUT`, aqui é um arquivo CSV. O caminho dos dados continua visível: entra um arquivo, sai outro.

## O ETL neste projeto

```text
CSV de entrada  --extract-->  registros  --transform-->  registros + mensagem  --load-->  CSV de saída
```

| Etapa | Função | O que faz |
| --- | --- | --- |
| Extract | `extract` | Lê o CSV em UTF-8 e devolve uma lista de dicionários. Tudo permanece texto. |
| Transform | `transform` | Escolhe um template pela posição da linha e preenche o nome. Não acessa a rede. |
| Load | `load` | Grava outro CSV em UTF-8. A pasta de destino é criada se precisar. |
| Fluxo completo | `run` | Chama as três, nesta ordem. |

`Conta` e `Cartão` não passam por `int` nem por `float`. O texto `00012340` continua `00012340`. Espaços no começo e no fim da célula são removidos; espaços no meio permanecem.

Também dá para usar as funções direto, a partir da pasta do repositório:

```python
from pathlib import Path
from etl_santander import extract, transform, load

registros = extract(Path("dados/clientes_exemplo.csv"))
mensagens = transform(registros)
load(mensagens, Path("exemplos/mensagens_exemplo.csv"))
```

## Dados fictícios

Não há dado financeiro, documento ou contato real. Cada linha do exemplo carrega o aviso `REGISTRO_FICTICIO`. Os identificadores já dizem que são de mentira:

| Nome | Conta | Cartão |
| --- | --- | --- |
| Ana (nome fictício) | `CONTA-FICTICIA-00012340` | `CARTAO-FICTICIO-****-0001` |
| João Conceição (nome fictício) | `CONTA-FICTICIA-00002-2` | `CARTAO-FICTICIO-****-0002` |
| Márcia Álvarez (nome fictício) | `CONTA-FICTICIA-00010-7` | `CARTAO-FICTICIO-****-0010` |
| Lúcia d'Ávila (nome fictício) | `CONTA-FICTICIA-00090-0` | `CARTAO-FICTICIO-****-0090` |

Os cartões estão mascarados (`****`) e o prefixo `CARTAO-FICTICIO` impede que sejam lidos como número de cartão verdadeiro. Acentos, apóstrofo e zeros à esquerda fazem parte do exemplo de propósito.

Colunas obrigatórias: `Nome`, `Conta`, `Cartão`. O nome precisa ser exatamente esse, com o til em `Cartão`. Outras colunas, como `Aviso`, são copiadas para a saída.

## Estrutura

```text
.
├── dados/clientes_exemplo.csv      # entrada fictícia, UTF-8
├── exemplos/mensagens_exemplo.csv  # saída gerada pela execução do CLI
├── etl_santander/
│   ├── pipeline.py                 # extract, transform, load, run
│   ├── cli.py                      # argumentos --entrada e --saida
│   ├── __main__.py                 # python -m etl_santander
│   └── __init__.py
├── tests/test_pipeline.py
├── requirements.txt                # sem pacotes externos
└── .gitignore
```

O arquivo `exemplos/mensagens_exemplo.csv` não foi escrito à mão. Ele saiu do comando da seção seguinte. O teste `test_exemplo_versionado_reproduz_a_execucao` compara os bytes desse arquivo com uma execução nova.

## Requisitos

- Python 3.10 ou superior (o ambiente usado para gerar o exemplo e rodar os testes foi o Python 3.12.3).
- Nenhuma biblioteca de terceiros. `requirements.txt` existe para deixar isso explícito: pandas, requests e openai aparecem no notebook original e **não** são usadas aqui. O módulo `csv` da biblioteca padrão evita transformar a conta em número.

```bash
python -m pip install -r requirements.txt
```

Esse comando não instala pacote nenhum.

## Como executar no Linux e no macOS

Na pasta do repositório:

```bash
python3 --version
python3 -m etl_santander --entrada dados/clientes_exemplo.csv --saida exemplos/mensagens_exemplo.csv
```

Saída obtida nesta execução:

```text
Modo: templates de texto (não é inteligência artificial). Nenhuma API é chamada.
Registros processados: 4
Arquivo de saída: exemplos/mensagens_exemplo.csv
```

O programa devolve o código `0`. Rodar de novo com a mesma entrada gera os mesmos bytes.

## Como executar no Windows

No PowerShell ou no Prompt de Comando, na pasta do repositório. Se `python` não existir, use o lançador `py -3`:

```bat
py -3 --version
py -3 -m etl_santander --entrada dados\clientes_exemplo.csv --saida exemplos\mensagens_exemplo.csv
```

O programa tenta configurar a saída do console para UTF-8, para os acentos aparecerem. Se o console antigo ainda mostrar caracteres trocados:

```bat
py -3 -X utf8 -m etl_santander --entrada dados\clientes_exemplo.csv --saida exemplos\mensagens_exemplo.csv
```

O CSV de saída usa quebra de linha LF e UTF-8 sem BOM. O Excel do Windows, ao abrir o arquivo com dois cliques, pode escolher o separador ou a codificação errados e, se a conta for só dígitos, pode ainda comer os zeros à esquerda. Para conferir o resultado, abra por **Dados > De Texto/CSV** e escolha UTF-8 e vírgula, ou abra no editor de texto. O pipeline em si não converte identificador em número.

## Resultado esperado

Quatro linhas, uma para cada pessoa, nesta ordem de colunas: `Nome`, `Conta`, `Cartão`, `Origem`, `Modelo`, `Mensagem` e, no exemplo, `Aviso`.

| Nome | Modelo | Ideia da frase |
| --- | --- | --- |
| Ana (nome fictício) | `template_reserva` | Separar um valor fixo para reserva de emergência. |
| João Conceição (nome fictício) | `template_orcamento` | Anotar entradas e saídas por uma semana. |
| Márcia Álvarez (nome fictício) | `template_meta` | Meta simples de economia, revista no fim do mês. |
| Lúcia d'Ávila (nome fictício) | `template_pausa` | Esperar dois dias antes de uma compra grande. |

`Origem` é sempre `template_de_texto_nao_e_ia`. O arquivo completo, igual ao que o comando gravou:

```csv
Nome,Conta,Cartão,Origem,Modelo,Mensagem,Aviso
Ana (nome fictício),CONTA-FICTICIA-00012340,CARTAO-FICTICIO-****-0001,template_de_texto_nao_e_ia,template_reserva,"Ana (nome fictício), separe um valor fixo no início do mês para uma reserva de emergência. Planejar o básico, com calma, reduz o impacto de imprevistos.",REGISTRO_FICTICIO
João Conceição (nome fictício),CONTA-FICTICIA-00002-2,CARTAO-FICTICIO-****-0002,template_de_texto_nao_e_ia,template_orcamento,"João Conceição (nome fictício), anote entradas e saídas durante uma semana. Enxergar o orçamento ajuda a decidir os próximos gastos com mais clareza.",REGISTRO_FICTICIO
Márcia Álvarez (nome fictício),CONTA-FICTICIA-00010-7,CARTAO-FICTICIO-****-0010,template_de_texto_nao_e_ia,template_meta,"Márcia Álvarez (nome fictício), escolha uma meta simples de economia e revise o progresso no fim do mês. A diferença aparece na constância, não na pressa.",REGISTRO_FICTICIO
Lúcia d'Ávila (nome fictício),CONTA-FICTICIA-00090-0,CARTAO-FICTICIO-****-0090,template_de_texto_nao_e_ia,template_pausa,"Lúcia d'Ávila (nome fictício), antes de uma compra grande, espere dois dias e compare o valor com a sua reserva. Essa pausa ajuda a gastar de acordo com o que você já planejou.",REGISTRO_FICTICIO
```

Campos com vírgula vão entre aspas. É o comportamento normal do CSV. Ao ler de novo com `extract`, os identificadores e a mensagem voltam iguais, inclusive `CONTA-FICTICIA-00012340` e `CARTAO-FICTICIO-****-0001`.

## Como o template é escolhido

Há quatro frases em `etl_santander/pipeline.py`, na tupla `MODELOS`. A linha 0 usa a primeira, a linha 1 a segunda, e a quinta linha volta para a primeira (`índice % 4`). Por isso o resultado é reproduzível: não depende de sorte, de horário nem de serviço externo.

| Código | Texto, com `{nome}` no lugar da pessoa |
| --- | --- |
| `template_reserva` | `{nome}, separe um valor fixo no início do mês para uma reserva de emergência. Planejar o básico, com calma, reduz o impacto de imprevistos.` |
| `template_orcamento` | `{nome}, anote entradas e saídas durante uma semana. Enxergar o orçamento ajuda a decidir os próximos gastos com mais clareza.` |
| `template_meta` | `{nome}, escolha uma meta simples de economia e revise o progresso no fim do mês. A diferença aparece na constância, não na pressa.` |
| `template_pausa` | `{nome}, antes de uma compra grande, espere dois dias e compare o valor com a sua reserva. Essa pausa ajuda a gastar de acordo com o que você já planejou.` |

O marcador é trocado por substituição de texto. A frase não analisa saldo, gasto ou perfil, porque a planilha não traz nada disso — e não deve ser lida como recomendação individual.

### Inteligência artificial generativa

O notebook original pedia uma frase curta à API da OpenAI. **Este repositório não implementa esse modo.** Ele ficaria fora do caminho padrão, exigiria chave e rede, e o exemplo versionado deixaria de ser reproduzível. Não existe arquivo `.env`, não existe chave e o programa não lê `OPENAI_API_KEY`. Nada aqui foi produzido por um modelo generativo.

## Validação e erros

A entrada inválida interrompe o fluxo antes de criar o arquivo de saída. As mensagens vão para a saída de erro.

| Situação | Código | Exemplo do que o programa diz |
| --- | --- | --- |
| Faltou `--entrada` ou `--saida` | 2 | texto de ajuda do argparse |
| Arquivo que não existe, pasta no lugar de arquivo, UTF-8 inválido | 1 | `Arquivo de entrada não encontrado: ...` ou `não está em UTF-8` |
| Coluna obrigatória ausente | 1 | ver abaixo |
| Valor vazio em `Nome`, `Conta` ou `Cartão` | 1 | ver abaixo |
| Cabeçalho com `;` no lugar da vírgula | 1 | dica para usar vírgula, como no exemplo |
| Coluna repetida, linha com colunas a mais, CSV sem registros | 1 | a mensagem aponta o problema |
| Entrada e saída no mesmo caminho | 1 | `precisam ser caminhos diferentes` |
| Sucesso | 0 | resumo com a quantidade de registros |

Coluna ausente, executado de verdade com um CSV que só tinha `Nome` e `Conta`:

```text
Erro: Colunas obrigatórias ausentes: Cartão. Encontradas: Nome, Conta. O CSV precisa das colunas Nome, Conta e Cartão.
```

Valor ausente, executado de verdade (a conta da linha 2 estava vazia):

```text
Erro: Valor ausente na coluna 'Conta' (linha 2 do arquivo).
```

Nos dois casos o código de saída foi `1` e o arquivo de destino não foi criado.

Outras regras úteis:

- a primeira linha é o cabeçalho; um BOM UTF-8 no começo do arquivo é aceito;
- linha totalmente vazia é ignorada;
- `Cartao` sem til, ou `nome` em minúsculas, gera uma dica com o nome exato da coluna;
- a saída substitui o arquivo anterior só depois que a escrita termina (um `.tmp` é trocado no lugar).

Ajuda:

```bash
python3 -m etl_santander --help
```

## Testes

Na pasta do repositório. No Windows, troque `python3` por `py -3`.

```bash
python3 -m unittest discover -s tests -v
```

Execução nesta máquina (Python 3.12.3):

```text
Ran 20 tests in 0.077s

OK
```

A suíte cobre, entre outros pontos:

- nomes com acento, cedilha e apóstrofo (`João Conceição`, `Márcia Álvarez`, `Lúcia d'Ávila`);
- coluna obrigatória ausente e valor vazio, com o número da linha;
- identificadores preservados, inclusive zeros à esquerda (`00012340`) e máscara com espaços internos;
- ida e volta: gravar, ler de novo e gravar outra vez produz os mesmos bytes;
- o exemplo versionado é idêntico a uma execução nova;
- o CLI avisa que o modo é template, não IA, e devolve código `1` quando a validação falha.

Não há teste contra a API da Santander nem contra a OpenAI, porque o programa não fala com elas.

## Limitações

- Serve para uma planilha pequena, lida inteira na memória. Não é um ETL de produção nem um pipeline agendado.
- O separador é a vírgula. O Excel em português costuma exportar com ponto e vírgula; nesse caso o programa explica o que ajustar, em vez de adivinhar o dialeto.
- Não valida dígito de conta ou de cartão. Os identificadores são texto opaco, de propósito.
- Linhas duplicadas são processadas uma a uma. Não há cadastro único de cliente.
- A frase depende da posição da linha, não de um perfil financeiro. Não há saldo na entrada.
- A saída usa LF. Isso é estável entre sistemas; alguns editores do Windows mostram tudo em uma linha só se não entenderem LF, e outros mostram normal.
- O modo generativo do notebook original não está implementado. Incluí-lo seria opcional e externo a este fluxo; o resultado deste repositório não depende disso.
- Nada aqui substitui orientação de um profissional. As mensagens são material educativo genérico sobre poupar e planejar.

## O que este repositório não faz

- Não consulta `https://sdw-2023-prd.up.railway.app` e não envia `PUT`.
- Não gera texto com IA e não guarda segredo de API.
- Não usa dado real de cliente, conta ou cartão.
- Não promete rentabilidade e não recomenda investimento.
