# Guia de Uso: data-profiler (Data Quality Executable)

Este documento descreve todas as possibilidades de configuração e uso do pacote `data-profiler`. A ferramenta é projetada para validar a qualidade dos dados e realizar descobertas exploratórias em arquivos CSV ou tabelas BigQuery.

---

## 🚀 Como Iniciar

A configuração principal é feita através de um arquivo JSON (como o `seu_config.json`). Você pode executar a ferramenta apontando para este arquivo:

```bash
.\data-profiler.exe --config seu_config.json --output reports/
```

---

## 🛠️ Estrutura do Arquivo de Configuração (JSON)

O arquivo de configuração é dividido em seções principais. Abaixo, detalhamos cada uma delas.

### 1. Origem dos Dados (`source`)
Define de onde os dados serão lidos. Pode ser configurado na raiz do JSON ou dentro de um objeto `"source"`.

| Campo | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `type` | string | `csv` ou `bigquery` | `"csv"` |
| `file` | string | Caminho do arquivo (se for CSV) | `"dados.csv"` |
| `sep` | string | Separador do CSV (padrão: `,`) | `";"` |
| `encoding`| string | Codificação (padrão: `utf-8`) | `"latin1"` |
| `project` | string | ID do projeto no Google Cloud (BQ) | `"v-projeto"` |
| `dataset` | string | Nome do dataset no BigQuery | `"v-dataset"` |
| `table` | string | Nome da tabela no BigQuery | `"v-tabela"` |

---

### 2. Validações de Qualidade (`validations`)
Esta seção define as regras de "saúde" dos dados. 

**Novidade**: Agora você pode usar a flag `"mandatory": true/false` (padrão: `true`). Se uma regra for `false` e falhar, ela gerará apenas um **WARN** no relatório, sem invalidar o pipeline completo.

```json
"validations": {
  "primary_key": { "columns": ["id"], "mandatory": true }, // Unicidade obrigatória
  "null_checks": [
    { "column": "email", "max_percent": 0.5, "mandatory": false } // Aviso se falhar
  ],
  "domain_checks": [
    { 
      "column": "status", 
      "allowed_values": ["ATIVO", "INATIVO"],
      "mandatory": true 
    }
  ],
  "numeric_checks": [
    { "column": "valor", "min": 0, "mandatory": true }
  ],
  "volume_checks": {
    "min_rows": 100,
    "mandatory": true
  },
  "outlier_checks": { "columns": ["*"], "mandatory": false }, // Apenas informativo
  "empty_string_checks": { "columns": ["nome"], "mandatory": true }
}
```

---

### 3. Descoberta de Dados (`discovery`)
Focada em metadados e análise exploratória.

```json
"discovery": {
  "filter": "idade > 18 AND status = 'ATIVO' AND nome LIKE 'A%'", // Filtro SQL para análise exploratória
  "detect_keys": true,                   // Tenta encontrar chaves primárias automaticamente
  "group_by": ["categoria", ["uf", "cidade"]], // Gera frequências para colunas ou grupos
  "date_analysis": ["data_venda"],       // Analisa distribuição temporal e datas máximas
  "dedupIncludeColumns": ["cpf"],        // Checa duplicidade considerando APENAS estas colunas
  "dedupExcludeColumns": ["id", "data"]  // Checa duplicidade considerando TODAS exceto estas
}
```

---

### 4. Profiling (`profiling`) e Drift
- **Profiling**: Gera um relatório profundo de distribuições e correlações usando `ydata-profiling`.
- **Reference**: Permite comparar o dataset atual com uma versão de referência para detectar **Data Drift** (mudança estatística nos dados).

```json
"profiling": {
  "title": "Perfil de Clientes 2024",
  "filter": "data > '2024-01-01'"
},
"reference": {
  "type": "csv",
  "file": "dados_ontem.csv"
}
```

---

## 💻 Interface de Linha de Comando (CLI)

Além do JSON, você pode passar parâmetros diretamente no terminal:

- `--source`: `csv` ou `bigquery`
- `--file`: Caminho do arquivo CSV
- `--project`, `--dataset`, `--table`: Credenciais BigQuery
- `--check-nulls`: Lista de colunas separadas por vírgula
- `--group-by`: Colunas para frequência
- `--output`: Pasta onde os relatórios HTML serão salvos

**Exemplo Rápido:**
```bash
.\data-profiler.exe --source csv --file sample.csv --check-nulls email --output reports/
```

---

## 📊 Relatórios Gerados

A ferramenta gera um dashboard interativo único:
1. `dashboard.html`: Ponto de entrada central.
2. `report_schema.html`: Análise de tipos e drift de schema.
3. `report_validations.html`: Resultados detalhados de cada regra de DQ.
4. `report_discovery.html`: Chaves candidatas, duplicatas e grupos.
5. `report_profiling.html`: Estatísticas profundas da biblioteca de profiling.

---

## 🧠 Integração com IA (MCP Server)

Se estiver usando um assistente de IA, você pode ativar o modo MCP para que a IA execute análises diretamente:

```bash
.\data-profiler.exe --mcp
```
