# ADR 0001: Adoção do Qdrant como Motor Vetorial Embarcado

## Status
Aceito

## Contexto
A plataforma IncluSign AI necessita de recuperação semântica eficiente (RAG) de diretrizes pedagógicas e terminologias de Libras. O banco vetorial precisava operar de forma totalmente local, sem dependência de serviços pagos em nuvem (RNF-002) e com suporte nativo a múltiplos sistemas operacionais (Windows, Linux, macOS).

## Decisão
Adotou-se o **Qdrant** em modo local/embarcado (`path=VECTOR_DB_DIR`) com embeddings via `all-MiniLM-L6-v2`.

## Consequências
- **Positivas:** Desempenho ultrarrápido em buscas por similaridade de cosseno; persistência limpa em disco sem necessidade de processo daemon adicional; total compatibilidade multiplataforma.
- **Negativas:** Exige sincronização inicial da pasta de índices caso a base de conhecimento seja expandida.

