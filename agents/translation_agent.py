"""
IncluSign AI — Agente de Tradução Contextual para Libras (Módulo 1)
===================================================================
Processa termos técnicos e gera explicações contextuais, apoio
semiótico e glossário adaptativo para intérpretes de Libras.

Aplica Arquitetura de Busca Híbrida Inteligente:
  - Recuperação direta e determinística nos dicionários oficiais.
  - Fallback vetorial semântico filtrado por domínio no Qdrant.
  - Síntese com blindagem linguística (Português do Brasil).

Requisitos atendidos: RF-003 a RF-009 (CICURV 2026)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from agents.base_agent import AgenteIA
from config import BASE_DIR, KNOWLEDGE_DIR
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

    def _buscar_verbete_dicionario(self, termo: str, dominio: str) -> dict[str, str] | None:
        """
        Busca determinística de alta precisão no dicionário terminológico do domínio.
        Garante fidelidade conceitual e padronização com a base validada na pesquisa.
        """
        candidatos = [
            KNOWLEDGE_DIR / "traducao" / dominio / f"dicionario_{dominio}_libras.txt",
            KNOWLEDGE_DIR / f"dicionario_{dominio}_libras.txt",
            BASE_DIR / "base-conhecimento" / "traducao" / dominio / f"dicionario_{dominio}_libras.txt",
            BASE_DIR / "base-conhecimento" / f"dicionario_{dominio}_libras.txt",
        ]

        dic_path = next((p for p in candidatos if p.exists()), None)
        if not dic_path:
            return None

        try:
            content = dic_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Falha ao ler dicionário '%s': %s", dic_path, exc)
            return None

        termo_limpo = re.sub(r"\s*\(.*?\)", "", termo).strip()
        padrao = rf"(TERMO TÉCNICO:[^\n]*?{re.escape(termo_limpo)}[^\n]*\n)(.*?)(?=\n\s*TERMO TÉCNICO:|\Z)"
        match = re.search(padrao, content, re.IGNORECASE | re.DOTALL)
        if match:
            return {
                "bloco": match.group(0).strip(),
                "fonte": dic_path.name,
            }

        return None

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

        # 1. Recuperação Híbrida: Busca direta no dicionário oficial do domínio
        verbete_oficial = self._buscar_verbete_dicionario(termo, dominio)

        if verbete_oficial:
            contexto_rag = (
                "\n\n--- CONTEXTO DOS DOCUMENTOS PEDAGÓGICOS ---\n"
                f"[Fonte: {verbete_oficial['fonte']}]\n"
                f"{verbete_oficial['bloco']}\n"
                "--- FIM DO CONTEXTO ---\n"
                "Use as informações acima como base factual para sua resposta, "
                "priorizando fidelidade conceitual e precisão terminológica.\n"
            )
        else:
            # 2. Fallback Semântico: Consulta vetorial filtrada no Qdrant
            contexto_rag = ""
            if self._rag and self._rag.available:
                rag_query = f"{termo} {dominio_completo}"
                results = self._rag.query(
                    rag_query,
                    top_k=3,
                    modulo="traducao",
                    dominio=dominio,
                )
                if results:
                    context_parts = ["\n\n--- CONTEXTO DOS DOCUMENTOS PEDAGÓGICOS ---"]
                    for item in results:
                        source = item.get("source", "documento")
                        text = item.get("text", "")
                        context_parts.append(f"\n[Fonte: {source}]\n{text}")
                    context_parts.append(
                        "\n--- FIM DO CONTEXTO ---\n"
                        "Use as informações acima como base factual para sua resposta, "
                        "priorizando fidelidade conceitual e precisão terminológica.\n"
                    )
                    contexto_rag = "\n".join(context_parts)
                else:
                    contexto_rag = "\n[AVISO: TERMO NÃO ENCONTRADO NOS DICIONÁRIOS OFICIAIS]\n"
            else:
                contexto_rag = "\n[AVISO: TERMO NÃO ENCONTRADO NOS DICIONÁRIOS OFICIAIS]\n"

        # 3. Construção da instrução de inferência
        user_prompt = (
            f"TERMO TÉCNICO: {termo}\n"
            f"DOMÍNIO ACADÊMICO: {dominio_completo}\n"
            f"CONTEXTO DE USO: {contexto or 'Geral'}\n\n"
            "Gere a mediação semiótica, definição conceitual e glosa em Libras."
        )

        # 4. Inferência com streaming ou retorno direto
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
