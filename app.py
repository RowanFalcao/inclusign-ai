# -*- coding: utf-8 -*-
"""
IncluSign AI — Aplicação Principal (Application Factory)
=========================================================
Servidor Flask desacoplado e production-grade para a plataforma de inclusão educacional.

Padrões de Projeto:
  - Application Factory Pattern (create_app)
  - Dependency Injection (serviços configuráveis e mockáveis)
  - Observer / Telemetry Pattern

Rotas da API:
  GET  /                          → Interface Web (Single Page Application)
  GET  /healthz                   → Liveness Probe (Healthcheck de infraestrutura)
  GET  /ready                     → Readiness Probe (Verificação de serviços)
  GET  /api/status                → Status consolidado do LLM + RAG + Telemetria
  POST /api/translate             → Tradução contextual para Libras (Módulo 1)
  POST /api/plan                  → Planejamento pedagógico adaptado DUA (Módulo 2)
  POST /api/chat                  → Chat interativo de refinamento
  GET  /api/telemetry             → Histórico de interações
  GET  /api/telemetry/export      → Exportação de telemetria em CSV/TXT
  POST /api/rag/reindex           → Re-indexação sob demanda
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from flask import Flask, Response, jsonify, render_template, request

# Garantir resolução correta de módulos
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from config import DEBUG_MODE, SERVER_HOST, SERVER_PORT, ensure_directories
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.telemetry_service import TelemetryService
from agents.translation_agent import AgenteTraducao
from agents.planning_agent import AgentePlanejamento

# Configuração de logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("IncluSign")


def create_app(
    test_config: Optional[dict[str, Any]] = None,
    llm_service_override: Optional[LLMService] = None,
    rag_service_override: Optional[RAGService] = None,
    telemetry_service_override: Optional[TelemetryService] = None,
) -> Flask:
    """
    Application Factory para instanciar a aplicação Flask de forma desacoplada.
    Facilita testes automatizados, conteinerização e execução em produção.
    """
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config["JSON_AS_ASCII"] = False

    if test_config:
        app.config.update(test_config)

    # Inicialização de diretórios
    ensure_directories()

    # Inicialização ou injeção dos serviços
    llm = llm_service_override or LLMService()
    
    if rag_service_override is not None:
        rag = rag_service_override
    else:
        try:
            rag = RAGService()
        except Exception as exc:
            logger.warning("RAG não inicializado: %s", exc)
            rag = None

    telemetry = telemetry_service_override or TelemetryService()

    # Instanciação dos agentes inteligentes
    translation_agent = AgenteTraducao(llm, rag)
    planning_agent = AgentePlanejamento(llm, rag)

    # Armazenamento de estado de chat em memória por sessão
    chat_histories: dict[str, list[dict[str, str]]] = defaultdict(list)

    # ------------------------------------------------------------------------
    # HEALTHCHECKS E OBSERVABILIDADE
    # ------------------------------------------------------------------------

    @app.route("/healthz", methods=["GET"])
    def healthz():
        """Liveness probe para monitoramento de integridade e Docker."""
        return jsonify({"status": "healthy", "service": "inclusign-ai"}), 200

    @app.route("/ready", methods=["GET"])
    def ready():
        """Readiness probe para verificar prontidão do motor de IA."""
        llm_ok = llm.is_available()
        rag_ok = rag.available if rag else False
        status_code = 200 if llm_ok else 503
        return jsonify({
            "ready": llm_ok,
            "llm_available": llm_ok,
            "rag_available": rag_ok,
        }), status_code

    # ------------------------------------------------------------------------
    # ROTAS WEB E SPA
    # ------------------------------------------------------------------------

    @app.route("/", methods=["GET"])
    def index():
        """Interface web principal do sistema."""
        return render_template("index.html")

    # ------------------------------------------------------------------------
    # ROTAS DA API
    # ------------------------------------------------------------------------

    @app.route("/api/status", methods=["GET"])
    def api_status():
        """Retorna o status consolidado de saúde dos componentes."""
        rag_status_data = (
            rag.get_status()
            if rag
            else {
                "disponivel": False,
                "mensagem": "Serviço RAG não inicializado.",
                "documentos": 0,
                "trechos_indexados": 0,
            }
        )

        llm_data = llm.get_status()
        llm_data["tipo"] = "local"

        return jsonify({
            "llm": llm_data,
            "rag": rag_status_data,
            "telemetria": telemetry.get_stats(),
            "sistema": {
                "nome": "IncluSign AI",
                "versao": "1.0.0",
                "modelo": config.OLLAMA_MODEL,
                "servidor": f"{SERVER_HOST}:{SERVER_PORT}",
                "diagnostico": config.get_system_diagnostics(),
            },
        })

    @app.route("/api/translate", methods=["POST"])
    def api_translate():
        """Processa tradução contextual para Libras (Módulo 1)."""
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id", str(uuid.uuid4())[:8])
        stream_requested = data.get("stream", False)

        result = translation_agent.processar({
            "dominio": data.get("dominio", ""),
            "termo": data.get("termo", ""),
            "contexto": data.get("contexto", ""),
        }, stream=stream_requested)

        if stream_requested:
            if isinstance(result, dict):
                def error_generator():
                    yield f"data: {json.dumps({'content': result.get('content', 'Erro de conexão com a IA.'), 'success': False})}\n\n"
                    yield f"data: {json.dumps({'done': True})}\n\n"
                return Response(error_generator(), mimetype="text/event-stream")

            def sse_generator():
                full_content = ""
                total_content_length = 0
                start_time = time.time()
                first_token = True
                ttft = 0

                for chunk_data in result:
                    if first_token:
                        ttft = int((time.time() - start_time) * 1000)
                        first_token = False

                    if isinstance(chunk_data, dict):
                        chunk_str = chunk_data.get("content", "")
                        is_thinking = chunk_data.get("is_thinking", False)
                    else:
                        chunk_str = chunk_data
                        is_thinking = False

                    if not is_thinking:
                        full_content += chunk_str

                    total_content_length += len(chunk_str)
                    yield f"data: {json.dumps({'content': chunk_str, 'success': True, 'is_thinking': is_thinking})}\n\n"

                context_key = f"{session_id}:traducao"
                user_msg = f"Traduza o termo '{data.get('termo')}' no domínio '{data.get('dominio')}'. Contexto de uso: {data.get('contexto')}"

                chat_histories[context_key] = [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": full_content}
                ]

                elapsed_ms = int((time.time() - start_time) * 1000)
                estimated_tokens = total_content_length // 4

                telemetry.log_interaction(
                    session_id=session_id,
                    agent_type="traducao",
                    input_data={
                        "dominio": data.get("dominio", ""),
                        "termo": data.get("termo", ""),
                        "contexto": data.get("contexto", ""),
                    },
                    output_data={"success": True, "content": full_content},
                    metadata={"tokens_used": estimated_tokens, "response_time_ms": elapsed_ms, "ttft_ms": ttft},
                )
                yield f"data: {json.dumps({'done': True, 'response_time_ms': elapsed_ms, 'tokens_used': estimated_tokens})}\n\n"

            return Response(sse_generator(), mimetype="text/event-stream")

        if result.get("success"):
            context_key = f"{session_id}:traducao"
            user_msg = f"Traduza o termo '{data.get('termo')}' no domínio '{data.get('dominio')}'. Contexto de uso: {data.get('contexto')}"
            chat_histories[context_key] = [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": result["content"]}
            ]

        telemetry.log_interaction(
            session_id=session_id,
            agent_type="traducao",
            input_data={
                "dominio": data.get("dominio", ""),
                "termo": data.get("termo", ""),
                "contexto": data.get("contexto", ""),
            },
            output_data={
                "success": result.get("success", False),
                "content": result.get("content", ""),
            },
            metadata={
                "tokens_used": result.get("tokens_used", 0),
                "response_time_ms": result.get("response_time_ms", 0),
            },
        )
        return jsonify(result)

    @app.route("/api/plan", methods=["POST"])
    def api_plan():
        """Processa planejamento pedagógico adaptado DUA (Módulo 2)."""
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id", str(uuid.uuid4())[:8])
        stream_requested = data.get("stream", False)
        use_reasoning = data.get("use_reasoning", False)

        result = planning_agent.processar({
            "tema": data.get("tema", ""),
            "objetivos": data.get("objetivos", ""),
            "perfil": data.get("perfil", ""),
            "perfil_detalhe": data.get("perfil_detalhe", ""),
            "duracao": data.get("duracao", "50 minutos"),
        }, stream=stream_requested, use_reasoning=use_reasoning)

        if stream_requested:
            if isinstance(result, dict):
                def error_generator():
                    yield f"data: {json.dumps({'content': result.get('content', 'Erro de conexão com a IA.'), 'success': False})}\n\n"
                    yield f"data: {json.dumps({'done': True})}\n\n"
                return Response(error_generator(), mimetype="text/event-stream")

            def sse_generator():
                full_content = ""
                total_content_length = 0
                start_time = time.time()
                first_token = True
                ttft = 0

                for chunk_data in result:
                    if first_token:
                        ttft = int((time.time() - start_time) * 1000)
                        first_token = False

                    if isinstance(chunk_data, dict):
                        chunk_str = chunk_data.get("content", "")
                        is_thinking = chunk_data.get("is_thinking", False)
                    else:
                        chunk_str = chunk_data
                        is_thinking = False

                    if not is_thinking:
                        full_content += chunk_str

                    total_content_length += len(chunk_str)
                    yield f"data: {json.dumps({'content': chunk_str, 'success': True, 'is_thinking': is_thinking})}\n\n"

                context_key = f"{session_id}:planejamento"
                user_msg = (
                    f"Crie um plano de aula sobre '{data.get('tema')}'. "
                    f"Objetivos: {data.get('objetivos')}. "
                    f"Perfil de necessidade: {data.get('perfil')}. "
                    f"Detalhes adicionais do perfil: {data.get('perfil_detalhe')}. "
                    f"Duração: {data.get('duracao')}."
                )

                chat_histories[context_key] = [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": full_content}
                ]

                elapsed_ms = int((time.time() - start_time) * 1000)
                estimated_tokens = total_content_length // 4

                telemetry.log_interaction(
                    session_id=session_id,
                    agent_type="planejamento",
                    input_data={
                        "tema": data.get("tema", ""),
                        "objetivos": data.get("objetivos", ""),
                        "perfil": data.get("perfil", ""),
                    },
                    output_data={"success": True, "content": full_content},
                    metadata={
                        "tokens_used": estimated_tokens,
                        "response_time_ms": elapsed_ms,
                        "ttft_ms": ttft,
                    },
                )
                yield f"data: {json.dumps({'done': True, 'response_time_ms': elapsed_ms, 'tokens_used': estimated_tokens})}\n\n"

            return Response(sse_generator(), mimetype="text/event-stream")

        if result.get("success"):
            context_key = f"{session_id}:planejamento"
            user_msg = (
                f"Crie um plano de aula sobre '{data.get('tema')}'. "
                f"Objetivos: {data.get('objetivos')}. "
                f"Perfil de necessidade: {data.get('perfil')}. "
                f"Detalhes adicionais do perfil: {data.get('perfil_detalhe')}. "
                f"Duração: {data.get('duracao')}."
            )
            chat_histories[context_key] = [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": result["content"]}
            ]

        telemetry.log_interaction(
            session_id=session_id,
            agent_type="planejamento",
            input_data={
                "tema": data.get("tema", ""),
                "objetivos": data.get("objetivos", ""),
                "perfil": data.get("perfil", ""),
            },
            output_data={
                "success": result.get("success", False),
                "content": result.get("content", ""),
            },
            metadata={
                "tokens_used": result.get("tokens_used", 0),
                "response_time_ms": result.get("response_time_ms", 0),
            },
        )
        return jsonify(result)

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """Chat de refinamento contextual das respostas geradas."""
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id", str(uuid.uuid4())[:8])
        agent_type = data.get("agent_type", "planejamento")
        user_msg = data.get("message", "").strip()
        context_key = f"{session_id}:{agent_type}"

        if not user_msg:
            return jsonify({"success": False, "content": "Mensagem vazia."}), 400

        system_prompt = (
            "Você é o assistente IncluSign AI em modo de chat de refinamento. "
            "Seu objetivo é ajudar o usuário a ajustar ou tirar dúvidas sobre a tradução ou plano gerado. "
            "Responda diretamente e com naturalidade em Português do Brasil (PT-BR)."
        )

        history = chat_histories[context_key]
        history.append({"role": "user", "content": user_msg})
        if len(history) > 6:
            history = history[-6:]
            chat_histories[context_key] = history

        stream_mode = data.get("stream", False)
        start_time = time.time()

        result = llm.generate(
            prompt=user_msg,
            system_prompt=system_prompt,
            messages_override=history,
            stream=stream_mode,
        )

        if stream_mode:
            def sse_generator():
                full_content = ""
                total_content_length = 0
                for chunk_data in result:
                    if isinstance(chunk_data, dict):
                        chunk_str = chunk_data.get("content", "")
                        is_thinking = chunk_data.get("is_thinking", False)
                    else:
                        chunk_str = chunk_data
                        is_thinking = False

                    if not is_thinking:
                        full_content += chunk_str

                    total_content_length += len(chunk_str)
                    yield f"data: {json.dumps({'content': chunk_str, 'success': True, 'is_thinking': is_thinking})}\n\n"

                history.append({"role": "assistant", "content": full_content})
                elapsed_ms = int((time.time() - start_time) * 1000)
                estimated_tokens = total_content_length // 4

                telemetry.log_interaction(
                    session_id=session_id,
                    agent_type=f"chat_{agent_type}",
                    input_data={"message": user_msg},
                    output_data={"success": True, "content": full_content},
                    metadata={"tokens_used": estimated_tokens, "response_time_ms": elapsed_ms},
                )
                yield f"data: {json.dumps({'done': True, 'response_time_ms': elapsed_ms, 'tokens_used': estimated_tokens})}\n\n"

            return Response(sse_generator(), mimetype="text/event-stream")

        elapsed_ms = int((time.time() - start_time) * 1000)
        if result.get("success"):
            history.append({"role": "assistant", "content": result["content"]})

        telemetry.log_interaction(
            session_id=session_id,
            agent_type=f"chat_{agent_type}",
            input_data={"message": user_msg},
            output_data={"success": result.get("success", False), "content": result.get("content", "")},
            metadata={"tokens_used": result.get("tokens_used", 0), "response_time_ms": elapsed_ms},
        )

        return jsonify({
            "success": result.get("success", False),
            "content": result.get("content", ""),
            "tokens_used": result.get("tokens_used", 0),
            "response_time_ms": elapsed_ms,
        })

    @app.route("/api/telemetry", methods=["GET"])
    def api_telemetry():
        """Consulta o histórico e estatísticas de telemetria."""
        limit = request.args.get("limit", 50, type=int)
        history = telemetry.get_history(limit=limit)
        stats = telemetry.get_stats()
        return jsonify({
            "historico": history,
            "estatisticas": stats,
        })

    @app.route("/api/telemetry/export", methods=["GET"])
    def api_telemetry_export():
        """Exporta dados de telemetria em formato CSV ou TXT."""
        fmt = request.args.get("format", "csv").lower()
        if fmt == "txt":
            content = telemetry.export_txt()
            return Response(
                content,
                mimetype="text/plain; charset=utf-8",
                headers={"Content-Disposition": "attachment; filename=inclusign_telemetria.txt"},
            )
        content = telemetry.export_csv()
        return Response(
            content,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=inclusign_telemetria.csv"},
        )

    @app.route("/api/rag/reindex", methods=["POST"])
    def api_rag_reindex():
        """Re-indexa os documentos vetoriais sob demanda."""
        if rag:
            result = rag.reindex()
            return jsonify(result)
        return jsonify({
            "success": False,
            "message": "Serviço RAG não disponível.",
        }), 503

    # ------------------------------------------------------------------------
    # TRATAMENTO DE ERROS
    # ------------------------------------------------------------------------

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Recurso não encontrado."}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Erro interno no servidor: %s", error)
        return jsonify({"error": "Erro interno do servidor. Tente novamente."}), 500

    return app


# Instância padrão para execução direta ou via servidor WSGI (ex.: gunicorn)
app = create_app()


def handle_shutdown(signum, frame):
    """Encerramento gracioso dos processos."""
    logger.info("Sinal de término recebido (%s). Finalizando aplicação...", signum)
    sys.exit(0)


if __name__ == "__main__":
    # Registro de sinais para encerramento gracioso
    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("=" * 60)
    logger.info("  IncluSign AI — Plataforma Pronta (CICURV 2026)")
    logger.info("  URL: http://%s:%s", SERVER_HOST, SERVER_PORT)
    logger.info("=" * 60)

    app.run(
        host=SERVER_HOST,
        port=SERVER_PORT,
        debug=DEBUG_MODE,
    )
