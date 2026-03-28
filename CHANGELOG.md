# Changelog - SentinelGate (Data Quality Framework) 🧬

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo, seguindo os princípios de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [3.5.0] - 2026-03-28 (Staff-Tier Refactor)

### Adicionado 🚀
- **SentinelGate Branding**: Transição oficial de `data-profiler` para `SentinelGate`.
- **Pydantic Contracts**: Implementação de validação de configuração rigorosa usando Pydantic V2 em `config/models.py`.
- **Suporte Multi-Formato (YAML/JSON)**: O framework agora suporta contratos de dados em YAML, permitindo comentários e maior legibilidade.
- **Hierarquia Modular**: Nova estrutura de pacotes (`core`, `engines`, `contracts`, `discovery`, `execution`).
- **Abstração de Engines**: Introdução da `BaseExecutionEngine` para desacoplar lógica de validação do motor de processamento (Pandas).
- **Guia Multi-Engine**: Nova documentação técnica para suporte futuro a Spark e DuckDB.
- **Suite de Testes de Configuração**: Novos testes para garantir integridade dos contratos JSON.
- **Novo Entry Point**: Suporte oficial para execução via `python -m sentinel_gate`.

### Alterado 🛠️
- **ValidationEngine**: Refatorado para usar o padrão de delegação via `ExecutionEngine`.
- **ResultCollector**: Desacoplado da engine de validação para garantir imutabilidade de estado.
- **Localização de Arquivos**: Centralização de relatórios em `/reports` e exemplos em `/samples`.
- **Scripts de Build**: Atualizados para gerar `sentinel_gate.exe` com os novos entry points.

### Corrigido 🐛
- **State Leakage**: Corrigido problema onde resultados de execuções anteriores podiam vazar entre instâncias do engine.
- **Alias de Resultados**: Restaurada propriedade `.results` no `ValidationEngine` para compatibilidade com integrações legadas.
- **Import Error**: Resolvido erro circular ao inicializar o pacote `engines`.

---

## [3.0.0] - Versão Anterior (Legacy)
- Versão monolítica baseada exclusivamente em Pandas.
- Configuração validada via dicionários e lógica manual em `config_parser.py`.
- Relatórios dispersos no diretório raiz.
