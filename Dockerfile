# ==============================================================================
# IncluSign AI — Dockerfile Multi-Stage (Segurança e Otimização Sênior)
# ==============================================================================

# Estágio 1: Builder (Compilação e Resolução de Dependências)
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Estágio 2: Imagem Final de Produção (Enxuta e Não-Root)
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    INCLUSIGN_HOST="0.0.0.0" \
    INCLUSIGN_PORT=5000

# Criar usuário sem privilégios de root para segurança corporativa
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

# Copiar dependências Python compiladas pelo builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código-fonte da aplicação
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 5000

# Healthcheck nativo utilizando o endpoint de observabilidade
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" || exit 1

CMD ["python", "app.py"]

