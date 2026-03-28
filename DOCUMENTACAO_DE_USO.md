# Guia de Uso: SentinelGate (Data Quality Framework)

Este documento descreve as possibilidades de configuração e uso do framework `SentinelGate`. A ferramenta é projetada para validar a qualidade dos dados, detectar drift de schema e realizar descobertas exploratórias em arquivos CSV ou tabelas BigQuery, seguindo padrões de engenharia de software de nível corporativo.

---

## 🚀 Como Iniciar

A configuração principal é feita através de um arquivo JSON. Você pode executar o framework de três formas:

### 1. Como Módulo Python (Recomendado)
```bash
python -m sentinel_gate --config seu_config.json --output reports/
```

### 2. Via Executável (Windows)
Se você gerou o binário via PyInstaller:
```bash
.\sentinel_gate.exe --config seu_config.json --output reports/
```

### 3. Modo Interativo (IA / MCP)
Para integrar com assistentes como o Claude/Cursor:
```bash
python -m sentinel_gate --mcp
```

---

## 🏗️ Arquitetura Modular (Staff-Tier)

O `SentinelGate` é organizado em domínios isolados para máxima extensibilidade:

- **`core/`**: Motor de validações, scoring de qualidade e geração de relatórios SQL-like.
- **`engines/`**: Camada de execução desacoplada (atualmente suporta Pandas, preparado para Spark/DuckDB).
- **`contracts/`**: Gestão de contratos de dados, inferência de tipos e detecção de Schema Drift.
- **`discovery/`**: Ferramentas exploratórias para detecção de chaves primárias e análise de cardinalidade.
- **`execution/`**: Orquestrador de workflow e abstração de fontes de dados (Datasource).

---

## 🛠️ Estrutura do Arquivo de Configuração (JSON)

O arquivo de configuração é dividido em seções principais.

### 1. Origem dos Dados (`source`)
| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `type` | string | `csv` ou `bigquery` | `"csv"` |
| `file` | string | Caminho do arquivo (se for CSV) | `"samples/dados.csv"` |
| `project` | string | ID do projeto no Google Cloud (BQ) | `"projeto-prod"` |
| `dataset` | string | Nome do dataset no BigQuery | `"raw_layer"` |
| `table` | string | Nome da tabela no BigQuery | `"vendas"` |

---

### 2. Validações de Qualidade (`validations`)
Seção que define as regras de integridade. Use `"mandatory": false` para gerar apenas alertas (**WARN**) sem derrubar o score técnico global.

```json
"validations": {
  "primary_key": { "columns": ["id"], "mandatory": true },
  "null_checks": [
    { "column": "email", "max_percent": 0.1, "mandatory": false }
  ],
  "domain_checks": [
    { "column": "status", "allowed_values": ["ATIVO", "INATIVO"] }
  ],
  "numeric_checks": [
    { "column": "valor", "min": 0 }
  ],
  "comparison_checks": [
    { "equation": "preco * qtd == total" }
  ],
  "lookup_checks": [
    { "column": "customer_id", "reference_source": {"table": "customers"}, "reference_column": "id" }
  ]
}
```

---

### 3. Descoberta e Auditoria (`discovery`)
Insights analíticos realizados **apenas nos dados que passaram nas validações obrigatórias**.

```json
"discovery": {
  "filter": "status = 'ATIVO'",          // Filtro SQL para descoberta
  "detect_keys": true,                   // Sugestão automática de PKs
  "group_by": ["categoria"],             // Frequência de valores
  "dedupIncludeColumns": ["cpf"]         // Auditoria de duplicidade semântica
}
```

---

## 📊 Relatórios Consolidados

Os resultados são centralizados na pasta `/reports` em um dashboard único:

1. **`dashboard.html`**: Painel central unificado.
2. **`report_validations.html`**: Detalhamento técnico das regras de DQ.
3. **`report_discovery.html`**: Insights analíticos e chaves candidatas.
4. **`report_schema.html`**: Metadados e análise de Drift.
5. **`report_profiling.html`**: Perfil estatístico profundo.

---

## 🧪 Desenvolvimento e Testes

Para rodar a suíte de testes corporativa:
```bash
$env:PYTHONPATH="."; python -m unittest discover sentinel_gate/tests
```

Se estiver usando um assistente de IA, você pode ativar o modo MCP para que a IA execute análises diretamente:

```bash
python -m sentinel_gate --mcp
```
