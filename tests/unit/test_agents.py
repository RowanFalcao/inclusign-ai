"""Testes unitários para os agentes especializados de IA."""

import config
from agents.planning_agent import AgentePlanejamento
from agents.translation_agent import AgenteTraducao


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


def test_translation_agent_lookup_dicionario(
    mock_llm_service, mock_rag_service, tmp_path, monkeypatch
):
    """Valida a busca determinística direta nos dicionários da base."""
    agent = AgenteTraducao(mock_llm_service, mock_rag_service)

    # Cria dicionário simulado no tmp_path para determinismo e isolamento em CI/CD
    dic_dir = tmp_path / "traducao" / "computacao"
    dic_dir.mkdir(parents=True)
    dic_file = dic_dir / "dicionario_computacao_libras.txt"
    dic_file.write_text(
        "TERMO TÉCNICO: 01 - Nuvem Computacional (Cloud Computing)\n"
        "ÁREA: Computação e Tecnologia da Informação\n"
        "CONCEITO: Servidores online onde você guarda arquivos.\n"
        "DESCRIÇÃO GLOSADA (LIBRAS): ESPAÇO-SUPERIOR GUARDAR.\n"
        "DICA DA INTÉRPRETE (APOIO SEMIÓTICO): Evite usar sinal de clima.\n\n"
        "TERMO TÉCNICO: 02 - Root\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(config, "KNOWLEDGE_DIR", tmp_path)

    verbete = agent._buscar_verbete_dicionario("Nuvem Computacional", "computacao")
    assert verbete is not None
    assert "Nuvem Computacional" in verbete["bloco"]
    assert "DESCRIÇÃO GLOSADA (LIBRAS)" in verbete["bloco"]

    inexistente = agent._buscar_verbete_dicionario("TermoTotalmenteInexistente123", "computacao")
    assert inexistente is None


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
