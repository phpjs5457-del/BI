# Goiás BI — Inteligência Fiscal Municipal

Dashboard interativo para explorar os repasses municipais de ICMS e IPVA em Goiás
no exercício de 2025. O projeto usa Python, Streamlit, Plotly e um banco SQLite.

> **Status acadêmico: versão provisória.** Os valores de ICMS e IPVA foram extraídos
> de abas diferentes da mesma pasta de trabalho. Se o trabalho exigir o cruzamento
> de duas bases públicas independentes, esta versão ainda não atende a esse requisito.
> A associação entre variáveis não demonstra causalidade.

## Conteúdo

- [O que o dashboard oferece](#o-que-o-dashboard-oferece)
- [Requisitos](#requisitos)
- [Instalação e execução no Windows](#instalação-e-execução-no-windows)
- [Como usar](#como-usar)
- [Dados e metodologia](#dados-e-metodologia)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Reimportar a planilha](#reimportar-a-planilha)
- [Problemas comuns](#problemas-comuns)
- [Próximas etapas](#próximas-etapas)

## O que o dashboard oferece

- Indicadores de quantidade de municípios e totais de ICMS e IPVA.
- Filtro interativo por município, aplicado aos indicadores, gráficos, tabela e arquivo CSV.
- Ranking dos até 20 maiores repasses de ICMS.
- Dispersão de IPVA e ICMS, reta de regressão linear simples, correlação de Pearson
  e coeficiente de determinação (R²).
- Simulador que estima o ICMS a partir de um valor de IPVA informado.
- Tabela detalhada e exportação dos dados selecionados para CSV.

## Requisitos

- Windows 10 ou superior.
- Python 3.10 ou superior disponível pelo inicializador `py`.
- Acesso à internet na primeira instalação das dependências.

O arquivo `requirements.txt` declara Streamlit, NumPy, pandas e Plotly.

## Instalação e execução no Windows

Abra o PowerShell na pasta `goias_bi_funcional` e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Não é necessário ativar o ambiente virtual. Quando o Streamlit iniciar, abra
[http://localhost:8501](http://localhost:8501) no navegador. Para encerrar, volte
ao terminal e pressione `Ctrl+C`.

Se a porta padrão já estiver ocupada, use outra:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502
```

## Como usar

1. Abra a aba **Visão geral** para consultar os totais e o ranking de ICMS.
2. Use o filtro **Municípios**, na barra lateral, para escolher a amostra.
3. Na aba **Relação estatística**, examine o gráfico de dispersão e as métricas.
4. Teste outro valor de IPVA no simulador. A estimativa é estatística, não oficial.
5. Na aba **Dados e metodologia**, consulte os valores e baixe o CSV filtrado.

## Dados e metodologia

### Fonte e unidade de análise

- **Fonte atual:** arquivo de Conciliação das Distribuições 2025, da Secretaria
  de Economia de Goiás.
- **Abas utilizadas:** `ICMS_Bolão.dez` e `IPVA_Bolão.dez`.
- **Unidade:** um registro por município e ano.
- **Chave:** código municipal e ano. O ETL também confere o nome do município entre
  as abas antes de gravar os registros.
- **Cobertura do banco fornecido:** 246 municípios, ano de 2025.

### Campos do banco

| Campo | Descrição |
|---|---|
| `codigo_municipio` | Código municipal como texto, para preservar zeros à esquerda |
| `municipio` | Nome do município |
| `ano` | Exercício do registro |
| `icms_20` | Componente de ICMS de 20% (R$) |
| `fundeb_icms_5` | Componente FUNDEB de ICMS de 5% (R$) |
| `icms_repassado` | Total anual de ICMS repassado (R$) |
| `ipva_40` | Componente de IPVA de 40% (R$) |
| `fundeb_ipva_10` | Componente FUNDEB de IPVA de 10% (R$) |
| `ipva_repassado` | Total anual de IPVA repassado (R$) |

O ETL carrega os acumulados anuais da aba de dezembro; não soma os valores mensais
novamente. Os valores monetários são persistidos com duas casas decimais.

### Análise estatística

- Variável explicativa `X`: IPVA repassado total.
- Variável resposta `Y`: ICMS repassado total.
- Modelo linear simples: `Y estimado = intercepto + inclinação × X`.
- A inclinação e o intercepto são ajustados por mínimos quadrados com `numpy.polyfit`.
- `r` é a correlação de Pearson e `R² = r²` para o modelo linear simples com intercepto.

Essa análise é observacional. Não controla outros fatores, não prova causalidade
e não deve ser usada como previsão oficial ou extrapolada sem validação.

## Estrutura do projeto

```text
goias_bi_funcional/
├── app.py                         # Dashboard Streamlit
├── etl.py                         # Importação e validação da planilha XLSX
├── requirements.txt               # Dependências Python
├── README.md                      # Documentação e instruções
├── dados/
│   └── Conciliacao_das_Distribuicoes-2025.xlsx  # Planilha de origem (se disponível)
└── saida/
    └── goias_bi.db                 # Banco SQLite incluído
```

O dashboard lê `saida/goias_bi.db` ao iniciar. A planilha de origem só é necessária
para reconstruir ou atualizar o banco.

## Reimportar a planilha

Coloque a planilha no diretório `dados` com o nome
`Conciliacao_das_Distribuicoes-2025.xlsx`. Na pasta do projeto, execute:

```powershell
.\.venv\Scripts\python.exe etl.py --arquivo dados/Conciliacao_das_Distribuicoes-2025.xlsx
```

Para salvar em outro caminho:

```powershell
.\.venv\Scripts\python.exe etl.py `
  --arquivo dados/Conciliacao_das_Distribuicoes-2025.xlsx `
  --banco saida/goias_bi.db
```

O ETL lê os dados diretamente da estrutura XLSX, valida a quantidade esperada de
municípios e confere a correspondência entre as abas antes de atualizar os registros
de 2025.

## Problemas comuns

### `py` não foi encontrado

Instale o Python para Windows e habilite o inicializador Python (`py`) durante a
instalação. Reabra o terminal e confirme com `py --version`.

### O Streamlit informa que o banco não foi encontrado

Confirme que `saida/goias_bi.db` existe na pasta do projeto. Se necessário,
reimporte a planilha seguindo a seção [Reimportar a planilha](#reimportar-a-planilha).

### A porta 8501 já está em uso

Inicie o dashboard em outra porta, por exemplo `8502`, conforme o comando na seção
de instalação.

### A importação informa quantidade inesperada ou aba ausente

Verifique se o arquivo é a planilha correta de 2025 e se as abas `ICMS_Bolão.dez`
e `IPVA_Bolão.dez` estão presentes. Não substitua o banco com uma planilha de
estrutura diferente sem antes conferir os dados.

## Próximas etapas

1. Selecionar uma segunda fonte pública oficial e independente, compatível por
   município e período (por exemplo, dados municipais de frota).
2. Registrar a origem, licença, data de obtenção e transformações dessa fonte.
3. Cruzar os dados por código municipal sempre que disponível e documentar ausências.
4. Refazer e validar a análise com a nova variável, incluindo análise de valores
   ausentes e observações influentes.
5. Preparar o relatório final com resultados, limitações e capturas do dashboard.
