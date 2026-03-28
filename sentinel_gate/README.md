# SentinelGate (Data Quality Framework) 💎

## Visão Geral

O **SentinelGate** é um framework modular de **Data Quality & Observability**, projetado para:

- Validar arquivos CSV ou tabelas BigQuery em escala corporativa.
- Suportar execução via **CLI** ou **Módulo Python**.
- Integrar com **IA via MCP server** para análises assistidas.
- Gerar relatórios **100% visuais em HTML** agrupados em um dashboard central.
- Calcular o **Data Quality Score** técnico e semântico.

Ideal para arquiteturas de dados com camadas **RAW → TRUSTED → REFINED**.

---

## 🏗️ Estrutura do Projeto (Staff-Tier)

O framework segue uma separação rigorosa de responsabilidades:

```
sentinel_gate/
├── core/                # Regras de Negócio & Relatórios
├── engines/             # Camada de Execução (Pandas, Future Spark)
├── contracts/           # Contratos de Dados & Drift
├── discovery/           # Descoberta & Análise Exploratória
├── execution/           # Orquestração & Fontes de Dados
├── interfaces/          # CLI & MCP Server
└── utils/               # Helpers (SQL, Logging, OS)
```

---

## 🛠️ Instalação e Execução

### Requisitos
- Python 3.10+
- `pip install -r requirements.txt`

### Como Rodar (Recomendado)
Execute o framework como um módulo Python:
```bash
python -m sentinel_gate --config samples/seu_config.json --output reports/
```

### Gerar Executável (Windows)
Para gerar um binário `.exe`:
```bash
powershell .\build_exe.ps1
```
O arquivo será gerado em: `dist/sentinel_gate.exe`.

---

## Funcionalidades Principais

- **Inferência Automática de Tipos**: boolean, integer, float, datetime, string, categorical.
- **Validações Técnicas**:
  - **Schema Drift**: Mudanças estruturais entre o esperado e o real.
  - **Integridade**: Nulos, unicidade (PK), PKs compostas.
  - **Domínio**: Listas permitidas, regex personalizados.
  - **Numéricas**: Min/Max, Outliers (Z-Score/IQR).
  - **Avançadas**: Cross-column formulas (AST-Safe), Lookups em fontes externas.
- **Auditoria de Negócio (Discovery)**:
  - Detecção automática de candidatos a PK.
  - Análise de cardinalidade e distribuição temporal.
  - Verificação de duplicidade técnica vs. semântica.
- **Profiling estatístico** profundo com `ydata-profiling`.

---

## 📊 Relatórios Consolidados

O SentinelGate centraliza todos os resultados na pasta `/reports` com um dashboard interativo:

1. **`dashboard.html`**: Resumo executivo e técnico.
2. **`report_schema.html`**: Auditoria de tipos e drift.
3. **`report_validations.html`**: Detalhamento microscópico das regras de DQ.
4. **`report_discovery.html`**: Insights de negócio e chaves candidatas.
5. **`report_profiling.html`**: Profiling estatístico profundo.

---

## 🧪 Desenvolvimento Local

Para rodar a suíte de testes de regressão:
```powershell
$env:PYTHONPATH="."
python -m unittest discover sentinel_gate/tests
```
