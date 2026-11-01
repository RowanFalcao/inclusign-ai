# ADR 0003: Execução 100% Offline para Privacidade de Dados Institucionais e Baixo Custo

## Status
Aceito

## Contexto
O projeto foi desenvolvido sob o Programa de Iniciação Científica (PIVIC/UniRV) visando a democratização do acesso a tecnologias inclusivas. A dependência de APIs comerciais proprietárias (como OpenAI ou Anthropic) criaria três barreiras:
1. Custo recorrente por tokens para instituições públicas de ensino.
2. Risco de vazamento de dados pedagógicos e relatórios confidenciais de alunos neurodivergentes para a nuvem.
3. Impossibilidade de uso em escolas com conectividade instável.

## Decisão
A arquitetura foi fixada para operação **100% offline**, utilizando o modelo quantizado `Qwen3:4b` executado localmente via Ollama, associado a um pipeline RAG com Qdrant local.

## Consequências
- **Positivas:** Conformidade total com a LGPD e privacidade institucional; custo zero de inferência; estabilidade em hardware de consumo (RTX 3050 6GB ou CPUs modernas).

