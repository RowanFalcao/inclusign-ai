"""
IncluSign AI — Serviço de LLM (Adapter Pattern)
================================================
Toda comunicação com o modelo de linguagem passa por este arquivo.
Para migrar o modelo ou a API no futuro, altere SOMENTE este arquivo.

Padrão de Projeto: Adapter
Requisitos atendidos: RNF-004, RNF-002, RNF-005, RNF-006
"""

import json
import logging

import requests

from config import (
    LLM_MAX_CONTEXT,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OLLAMA_MODEL,
    OLLAMA_URL,
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    Adapter para comunicação com o LLM local via Ollama.
    """

    def __init__(
        self,
        url: str = OLLAMA_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = LLM_TIMEOUT,
    ):
        self.url = url.rstrip("/") if url else ""
        self.model = model
        self.timeout = timeout
        self._available = False  # cache de status
        self.active_type = "local"  # "nuvem" ou "local"

    # ------------------------------------------------------------------
    # Interface Pública
    # ------------------------------------------------------------------

    def _check_endpoint(self, url: str, timeout: int = 3) -> bool:
        """Helper para verificar se um endpoint Ollama específico está respondendo."""
        if not url:
            return False
        try:
            resp = requests.get(f"{url}/api/tags", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self.model.split(":")[0]
                has_model = any(model_base in m for m in models)
                if not has_model:
                    logger.warning(
                        "Ollama acessível em %s, mas modelo '%s' não encontrado.", url, self.model
                    )
                return has_model
            return False
        except requests.RequestException:
            return False

    def is_available(self) -> bool:
        """
        Verifica se o Ollama local está online e respondendo.
        """
        if self._check_endpoint(self.url, timeout=3):
            self._available = True
            return True

        self._available = False
        return False

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        messages_override: list | None = None,
        stream: bool = False,
        think: bool = False,
    ):
        """
        Gera uma resposta do LLM via Ollama (/api/generate).

        Parâmetros:
            prompt: Texto do usuário.
            system_prompt: Instruções invisíveis ao usuário.
            temperature: Controle de criatividade (0.0 = determinístico).
            max_tokens: Limite de tokens na resposta.
            messages_override: Histórico de mensagens (não usado no Ollama atual).

        Retorna:
            dict com chaves:
                - "success": bool
                - "content": str (texto gerado) ou mensagem de erro
                - "tokens_used": int (tokens consumidos, se disponível)
        """
        if temperature is None:
            temperature = LLM_TEMPERATURE
        if max_tokens is None:
            max_tokens = LLM_MAX_TOKENS

        if not self._available:
            self.is_available()

        if not self._available:
            return {
                "success": False,
                "content": "Servidor de IA local não disponível.",
                "tokens_used": 0,
            }

        # Sempre construir mensagens no formato do chat para garantir o uso correto do template do modelo
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if messages_override:
            messages.extend(messages_override)
        else:
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "repeat_penalty": 1.0,
                "num_predict": max_tokens,
                "num_ctx": LLM_MAX_CONTEXT,
                "num_gpu": 99,
            },
            "keep_alive": -1,
            "think": True,
        }
        endpoint = f"{self.url}/api/chat"

        try:
            if stream:
                resp = requests.post(endpoint, json=payload, stream=True, timeout=self.timeout)
                resp.raise_for_status()

                def token_generator():
                    in_fallback_thinking = False
                    buffer = ""
                    # Prefixos parciais possíveis para retenção durante streaming
                    tag_prefixes = (
                        "</think>",
                        "</think",
                        "</thin",
                        "</thi",
                        "</th",
                        "</t",
                        "</",
                        "<think>",
                        "<think",
                        "<thin",
                        "<thi",
                        "<th",
                        "<t",
                        "<",
                    )

                    for line in resp.iter_lines():
                        if line:
                            data = json.loads(line)
                            msg = data.get("message", {})

                            thinking_token = msg.get("thinking", "")
                            content_token = msg.get("content", "")

                            # 1. Separação de tokens de raciocínio da API do Ollama
                            if thinking_token:
                                yield {"content": thinking_token, "is_thinking": True}
                                continue

                            # 2. Processamento do buffer de saída e mitigação de fragmentação de delimitadores
                            if content_token:
                                buffer += content_token

                                # Tratamento de tag de abertura
                                if "<think>" in buffer:
                                    in_fallback_thinking = True
                                    buffer = buffer.replace("<think>", "")

                                # Tratamento de tag de fechamento
                                if "</think>" in buffer:
                                    in_fallback_thinking = False
                                    buffer = buffer.replace("</think>", "")

                                # Verifica se o buffer termina com algum prefixo parcial de tag
                                hold_len = 0
                                for prefix in tag_prefixes:
                                    if buffer.endswith(prefix):
                                        hold_len = len(prefix)
                                        break

                                if hold_len > 0:
                                    emit_part = buffer[:-hold_len]
                                    buffer = buffer[-hold_len:]
                                else:
                                    emit_part = buffer
                                    buffer = ""

                                if emit_part:
                                    yield {
                                        "content": emit_part,
                                        "is_thinking": in_fallback_thinking,
                                    }

                    # Ao final do stream, emitir qualquer resquício seguro do buffer
                    if buffer:
                        buffer = buffer.replace("<think>", "").replace("</think>", "")
                        if buffer:
                            yield {"content": buffer, "is_thinking": in_fallback_thinking}

                return token_generator()

            # Processamento síncrono (sem streaming)
            resp = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            # Extração do conteúdo principal fornecido pela API
            content = data.get("message", {}).get("content", "")

            # Truncamento defensivo em caso de repetição de seções estruturais
            first_h3 = content.find("### 1.")
            if first_h3 != -1:
                second_h3 = content.find("### 1.", first_h3 + 6)
                if second_h3 != -1:
                    content = content[:second_h3]

            content = content.strip()
            tokens = data.get("eval_count", 0)

            return {
                "success": True,
                "content": content,
                "tokens_used": tokens,
            }

        except requests.Timeout:
            msg = (
                "O modelo de IA demorou mais do que o esperado para responder. "
                "Por favor, tente novamente com uma pergunta mais curta."
            )
            logger.error("Timeout na requisição ao LLM (%ds)", self.timeout)
            return {"success": False, "content": msg, "tokens_used": 0}

        except requests.ConnectionError:
            msg = (
                "Não foi possível conectar ao servidor de IA. "
                "Verifique se o Ollama local está em execução."
            )
            logger.error("Falha de conexão com Ollama em %s", self.url)
            return {"success": False, "content": msg, "tokens_used": 0}

        except requests.HTTPError as exc:
            msg = "O servidor de IA retornou um erro interno. Tente novamente em alguns instantes."
            logger.error("Erro HTTP do Ollama: %s", exc)
            return {"success": False, "content": msg, "tokens_used": 0}

        except (json.JSONDecodeError, KeyError) as exc:
            msg = "Erro ao processar a resposta do modelo de IA."
            logger.error("Erro de parse na resposta do LLM: %s", exc)
            return {"success": False, "content": msg, "tokens_used": 0}

    def get_status(self) -> dict:
        """Retorna informações de status do serviço LLM."""
        available = self.is_available()
        return {
            "disponivel": available,
            "modelo": self.model,
            "servidor": self.url,
            "tipo": self.active_type,
            "mensagem": (
                f"Modelo {self.model} pronto para inferência."
                if available
                else "Servidor de IA local não disponível."
            ),
        }
