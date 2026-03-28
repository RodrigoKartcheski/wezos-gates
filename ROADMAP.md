# RoadMap - SentinelGate (Data Quality Framework) 🚀

Completamos com sucesso o refactor de nível Staff Engineer no SentinelGate. O sistema agora não é apenas funcional, ele é arquiteturalmente sólido, modular e escalável.

Aqui estão os próximos passos recomendados para elevar o SentinelGate ao patamar de ferramentas como Great Expectations ou Monte Carlo:

## 1. Próximos Passos Imediatos (Hands-on)
- **1.1 - DuckDB Engine**: Implementar o `DuckDBExecutionEngine` para processar arquivos Parquet/CSV de 10GB+ com Zero-copy.
- **1.2 - Data Remediation (Auto-Fix)**: Criar regras de "cura" (ex: `strip_whitespace`, `fill_na`) para limpar os dados automaticamente durante a validação.
- **1.3 - dbt Connector**: Importar configurações de `schema.yml` do dbt diretamente para contratos SentinelGate.

## 2. Expansão de Inteligência (AI & Governance)
- **2.1 - AI Rule Suggestion**: Interface com LLM (Gemini/GPT-4) para sugerir regras de qualidade baseadas no perfil do dado.
- **2.2 - Advanced Drift Analysis**: Integração com **EvidentlyAI** para monitoramento estatístico avançado de desvios.
- **2.3 - Responsible AI (Bias Detection)**: Detecção de desequilíbrios em dados sensíveis (Gênero, Etnia, Idade).

## 3. Observabilidade & Interface
- **3.1 - Quality History (SQLite)**: Persistência de resultados para acompanhar a evolução da qualidade ao longo do tempo.
- **3.2 - SentinelGate UI (Streamlit)**: Dashboard interativo para configuração e visualização de relatórios sem terminal.
- **3.3 - Parallel Execution**: Suporte a processamento paralelo de chunks para datasets de altíssimo volume.

## 4. Infraestrutura & Cloud
- **4.1 - GitHub Actions**: Automatização de testes e build do `.exe` por release.
- **4.2 - Cloud Connectors**: Leitura nativa de S3, GCS e Azure Blob Storage em `datasource.py`.