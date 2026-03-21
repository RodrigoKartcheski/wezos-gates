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

## 🛠️ Instalação e Build

### Requisitos
- Python 3.10+
- Bibliotecas listadas em `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Gerar Executável (Windows)
Para gerar o seu `.exe` localmente, execute o script de build:
```bash
bash build_exe.sh
```
O arquivo será gerado em: `dist/data-profiler.exe`.

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

> [!IMPORTANT]
> **Integrated Trust Workflow**: Agora, o Discovery e as Análises Analíticas são realizados **apenas nos dados que passaram nas validações obrigatórias** (`mandatory: true`). Isso garante que os seus insights de BI (médias, contagens por loja, deduplicação) não sejam poluídos por registros tecnicamente inválidos que não deveriam estar no dataset final.

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

## 📖 Detalhamento de Funções & Exemplos de Uso

Abaixo, explicamos o que cada bloco de configuração faz e como usá-lo para garantir a integridade dos seus dados.

### 🛡️ Seção: Validações (`validations`)
O objetivo aqui é garantir a **integridade técnica** do dataset.

| Função | Descrição | Exemplo de JSON |
| :--- | :--- | :--- |
| `primary_key` | Valida se uma ou mais colunas formam uma chave única sem duplicatas. | `"primary_key": ["id", "loja"]` |
| `null_checks` | Checa nulos em colunas críticas. Suporta `max_percent` (ex: 0.1 = 10%). | `{"column": "email", "max_percent": 0.05}` |
| `domain_checks`| Garante que os valores de uma coluna estejam em uma lista permitida. | `{"column": "status", "allowed_values": ["A", "B"]}` |
| `numeric_checks`| Valida faixas de valores (mínimo e máximo) para colunas numéricas. | `{"column": "valor", "min": 0, "max": 1000}` |
| `outlier_checks`| Identifica valores fora da curva (Z-Score > 3). Útil para capturar erros de digitação. | `"outlier_checks": {"columns": ["*"], "mandatory": false}` |
| `date_check` | Valida se o formato da data é consistente com o esperado (ex: YYYY-MM-DD). | `{"column": "data_venda", "format": "%Y-%m-%d"}` |
| `duplicate_check`| Checa se existem linhas no dataset que são duplicatas exatas de outras. | `"duplicate_check": true` |

> [!TIP]
> Use `"mandatory": false` em regras secundárias (como outliers) para gerar apenas alertas (**WARN**) sem derrubar o score técnico global.

---

### 🔍 Seção: Descoberta (`discovery`)
O objetivo aqui é extrair **insights analíticos** e garantir a **confiança semântica**.

| Função | Descrição | Exemplo de JSON |
| :--- | :--- | :--- |
| `detect_keys` | O motor usa IA para sugerir possíveis chaves primárias que você ainda não mapeou. | `"detect_keys": true` |
| `group_by` | Gera a distribuição (frequência) de valores para entender a volumetria de negócio. | `"group_by": ["status", "loja"]` |
| `filter` | Aplica um filtro SQL (WHERE) antes de realizar as análises exploratórias. | `"filter": "idade > 30"` |
| `dedupIncludeColumns`| **Auditoria Semântica**: Verifica se há duplicidade considerando apenas colunas de negócio (ex: CPF). | `"dedupIncludeColumns": ["cpf"]` |
| `date_analysis` | Analisa a distribuição das datas e identifica a data máxima (Max Date) do dataset. | `"date_analysis": ["data_cadastro"]` |

> [!IMPORTANT]
> **Trust Integrado**: Se uma linha falhar em uma validação técnica `"mandatory": true`, ela é **automaticamente excluída** das análises de Discovery. Isso evita que insights de BI sejam gerados em cima de dados "sujos".

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

## 📊 Relatórios Modulares (Comportamento Dinâmico)

O `data-profiler` utiliza uma abordagem de **renderização modular**. Isso significa que o relatório final (`report_validations.html` e `report_discovery.html`) só exibirá as seções que foram explicitamente configuradas no seu JSON.

- **Seção Omitida no JSON**: Se você não definir `volume_checks`, essa tabela não aparecerá no relatório, mantendo-o limpo e focado no que importa para aquela análise específica.
- **Discovery Básico**: Por padrão, o motor sempre exibe estatísticas de cardinalidade (`Distinct Values Count`) para dar contexto, mas análises avançadas (PK Detection, Deduplicação, Grupos) só aparecem se as chaves correspondentes forem ativadas.

---

## 📊 Relatórios Gerados

A ferramenta gera um dashboard interativo único:
1. `dashboard.html`: Ponto de entrada central.
2. `report_schema.html`: Análise de tipos e drift de schema.
3. `report_validations.html`: Resultados detalhados de cada regra de DQ.
4. `report_discovery.html`: Chaves candidatas, duplicatas e grupos.
5. `report_profiling.html`: Estatísticas profundas da biblioteca de profiling.

---

```bash
.\data-profiler.exe --mcp
```

---

## 🧪 Desenvolvimento Local (Teste)

Para rodar o motor via código (Powershell) e validar alterações rapidamente sem precisar do build:

```powershell
$env:PYTHONPATH = "c:\Temp\wezos-gates"
python .\data_profiler\interfaces\cli.py --source csv --config .\seu_config_v6.json --output .\reports_test
```
