# ADR 0002: Arquitetura de Agentes Inteligentes via Adapter Pattern

## Status
Aceito

## Contexto
O ecossistema de modelos de linguagem (LLMs) evolui rapidamente. O sistema não poderia ficar acoplado rigidamente a uma biblioteca específica ou a uma API proprietária, permitindo a substituição do motor de inferência sem impactar as regras pedagógicas de negócio.

## Decisão
Implementou-se a separação estrita de responsabilidades:
1. `LLMService` atua como **Adapter**, centralizando as chamadas HTTP, retentativas e streaming com o Ollama local.
2. `AgenteIA` atua como **Template Method / Facade**, gerenciando injeção de prompts de sistema, recuperação contextual via RAG e formatação defensiva.
3. Agentes especializados (`AgenteTraducao`, `AgentePlanejamento`) implementam apenas as regras de domínio.

## Consequências
- **Positivas:** Isolamento completo para testes automatizados com mocks; facilidade para alternar entre modelos locais (ex.: Qwen3:4b, Llama 3) ou backends de inferência; resiliência a falhas de rede.

