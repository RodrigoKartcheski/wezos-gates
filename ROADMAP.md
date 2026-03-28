# RoadMap - SentinelGate (Data Quality Framework) 🚀

Completamos com sucesso o refactor de nível Staff Engineer no SentinelGate. O sistema agora não é apenas funcional, ele é arquiteturalmente sólido, modular e escalável.

Aqui estão os próximos passos recomendados para elevar o SentinelGate ao patamar de ferramentas como Great Expectations ou Monte Carlo:

## 1. Próximos Passos Imediatos (Hands-on)
- **1.1 - DuckDB Engine**: Implementar o `DuckDBExecutionEngine` para processar arquivos Parquet/CSV de 10GB+ sem estourar a memória (usando Zero-copy).
- **1.2 - Data Chunking**: Adicionar suporte a processamento em pedaços (chunks) no `PandasExecutionEngine` para datasets maiores que a RAM disponível.
- **1.3 - Pydantic Evolution**: Expandir modelos para suportar validação de arquivos de configuração em YAML além de JSON.

## 2. Expansão de Inteligência
- **2.1 - Advanced Drift Analysis**: Integrar profundamente o `sentinel_gate/core/drift.py` com a biblioteca **EvidentlyAI** para detectar mudanças no comportamento estatístico das colunas ao longo do tempo.
- **2.2 - Análise de Viés (Bias Detection)**: Criar regras de validação para detectar desequilíbrios em dados sensíveis (Gênero, Etnia, etc.).

## 3. Infraestrutura & DevOps
- **3.1 - GitHub Actions**: Criar um workflow de CI que rode os testes automaticamente e gere o `.exe` como artifact.
- **3.2 - Cloud Native**: Adicionar conectores em `execution/datasource.py` para ler diretamente de S3 e Azure Blob Storage.