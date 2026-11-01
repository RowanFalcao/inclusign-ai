# -*- coding: utf-8 -*-
"""
Validação Automatizada dos Casos de Teste Pedagógicos (CICURV 2026)
===================================================================
Converte a bateria de validação empírica da pesquisa em testes parametrizados,
assegurando determinismo e regressão zero na esteira de CI/CD.
"""

import pytest

CASOS_TRADUCAO = [
    # Computação
    ("Computação e Tecnologia", "Nuvem Computacional", "Armazenamento remoto em servidores"),
    ("Computação e Tecnologia", "Root (Superusuário)", "Nível de privilégio total no SO"),
    ("Computação e Tecnologia", "Deadlock", "Impasse de concorrência em sistemas operacionais"),
    # Agronomia
    ("Agronomia e Ciências Agrárias", "Lixiviação", "Lavagem de nutrientes do solo por água da chuva"),
    ("Agronomia e Ciências Agrárias", "Alelopatia", "Guerra química biológica entre espécies vegetais"),
    ("Agronomia e Ciências Agrárias", "Rizóbio", "Bactéria simbiótica fixadora de nitrogênio"),
    # Medicina
    ("Medicina e Ciências da Saúde", "Rabdomiólise", "Destruição do tecido muscular e sobrecarga renal"),
    ("Medicina e Ciências da Saúde", "Cetoacidose Diabética", "Queima emergencial de gordura gerando acidose"),
]


@pytest.mark.parametrize("dominio,termo,contexto", CASOS_TRADUCAO)
def test_pedagogical_translation_cases(client, dominio, termo, contexto):
    """Executa a bateria de casos de teste pedagógicos de tradução para Libras."""
    response = client.post(
        "/api/translate",
        json={"dominio": dominio, "termo": termo, "contexto": contexto, "stream": False},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["content"]) > 0


CASOS_PLANEJAMENTO = [
    ("Biologia Celular", "Mitose e Meiose", "TEA - Nível 1", "Sensibilidade a ruído"),
    ("Física Quântica", "Dualidade Onda-Partícula", "TDAH - Desatento", "Necessidade de pausas curtas"),
]


@pytest.mark.parametrize("tema,objetivos,perfil,detalhes", CASOS_PLANEJAMENTO)
def test_pedagogical_planning_cases(client, tema, objetivos, perfil, detalhes):
    """Executa a bateria de casos de teste pedagógicos de planejamento DUA."""
    response = client.post(
        "/api/plan",
        json={
            "tema": tema,
            "objetivos": objetivos,
            "perfil": perfil,
            "perfil_detalhe": detalhes,
            "duracao": "50 minutos",
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["content"]) > 0

