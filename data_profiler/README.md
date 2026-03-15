# Data Quality Executable – data-profiler

## Visão Geral

O **Data Quality Executable (data-profiler.exe)** é uma ferramenta modular para **validação e profiling de datasets**, projetada para:

- Validar arquivos CSV ou tabelas BigQuery
- Suportar execução via **CLI** (para humanos)
- Integrar com **IA via MCP server**
- Gerar relatórios **100% visuais em HTML**
- Calcular **Data Quality Score**

A ferramenta é especialmente útil em arquiteturas de dados com camadas **RAW → TRUSTED → REFINED**.

---

## Funcionalidades Principais

- Inferência automática de tipos: boolean, integer, float, datetime, string, categorical
- Validações:
  - Schema: colunas obrigatórias, tipos, colunas extras/faltantes (**Schema Drift**)
  - Nulos: not null, max percent null
  - Unicidade: primary key, unique, composite keys
  - Cardinalidade: min/max distinct, distinct count
  - Domínio: allowed/forbidden values, regex
  - Numéricas: min, max, outliers
  - Volume: min/max rows
  - Agregações: group by, count, sum, avg, min, max
- Profiling automático com [ydata-profiling](https://github.com/ydataai/ydata-profiling)
- Geração de relatórios visuais (HTML):
  - `report_schema.html`: Análise de schema e tipos.
  - `report_validations.html`: Dashboard de regras de qualidade.
  - `report_profiling.html`: Profiling profundo (distribuições, correlações).

---

## Instalação

### Requisitos

- Python 3.10+
- Bibliotecas listadas em `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Build do Executável
```bash
bash build_exe.sh
```

O executável será gerado em:
`dist/data-profiler.exe`

---

## Modos de Execução

### CLI (Humano)

Parâmetros principais:

| Parâmetro | Tipo | Descrição |
| :--- | :--- | :--- |
| --source | csv ou bigquery | Origem dos dados |
| --file | string | Caminho do CSV |
| --project | string | Projeto BigQuery |
| --dataset | string | Dataset BigQuery |
| --table | string | Tabela BigQuery |
| --columns | lista | Colunas específicas a validar |
| --where | string | Filtro SQL opcional |
| --config | string | Arquivo JSON de regras |
| --check-nulls | lista | Colunas para checar nulos |
| --group-by | lista | Colunas para agregações |
| --agg | lista | Funções de agregação (count, sum, avg, min, max) |
| --limit | int | Limite de linhas para teste |
| --output | string | Pasta para salvar relatórios |
| --mcp | bool | Ativa modo MCP server para IA |

#### Exemplo CSV
```bash
data-profiler.exe \
--source csv \
--file sample/clientes.csv \
--check-nulls email,telefone \
--group-by status \
--agg count,sum \
--output reports/
```

### Saída do Executável

O executável gera 5 arquivos HTML na pasta de output:

```text
reports/
├── dashboard.html                    <-- Fácil acesso (Sempre o mais recente)
├── 2026-03-13_17h50_dashboard.html   <-- Histórico com timestamp
├── 2026-03-13_17h50_report_schema.html
├── 2026-03-13_17h50_report_validations.html
└── 2026-03-13_17h50_report_profiling.html
```

- **Unified Dashboard**: O arquivo `dashboard.html` é o ponto de entrada principal que contém as abas navegáveis.
- **Histórico**: Os arquivos com timestamp são mantidos para auditoria e histórico de execuções passadas.

---

## MCP Server (Integração IA)

Ativar:
```bash
data-profiler.exe --mcp
```

Ferramentas disponíveis: `load_dataset`, `infer_schema`, `run_validation`, `profile_dataset`.

---

## Arquivo de Configuração JSON

```json
{
  "source": { "type": "csv", "file": "clientes.csv" },
  "validations": {
    "primary_key": ["id_cliente"],
    "null_checks": [{ "column": "email", "max_percent": 0 }]
  }
}
```

Executar:
```bash
data-profiler.exe --config rules.json --output reports/
```

---

## Boas Práticas

1. **Validar RAW primeiro** para garantir tipos e detectar drift precocemente.
2. **Histórico**: Armazene os relatórios HTML em pastas datadas para auditoria de regressão.
3. **Dashboards**: Integre os links dos HTMLs em seus portais de monitoramento de dados.

---

## Contato e Suporte

**Time de Engenharia de Dados**
**Git Issues**: [repo-link]

Abrir o README.md
start .\data_profiler\README.md


Rodar o executavel
.\data-profiler.exe --source csv --file sample_data.csv --output reports/

.\data-profiler.exe --source csv --config seu_config.json --output reports

start reports/dashboard.html

exemplos de json:
-- source csv
{
  "file": "repro_data.csv",
  "group_by": ["category"]
}

-- source bigquery
{
  "project": "your-project",
  "dataset": "your-dataset",
  "table": "your-table"
}

-- source bigquery
{
  "project": "your-project",
  "dataset": "your-dataset",
  "table": "your-table",
  "group_by": ["category"]
}

-- source bigquery com referencia
{
  "project": "your-project",
  "dataset": "your-dataset",
  "table": "your-table",
  "reference": {
    "project": "your-project",
    "dataset": "your-dataset",
    "table": "your-table"
  }
}

# TESTE LOCAL
$env:PYTHONPATH = "c:\Temp\wezos-gates"
python c:\Temp\wezos-gates\data_profiler\interfaces\cli.py --source csv --config c:\Temp\wezos-gates\seu_config.json --output c:\Temp\wezos-gates\reports_test
