# Guia de Uso: SentinelGate (Data Quality Platform) 🧬

O **SentinelGate** é uma plataforma modular de Data Quality de nível corporativo. Ele permite validar a integridade de dados, detectar drifts e realizar descobertas exploratórias em CSV e BigQuery de forma performática (multicore).

---

## 🚦 Portas de Entrada (Trindade de Uso)

Você pode interagir com o framework de três maneiras, dependendo da necessidade:

### 1. 🎨 SentinelGate Studio (Visual / Low-Code)
Ideal para exploração, configuração visual e usuários não-técnicos.
```bash
streamlit run sentinel_gate/app.py
```
- **Recursos**: Upload de CSV, botão "Sugestão Mágica" (Auto-Discovery), exportação de JSON e gráficos de tendência de score.

### 2. ⌨️ CLI (Automação / CI-CD)
Ideal para rodar em Airflow, GitHub Actions ou scripts agendados.
```bash
python -m sentinel_gate --config contrato.json --output reports/
```
- **Opções de Histórico**:
  - `--save-history`: Ativa o registro no banco de dados SQLite.
  - `--no-history`: Desativa o registro (Padrão para evitar poluição).

### 3. 🤖 MCP Server (Agentes de IA)
Permite que IAs (Claude/GPT) executem o framework de forma autônoma.
```bash
python -m sentinel_gate --mcp
```

---

## 🏛️ Observabilidade e Persistência

O SentinelGate utiliza um banco de dados **SQLite** (`sentinel_gate/history.db`) para armazenar o histórico de execuções.

- **Fase 1**: Monitoramento de tendência de score.
- **Gráficos**: Visíveis via **SentinelGate Studio** na aba "Histórico".
- **Default**: O histórico vem **DESATIVADO** por padrão para garantir privacidade em rodadas de teste. Use `--save-history` no CLI ou marque o checkbox no Studio para persistir.

---

## 🛠️ Configuração do Contrato (JSON/YAML)

O contrato define a inteligência do pipeline. Abaixo as seções principais:

### 1. Origem (`source`)
| Campo | Descrição | Exemplo |
| :--- | :--- | :--- |
| `type` | `csv` ou `bigquery` | `"csv"` |
| `file` | Caminho do arquivo | `"samples/vendas.csv"` |
| `chunk_size` | Tamanho do pedaço para processamento em RAM baixa | `5000` |
| `parallel_workers` | Número de CPUs para processamento paralelo | `4` |

### 2. Validações (`validations`)
```json
"validations": {
  "null_checks": [{ "column": "id", "mandatory": true }],
  "numeric_checks": [{ "column": "preco", "min": 0 }]
}
```

---

## 🧪 Verificação Técnica

Para rodar os testes de engenharia e garantir que a instalação está correta:
```bash
$env:PYTHONPATH="."; python -m unittest discover sentinel_gate/tests
```

O sistema agora é **Modular**, **Paralelo** e **Auditável**.
