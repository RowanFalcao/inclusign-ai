"""
IncluSign AI — Test Fixtures (Pytest)
======================================
Fixtures para isolamento e determinismo completo dos testes unitários e de integração.
Permite execução imediata em qualquer ambiente sem necessidade de Ollama ou GPU ativos.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from flask.testing import FlaskClient

from app import create_app
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.telemetry_service import TelemetryService


@pytest.fixture
def mock_llm_service() -> MagicMock:
    """Mock determinístico do LLMService."""
    mock = MagicMock(spec=LLMService)
    mock.is_available.return_value = True
    mock.get_status.return_value = {
        "disponivel": True,
        "mensagem": "LLM Local (Mock) pronto para inferência.",
        "modelo": "qwen3:4b-mock",
    }
    mock.generate.return_value = {
        "success": True,
        "content": "Definição conceitual e glosa em Libras simulada para testes.",
        "tokens_used": 42,
        "response_time_ms": 150,
    }
    return mock


@pytest.fixture
def mock_rag_service() -> MagicMock:
    """Mock determinístico do RAGService."""
    mock = MagicMock(spec=RAGService)
    mock.available = True
    mock.doc_count = 3
    mock.chunk_count = 12
    mock.get_status.return_value = {
        "disponivel": True,
        "mensagem": "RAG Mock ativo.",
        "documentos": 3,
        "trechos_indexados": 12,
    }
    mock.query.return_value = [
        {
            "id": 1,
            "text": "Glossário técnico: Definição simulada de suporte pedagógico.",
            "source": "sample_glossary.txt",
            "score": 0.95,
        }
    ]
    return mock


@pytest.fixture
def mock_telemetry_service(tmp_path) -> TelemetryService:
    """Instância de TelemetryService isolada em diretório temporário."""
    telemetry = TelemetryService()
    # Redireciona o log para o tmp_path para não poluir os logs reais
    telemetry._log_file = tmp_path / "test_telemetry.jsonl"
    return telemetry


@pytest.fixture
def app_instance(mock_llm_service, mock_rag_service, mock_telemetry_service):
    """Instância da aplicação Flask com injeção de dependências mockadas."""
    app = create_app(
        test_config={"TESTING": True},
        llm_service_override=mock_llm_service,
        rag_service_override=mock_rag_service,
        telemetry_service_override=mock_telemetry_service,
    )
    return app


@pytest.fixture
def client(app_instance) -> FlaskClient:
    """Cliente de teste Flask para simular requisições HTTP."""
    return app_instance.test_client()
