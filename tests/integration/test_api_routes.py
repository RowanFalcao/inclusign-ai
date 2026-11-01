# -*- coding: utf-8 -*-
"""Testes de integração para as rotas da API REST do IncluSign AI."""


def test_healthz_endpoint(client):
    """Valida o endpoint de liveness probe (/healthz)."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "inclusign-ai"


def test_ready_endpoint(client):
    """Valida o endpoint de readiness probe (/ready)."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ready"] is True
    assert data["llm_available"] is True


def test_api_status_endpoint(client):
    """Valida o endpoint consolidado de status (/api/status)."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.get_json()
    assert "llm" in data
    assert "rag" in data
    assert "sistema" in data
    assert data["sistema"]["versao"] == "1.0.0"


def test_api_translate_endpoint(client):
    """Valida a rota POST /api/translate com payload válido."""
    payload = {
        "dominio": "Computação e Tecnologia",
        "termo": "Deadlock",
        "contexto": "Aula de Sistemas Operacionais",
        "stream": False,
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "content" in data


def test_api_plan_endpoint(client):
    """Valida a rota POST /api/plan com payload pedagógico DUA."""
    payload = {
        "tema": "Algoritmos de Ordenação",
        "objetivos": "Ensinar Bubble Sort visualmente",
        "perfil": "TDAH - Apresentação Desatenta",
        "perfil_detalhe": "Necessidade de pausas estruturadas e recursos visuais",
        "duracao": "45 minutos",
        "stream": False,
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "content" in data


def test_api_telemetry_endpoint(client):
    """Valida a rota de telemetria (/api/telemetry)."""
    response = client.get("/api/telemetry")
    assert response.status_code == 200
    data = response.get_json()
    assert "historico" in data
    assert "estatisticas" in data

