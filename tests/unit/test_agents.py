# -*- coding: utf-8 -*-
"""Testes unitários para os agentes especializados de IA."""

from agents.translation_agent import AgenteTraducao
from agents.planning_agent import AgentePlanejamento


def test_translation_agent_processar(mock_llm_service, mock_rag_service):
    """Valida o fluxo do agente de tradução contextual."""
    agent = AgenteTraducao(mock_llm_service, mock_rag_service)
    
    dados = {
        "dominio": "Computação e Tecnologia",
        "termo": "Nuvem Computacional",
        "contexto": "Explicação para estudante surdo sobre armazenamento virtual.",
    }
    resultado = agent.processar(dados)

    assert resultado["success"] is True
    assert "content" in resultado
    mock_llm_service.generate.assert_called_once()


def test_planning_agent_processar(mock_llm_service, mock_rag_service):
    """Valida o fluxo do agente de planejamento pedagógico adaptado."""
    agent = AgentePlanejamento(mock_llm_service, mock_rag_service)

    dados = {
        "tema": "Ecossistemas e Sustentabilidade",
        "objetivos": "Compreender cadeias alimentares",
        "perfil": "TEA - Nível 1",
        "perfil_detalhe": "Sensibilidade a ruídos e necessidade de rotina visual previsível",
        "duracao": "50 minutos",
    }
    resultado = agent.processar(dados)

    assert resultado["success"] is True
    assert "content" in resultado
    mock_llm_service.generate.assert_called_once()

