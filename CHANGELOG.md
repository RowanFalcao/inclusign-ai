# Changelog

Todas as alterações notáveis neste projeto serão documentadas neste arquivo.

O formato baseia-se em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-31

### Adicionado
- **Módulo 1:** Agente de Tradução Contextual e Mediação Semiótica para Libras em domínios acadêmicos (Computação, Medicina e Agronomia).
- **Módulo 2:** Agente de Planejamento Pedagógico Inclusivo alinhado às diretrizes do Desenho Universal para a Aprendizagem (DUA) para cenários de TEA e TDAH.
- Arquitetura RAG embarcada utilizando banco vetorial **Qdrant** e modelo de embeddings `all-MiniLM-L6-v2`.
- Suporte a streaming de tokens e telemetria em tempo real via Server-Sent Events (SSE).
- Suíte completa de testes automatizados com `pytest` cobrindo casos unitários e de integração.
- Esteira de CI/CD via GitHub Actions com matriz de testes para Ubuntu e Windows (Python 3.11 e 3.12).
- Conteinerização completa com `Dockerfile` multi-stage (não-root) e `docker-compose.yml`.
- Endpoints de observabilidade corporativa (`/healthz` e `/ready`).
- Documentação técnica padrão-ouro com Architectural Decision Records (ADRs).

