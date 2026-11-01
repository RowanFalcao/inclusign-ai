"""
IncluSign AI — Configurações Centralizadas e Portáveis
======================================================
Todas as variáveis de ambiente e caminhos do sistema são gerenciados aqui.
Compatível 100% com Linux, macOS e Windows (cross-platform).

Atributos de Qualidade aplicados:
  - Portabilidade: caminhos agnósticos via pathlib.Path
  - Manutenibilidade: ponto único de configuração com tipagem
  - Segurança: parametrização via variáveis de ambiente com defaults seguros
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# ============================================================================
# DIRETÓRIOS DO SISTEMA (100% DINÂMICOS E AGNÓSTICOS)
# ============================================================================

# Diretório raiz da aplicação
BASE_DIR = Path(__file__).resolve().parent

# Pasta para base de conhecimento textual e PDFs pedagógicos (fonte do RAG)
KNOWLEDGE_DIR = BASE_DIR / "base-conhecimento"

# Pasta de dados de demonstração (sample reproduzível para avaliadores)
SAMPLE_KNOWLEDGE_DIR = BASE_DIR / "sample_knowledge"

# Pasta para persistência do banco de dados vetorial (Qdrant embarcado)
VECTOR_DB_DIR = BASE_DIR / "banco-vetorial"

# Pasta para registros de telemetria e auditoria
LOGS_DIR = BASE_DIR / "logs"

# Pasta dos system prompts
PROMPTS_DIR = Path(os.environ.get("INCLUSIGN_PROMPTS_DIR", str(BASE_DIR / "prompts")))

# ============================================================================
# MODELO LLM LOCAL (OLLAMA / CPU OU GPU COMPATÍVEL)
# ============================================================================

# URL do servidor Ollama local (padrão oficial)
OLLAMA_URL = os.environ.get("INCLUSIGN_OLLAMA_URL", "http://127.0.0.1:11434")

# Nome/tag do modelo validado na metodologia científica (CICURV 2026)
OLLAMA_MODEL = os.environ.get("INCLUSIGN_OLLAMA_MODEL", "qwen3:4b")

# Timeout para requisições ao LLM (em segundos)
LLM_TIMEOUT = int(os.environ.get("INCLUSIGN_LLM_TIMEOUT", "120"))

# Temperatura padrão para inferência determinística (baixo desvio)
LLM_TEMPERATURE = float(os.environ.get("INCLUSIGN_LLM_TEMPERATURE", "0.4"))

# Número máximo de tokens na resposta
LLM_MAX_TOKENS = int(os.environ.get("INCLUSIGN_LLM_MAX_TOKENS", "8192"))

# Limite total da janela de contexto (System + RAG + User + Output)
LLM_MAX_CONTEXT = int(os.environ.get("INCLUSIGN_LLM_MAX_CONTEXT", "8192"))

# Janela de penalidade de repetição (repeat_last_n)
LLM_REPEAT_LAST_N = int(os.environ.get("INCLUSIGN_LLM_REPEAT_LAST_N", "64"))

# ============================================================================
# RAG (Retrieval-Augmented Generation & Qdrant)
# ============================================================================

# Modelo de embeddings para busca semântica
EMBEDDING_MODEL = os.environ.get("INCLUSIGN_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Tamanho dos chunks de texto para indexação (em caracteres)
RAG_CHUNK_SIZE = int(os.environ.get("INCLUSIGN_RAG_CHUNK_SIZE", "800"))

# Sobreposição entre chunks adjacentes
RAG_CHUNK_OVERLAP = int(os.environ.get("INCLUSIGN_RAG_CHUNK_OVERLAP", "150"))

# Número de passagens retornadas por consulta semântica
RAG_TOP_K = int(os.environ.get("INCLUSIGN_RAG_TOP_K", "3"))

# Nome da coleção no Qdrant
VECTOR_COLLECTION = os.environ.get("INCLUSIGN_VECTOR_COLLECTION", "inclusign_knowledge")

# ============================================================================
# SERVIDOR WEB E API
# ============================================================================

# Porta do servidor web
SERVER_PORT = int(os.environ.get("INCLUSIGN_PORT", "5000"))

# Host de bind (127.0.0.1 por padrão de segurança local; 0.0.0.0 em Docker)
SERVER_HOST = os.environ.get("INCLUSIGN_HOST", "127.0.0.1")

# Modo debug (desabilitado em produção)
DEBUG_MODE = os.environ.get("INCLUSIGN_DEBUG", "False").lower() in ("true", "1", "t")

# ============================================================================
# TELEMETRIA E LOGS
# ============================================================================

LOG_FILENAME_PATTERN = "inclusign_telemetry_{date}.jsonl"

# ============================================================================
# INICIALIZAÇÃO DE DIRETÓRIOS ESSENCIAIS
# ============================================================================


def ensure_directories() -> None:
    """Cria os diretórios necessários se não existirem, com tratamento resiliente."""
    for directory in [KNOWLEDGE_DIR, VECTOR_DB_DIR, LOGS_DIR, PROMPTS_DIR, SAMPLE_KNOWLEDGE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_system_diagnostics() -> dict[str, object]:
    """Retorna metadados de diagnóstico do ambiente de execução de forma segura."""
    return {
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "knowledge_dir_exists": KNOWLEDGE_DIR.exists(),
        "sample_knowledge_dir_exists": SAMPLE_KNOWLEDGE_DIR.exists(),
        "vector_db_dir_exists": VECTOR_DB_DIR.exists(),
    }
