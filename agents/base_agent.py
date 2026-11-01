# -*- coding: utf-8 -*-
"""
IncluSign AI — Agente Base (Classe Abstrata)
=============================================
Encapsula a lógica comum a todos os agentes de IA do sistema.

Padrão de Projeto: Template Method + Facade
Atributos de Qualidade: Resiliência, Type Safety e Desacoplamento.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generator, Dict, Optional

from services.llm_service import LLMService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Prompts padrão (fallback público seguro para garantir reprodutibilidade aberta)
DEFAULT_PROMPTS: dict[str, str] = {
    "translation_system.txt": (
        "Você é o Agente Especialista em Tradução e Mediação Semiótica para Libras do IncluSign AI. "
        "Sua função é fornecer traduções precisas, descrições glosadas padronizadas e apoios visuais "
        "para termos e jargões científicos nos domínios acadêmicos (Computação, Medicina e Agronomia)."
    ),
    "planning_system.txt": (
        "Você é o Agente Especialista em Planejamento Pedagógico Inclusivo do IncluSign AI. "
        "Sua função é gerar planos de aula adaptados alinhados às diretrizes do Desenho Universal para a "
        "Aprendizagem (DUA) e aos protocolos de suporte para estudantes neurodivergentes (TEA e TDAH)."
    ),
}


class AgenteIA(ABC):
    """
    Classe abstrata base para os agentes de IA do IncluSign AI.

    Encapsula:
    - Carregamento resiliente de system prompts com fallback seguro
    - Conexão desacoplada com o LLM local via LLMService
    - Integração transparente com o banco vetorial RAG
    """

    def __init__(
        self,
        llm_service: LLMService,
        rag_service: Optional[RAGService],
        prompt_file: str,
    ) -> None:
        """
        Inicializa o agente com injeção de dependências.

        Parâmetros:
            llm_service: Instância do serviço de LLM.
            rag_service: Instância opcional do serviço RAG.
            prompt_file: Nome do arquivo de system prompt (em prompts/).
        """
        self._llm = llm_service
        self._rag = rag_service
        self._prompt_file = prompt_file
        self._system_prompt = self._load_system_prompt(prompt_file)

    def _load_system_prompt(self, filename: str = "") -> str:
        """
        Carrega o system prompt com estratégia de fallback em 3 níveis:
        1. Arquivo proprietário local (prompts/<filename>) se existir.
        2. Arquivo de exemplo público (prompts/<filename>.example) se existir.
        3. Prompt base embutido para garantir reprodutibilidade sem quebra.
        """
        target_file = filename or self._prompt_file
        if not target_file:
            return getattr(self, "_system_prompt", "")

        from config import PROMPTS_DIR

        # Nível 1: Arquivo direto
        prompt_path = PROMPTS_DIR / target_file
        if prompt_path.exists():
            try:
                content = prompt_path.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except Exception as exc:
                logger.warning("Falha ao ler prompt '%s': %s. Tentando fallback.", prompt_path, exc)

        # Nível 2: Arquivo .example
        example_path = PROMPTS_DIR / f"{target_file}.example"
        if example_path.exists():
            try:
                content = example_path.read_text(encoding="utf-8").strip()
                if content:
                    logger.info("Carregando prompt de exemplo: %s", example_path)
                    return content
            except Exception as exc:
                logger.warning("Falha ao ler prompt exemplo: %s", exc)

        # Nível 3: Fallback embutido
        if target_file in DEFAULT_PROMPTS:
            logger.info("Utilizando prompt padrão embutido para '%s'", target_file)
            return DEFAULT_PROMPTS[target_file]

        logger.warning("Nenhum prompt disponível para '%s'. Usando instrução genérica.", target_file)
        return "Você é um assistente educacional inclusivo da plataforma IncluSign AI."

    def conectar_api_llama_local(self) -> bool:
        """
        Verifica a disponibilidade do LLM local.

        Retorna:
            True se o modelo está acessível, False caso contrário.
        """
        return self._llm.is_available()

    def _enriquecer_com_rag(self, query: str) -> str:
        """
        Consulta o RAG para obter contexto adicional dos documentos.
        Se o RAG estiver indisponível ou vazio, retorna string vazia sem lançar exceção.
        """
        if not self._rag or not self._rag.available:
            return ""

        results = self._rag.query(query)
        if not results:
            return ""

        context_parts = [
            "\n\n--- CONTEXTO DOS DOCUMENTOS PEDAGÓGICOS ---"
        ]
        for item in results:
            source = item.get("source", "documento")
            text = item.get("text", "")
            context_parts.append(f"\n[Fonte: {source}]\n{text}")

        context_parts.append(
            "\n--- FIM DO CONTEXTO ---\n"
            "Use as informações acima como base factual para sua resposta, "
            "priorizando fidelidade conceitual e precisão terminológica.\n"
        )

        return "\n".join(context_parts)

    def _gerar_resposta(
        self,
        user_prompt: str,
        extra_context: str = "",
        temperature: Optional[float] = None,
        stream: bool = False,
        think: bool = False,
    ) -> Any:
        """
        Gera resposta do LLM com system prompt e contexto RAG integrados.
        """
        full_system = self._system_prompt
        full_user_prompt = f"{extra_context}\n\n{user_prompt}" if extra_context else user_prompt

        return self._llm.generate(
            prompt=full_user_prompt,
            system_prompt=full_system,
            temperature=temperature,
            stream=stream,
            think=think,
        )

    @abstractmethod
    def processar(self, dados_entrada: dict[str, Any], stream: bool = False) -> Any:
        """
        Processa uma requisição do usuário.
        Cada agente especializado implementa sua lógica específica.
        """
        pass
