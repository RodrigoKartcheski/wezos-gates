# Funcionalidades: SentinelGate (Data Quality Framework) 💎

O SentinelGate oferece uma suíte completa de ferramentas para auditoria, validação e observabilidade de dados. Abaixo detalhamos as funcionalidades divididas por seus respectivos módulos arquiteturais.

---

## 🏗️ 1. Módulo de Validação (`core.validation`)
Focado na "saúde" técnica e conformidade dos dados.

- **Check de Nulos**: Validação binária (Not Null) ou volumétrica (`max_percent` tolerado).
- **Unicidade**: Suporte a chaves primárias (`PK`) simples e compostas.
- **Domínio**: Validação contra listas de valores permitidos (`allowed_values`) ou proibidos (`forbidden_values`).
- **Padrões de Texto (Regex)**: Validação de formatos customizados (Ex: CPFs, E-mails, IDs internos).
- **Numéricas**: Faixas de valores (`min`/`max`) e detecção de negativos não autorizados.
- **Comparação entre Colunas**: Fórmulas customizadas (Ex: `A + B == C`) validadas via motor **AST-Safe** (Impede execução de código malicioso).
- **Lookups Externos**: Cruzamento de dados com tabelas de referência externas para garantir integridade referencial.
- **Unidades e Magnitudes**: Validação de escalas e grandezas (Ex: Peso em KG dentro de margens lógicas).

---

## 🔍 2. Módulo de Descoberta (`discovery`)
Focado em extrair arquitetura oculta e insights semânticos.

- **PK Detection**: Algoritmo iterativo que sugere a melhor combinação de colunas para formar uma chave única.
- **Deduplicação Inteligente**: Separação entre duplicidade técnica (linhas idênticas) e semântica (duplicação baseada em chaves de negócio).
- **Análise Temporal**: Identificação automática de janelas de tempo e `Max Date` do dataset.
- **Distribuição de Grupos**: Análise de frequência para detecção de desbalanceamento de classes em colunas categóricas.
- **Cardinalidade**: Monitoramento de valores distintos por coluna.

---

## 📜 3. Módulo de Contratos e Drift (`contracts`)
Focado na estabilidade do pipeline ao longo do tempo.

- **Inferência de Tipos**: Motor inteligente que detecta tipos (boolean, integer, float, date, category) mesmo em campos de texto.
- **Schema Drift**: Alertas imediatos caso o dataset de entrada mude de estrutura (novas colunas, colunas faltando ou mudança de tipo).
- **Data Drift**: Identificação de mudanças estatísticas significativas no perfil dos dados em comparação com um dataset de referência.

---

## 📊 4. Módulo de Relatórios e Scoring (`core.report` & `core.scoring`)
Transforma dados técnicos em informações executivas.

- **Dashboard Unificado**: Painel centralizado que agrupa todas as métricas em uma única visão.
- **DQ Score Técnico**: Pontuação de 0 a 100 baseada no cumprimento das regras de integridade configuradas.
- **Resultados Visuais**: Relatórios HTML interativos com tabelas filtráveis e status color-coded.
- **Integrated Trust Workflow**: Garantia de que as análises analíticas (Profiling) só utilizam dados que passaram nas validações de integridade.

---

## 🤖 5. Interface MCP e CLI
Facilidade de uso para humanos e IAs.

- **CLI robusta**: Suporta configuração via JSON ou parâmetros de terminal.
- **MCP Server**: Permite que agentes de IA (como Claude e ChatGPT) "enxerguem" e analisem seus dados diretamente.

---

## 🚀 Próximos Passos (Multi-Engine)
O SentinelGate está preparado para crescer além do Pandas. Confira nosso **[Guia de Multi-Engine](multi_engine.md)** para entender como implementar suporte a Spark, DuckDB e outros motores de Big Data.
