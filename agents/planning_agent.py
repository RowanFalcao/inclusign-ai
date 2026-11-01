"""
IncluSign AI — Agente de Planejamento Pedagógico (Módulo 3)
============================================================
Gera planos de aula estruturados e adaptados ao perfil cognitivo
de alunos surdos e neurodivergentes.

Requisitos atendidos: RF-010 a RF-013
"""

import logging
import time

from agents.base_agent import AgenteIA
from services.llm_service import LLMService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Perfis de necessidade suportados
PERFIS_ALUNO = {
    "tdah": "TDAH (Transtorno de Déficit de Atenção e Hiperatividade)",
    "dislexia": "Dislexia",
    "tea": "TEA (Transtorno do Espectro Autista)",
    "surdez": "Surdez / Deficiência Auditiva",
    "baixa_visao": "Baixa Visão",
    "superdotacao": "Altas Habilidades / Superdotação",
    "outro": "Outro (especificado pelo professor)",
}

# Instrução automática exibida ao iniciar o módulo (RF-010)
INSTRUCAO_PARAMETROS = (
    "📋 INSTRUÇÕES: Para gerar um plano de aula assertivo e personalizado, "
    "informe os seguintes parâmetros:\n\n"
    "1. **Tema da Aula** — O assunto ou conteúdo a ser ensinado\n"
    "2. **Objetivos de Aprendizagem** — O que o aluno deve ser capaz de fazer "
    "após a aula\n"
    "3. **Perfil do Aluno** — O tipo de necessidade educacional especial "
    "(TDAH, Dislexia, TEA, Surdez, etc.)\n\n"
    "Quanto mais detalhes você fornecer, mais preciso será o plano gerado."
)


class AgentePlanejamento(AgenteIA):
    """
    Agente especializado em geração de planos de aula inclusivos.

    Herda de AgenteIA e implementa o Módulo 3 do sistema.
    """

    def __init__(self, llm_service: LLMService, rag_service: RAGService):
        super().__init__(
            llm_service=llm_service,
            rag_service=rag_service,
            prompt_file="planning_system.txt",
        )

    def processar(self, dados_entrada: dict, stream: bool = False, use_reasoning: bool = False):
        """
        Processa uma solicitação de plano de aula.

        Parâmetros (dados_entrada):
            tema: str — Tema da aula
            objetivos: str — Objetivos de aprendizagem
            perfil: str — Perfil de necessidade do aluno
            perfil_detalhe: str — Detalhes adicionais (opcional)
            duracao: str — Duração estimada (opcional)

        Retorna:
            dict com: success, content, tokens_used, response_time_ms
        """
        tema = dados_entrada.get("tema", "").strip()
        objetivos = dados_entrada.get("objetivos", "").strip()
        perfil = dados_entrada.get("perfil", "").lower().strip()
        perfil_detalhe = dados_entrada.get("perfil_detalhe", "").strip()
        duracao = dados_entrada.get("duracao", "50 minutos").strip()

        # Validação de entrada
        if not tema:
            return {
                "success": False,
                "content": "Por favor, informe o tema da aula.",
                "instrucao": INSTRUCAO_PARAMETROS,
            }

        if not objetivos:
            return {
                "success": False,
                "content": "Por favor, descreva os objetivos de aprendizagem.",
                "instrucao": INSTRUCAO_PARAMETROS,
            }

        if not perfil:
            return {
                "success": False,
                "content": "Por favor, selecione o perfil de necessidade do aluno.",
                "instrucao": INSTRUCAO_PARAMETROS,
            }

        # Resolver nome completo do perfil
        perfil_nome = PERFIS_ALUNO.get(perfil, perfil_detalhe or perfil)
        if perfil == "outro" and perfil_detalhe:
            perfil_nome = perfil_detalhe

        # Enriquecimento com contexto do RAG: filtragem de documentos e busca semântica
        rag_query = f"adaptação pedagógica inclusão {perfil_nome} dicas estratégias"
        rag_context = ""

        if self._rag and self._rag.available:
            context_items = self._rag.query(rag_query, top_k=10)
            textos_filtrados = []

            for item in context_items:
                # Desconsidera dicionários terminológicos para restringir o contexto a manuais pedagógicos
                if "dicionario" not in item.get("source", "").lower():
                    textos_filtrados.append(f"\n[Fonte: {item['source']}]\n{item['text']}")

            if textos_filtrados:
                rag_context = (
                    "\n\n--- CONTEXTO DOS DOCUMENTOS PEDAGÓGICOS ---"
                    + "".join(textos_filtrados)
                    + "\n\n--- FIM DO CONTEXTO ---\n"
                    "Use as informações acima como base para sua resposta, "
                    "mas não mencione que recebeu esse contexto.\n"
                )

        # Construir prompt
        user_prompt = self._build_prompt(
            tema, objetivos, perfil_nome, duracao, perfil_detalhe, use_reasoning
        )

        # Controle de raciocínio lógico (soft switch) e temperatura de amostragem do modelo Qwen
        if use_reasoning:
            user_prompt += " /think"
            temp_oficial = 0.6
        else:
            user_prompt += " /no_think"
            temp_oficial = 0.7

        # Gerar resposta
        start_time = time.time()
        result = self._gerar_resposta(
            user_prompt=user_prompt,
            extra_context=rag_context,
            temperature=temp_oficial,
            stream=stream,
            think=use_reasoning,
        )

        if stream:
            return result
        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "success": result["success"],
            "content": result["content"],
            "perfil_nome": perfil_nome,
            "tokens_used": result.get("tokens_used", 0),
            "response_time_ms": elapsed_ms,
        }

    def _build_prompt(
        self,
        tema: str,
        objetivos: str,
        perfil: str,
        duracao: str,
        detalhe: str = "",
        use_reasoning: bool = False,
    ) -> str:
        """Constrói o prompt de usuário para geração de plano de aula."""
        parts = [
            f"**Tema da Aula:** {tema}",
            f"**Objetivos de Aprendizagem:** {objetivos}",
            f"**Perfil de Necessidade do Aluno:** {perfil}",
            f"**Duração Estimada:** {duracao}",
        ]

        if detalhe:
            parts.append(f"**Detalhes Adicionais do Perfil:** {detalhe}")

        instrucao = (
            "\nPor favor, elabore um plano de aula completo e estruturado "
            "com todas as seções especificadas (Dados da Aula, Objetivos, "
            "Estratégias Adaptadas, Cronograma, Recursos, Avaliação e Glossário)."
        )

        if use_reasoning:
            instrucao += (
                "\nREGRA OBRIGATÓRIA: Você DEVE usar formatação de tabelas em Markdown "
                "(iniciando as linhas com a barra vertical |) para apresentar as seções de Cronograma, Recursos e Avaliação."
            )

        parts.append(instrucao)

        return "\n".join(parts)

    def get_perfis(self) -> dict:
        """Retorna os perfis de aluno disponíveis."""
        return PERFIS_ALUNO.copy()

    def get_instrucao(self) -> str:
        """Retorna a instrução automática (RF-010)."""
        return INSTRUCAO_PARAMETROS
