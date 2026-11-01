"""
IncluSign AI — Agente de Tradução Contextual para Libras (Módulo 1)
===================================================================
Processa termos técnicos e gera explicações contextuais, apoio
semiótico e glossário adaptativo para intérpretes de Libras.

Requisitos atendidos: RF-003 a RF-009 (CICURV 2026)
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base_agent import AgenteIA
from services.llm_service import LLMService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)

DOMINIOS_VALIDOS = {
    "computacao": "Computação e Tecnologia da Informação",
    "medicina": "Medicina e Ciências da Saúde",
    "agronomia": "Agronomia e Ciências Agrárias",
}

AVISO_LIMITACAO = (
    "⚠️ AVISO IMPORTANTE: As sugestões apresentadas são apoios pedagógicos "
    "gerados por inteligência artificial e NÃO constituem sinais oficiais da "
    "Língua Brasileira de Sinais (Libras). A criação e validação de novos sinais "
    "é competência exclusiva da comunidade surda e de linguistas especializados."
)

AVISOS_ESCOPO = {
    "computacao": "🔍 ESCOPO: Otimizado para Programação, Redes, Segurança Cibernética, Algoritmos e Estruturas de Dados.",
    "medicina": "🔍 ESCOPO: Otimizado para Anatomia, Fisiologia, Farmacologia e Diagnóstico Clínico.",
    "agronomia": "🔍 ESCOPO: Otimizado para Fitossanidade, Mecanização Agrícola, Biotecnologia e Ciência do Solo.",
}


def normalizar_dominio(dominio_raw: str) -> str:
    """Normaliza strings variadas de domínio para as chaves canônicas."""
    d = dominio_raw.lower().strip()
    if "comp" in d or "tecnol" in d:
        return "computacao"
    if "agro" in d:
        return "agronomia"
    if "med" in d or "saude" in d or "saúde" in d:
        return "medicina"
    return d


class AgenteTraducao(AgenteIA):
    """Agente especializado em tradução contextual de termos técnicos."""

    def __init__(self, llm_service: LLMService, rag_service: RAGService | None = None):
        super().__init__(
            llm_service=llm_service,
            rag_service=rag_service,
            prompt_file="translation_system.txt",
        )

    def processar(self, dados_entrada: dict[str, Any], stream: bool = False) -> Any:
        dominio_raw = dados_entrada.get("dominio", "")
        dominio = normalizar_dominio(dominio_raw)
        termo = str(dados_entrada.get("termo", "")).strip()
        contexto = str(dados_entrada.get("contexto", "")).strip()

        if not termo:
            return {
                "success": False,
                "content": "Por favor, insira o termo técnico que deseja traduzir.",
                "aviso_escopo": "",
                "aviso_limitacao": AVISO_LIMITACAO,
            }
        if dominio not in DOMINIOS_VALIDOS:
            return {
                "success": False,
                "content": "Domínio inválido. Selecione: Computação, Medicina ou Agronomia.",
                "aviso_escopo": "",
                "aviso_limitacao": AVISO_LIMITACAO,
            }

        dominio_completo = DOMINIOS_VALIDOS[dominio]
        aviso_escopo = AVISOS_ESCOPO.get(dominio, "")

        # 1. Recuperação RAG (caso disponível)
        rag_query = f"{termo} {dominio_completo} {contexto}"
        contexto_rag = self._enriquecer_com_rag(rag_query)

        # 2. Construção da instrução de inferência
        user_prompt = (
            f"TERMO TÉCNICO: {termo}\n"
            f"DOMÍNIO ACADÊMICO: {dominio_completo}\n"
            f"CONTEXTO DE USO: {contexto or 'Geral'}\n\n"
            "Gere a mediação semiótica, definição conceitual e glosa em Libras."
        )

        # 3. Inferência com streaming ou retorno direto
        result = self._gerar_resposta(
            user_prompt=user_prompt,
            extra_context=contexto_rag,
            stream=stream,
        )

        if stream:
            return result

        if isinstance(result, dict) and result.get("success"):
            result["aviso_escopo"] = aviso_escopo
            result["aviso_limitacao"] = AVISO_LIMITACAO

        return result
