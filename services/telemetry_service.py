# -*- coding: utf-8 -*-
"""
IncluSign AI — Serviço de Telemetria
=====================================
Registro de interações para fins de pesquisa acadêmica.
Exportação em CSV e TXT para análise qualitativa.

Requisitos atendidos: RF-014, RF-015, RNF-001
Atributos de qualidade: Confiabilidade, Segurança (sem dados pessoais)
"""

import csv
import io
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from config import LOGS_DIR, LOG_FILENAME_PATTERN

logger = logging.getLogger(__name__)


class TelemetryService:
    """
    Registra e exporta interações do sistema para pesquisa.

    Formato de armazenamento: JSON Lines (.jsonl) — uma linha por interação.
    Não armazena dados pessoais ou de identificação (RNF-001).
    """

    def __init__(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._log_file = self._get_log_filepath()

    def _get_log_filepath(self) -> Path:
        """Retorna o caminho do arquivo de log do dia atual."""
        today = datetime.now().strftime("%Y-%m-%d")
        filename = LOG_FILENAME_PATTERN.format(date=today)
        return LOGS_DIR / filename

    def log_interaction(
        self,
        session_id: str,
        agent_type: str,
        input_data: dict,
        output_data: dict,
        metadata: dict | None = None,
    ) -> str:
        """
        Registra uma interação no log.

        Parâmetros:
            session_id: ID da sessão educacional.
            agent_type: Tipo do agente ("traducao" ou "planejamento").
            input_data: Dados de entrada (sem informações pessoais).
            output_data: Resposta gerada pelo sistema.
            metadata: Dados adicionais (tempo de resposta, tokens, etc.).

        Retorna:
            ID único da interação registrada.
        """
        interaction_id = str(uuid.uuid4())[:8]

        record = {
            "id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "agent_type": agent_type,
            "input": self._sanitize_data(input_data),
            "output": self._sanitize_data(output_data),
            "metadata": metadata or {},
        }

        try:
            # Atualizar caminho caso tenha mudado o dia
            self._log_file = self._get_log_filepath()

            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            logger.debug("Interação registrada: %s", interaction_id)

        except Exception as exc:
            logger.error("Erro ao registrar interação: %s", exc)

        return interaction_id

    def _sanitize_data(self, data: dict) -> dict:
        """
        Remove ou anonimiza dados potencialmente sensíveis (RNF-001).
        Filtra campos que possam conter informações pessoais.
        """
        sensitive_keys = {"nome", "email", "cpf", "telefone", "endereco", "ip"}
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[ANONIMIZADO]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        return sanitized

    def get_history(self, limit: int = 50) -> list[dict]:
        """
        Retorna as últimas interações registradas.

        Parâmetros:
            limit: Número máximo de registros a retornar.

        Retorna:
            Lista de dicts com as interações (mais recentes primeiro).
        """
        all_records = []

        try:
            # Ler todos os arquivos de log, ordenados por data
            log_files = sorted(LOGS_DIR.glob("*.jsonl"), reverse=True)

            for log_file in log_files:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                record = json.loads(line)
                                all_records.append(record)
                            except json.JSONDecodeError:
                                continue

                if len(all_records) >= limit:
                    break

        except Exception as exc:
            logger.error("Erro ao ler histórico: %s", exc)

        # Ordenar por timestamp decrescente e limitar
        all_records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return all_records[:limit]

    def export_csv(self) -> str:
        """
        Exporta todo o histórico em formato CSV (RF-015).

        Retorna:
            String contendo o CSV formatado.
        """
        records = self.get_history(limit=10000)

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Cabeçalho
        writer.writerow([
            "ID",
            "Data/Hora",
            "Sessão",
            "Agente",
            "Entrada",
            "Saída",
            "Tokens",
            "Tempo (ms)",
        ])

        for record in records:
            meta = record.get("metadata", {})
            writer.writerow([
                record.get("id", ""),
                record.get("timestamp", ""),
                record.get("session_id", ""),
                record.get("agent_type", ""),
                json.dumps(record.get("input", {}), ensure_ascii=False),
                json.dumps(record.get("output", {}), ensure_ascii=False),
                meta.get("tokens_used", ""),
                meta.get("response_time_ms", ""),
            ])

        return output.getvalue()

    def export_txt(self) -> str:
        """
        Exporta todo o histórico em formato TXT legível (RF-015).

        Retorna:
            String contendo o relatório formatado.
        """
        records = self.get_history(limit=10000)
        lines = []

        lines.append("=" * 80)
        lines.append("INCLUSIGN AI — RELATÓRIO DE TELEMETRIA")
        lines.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Total de interações: {len(records)}")
        lines.append("=" * 80)
        lines.append("")

        for i, record in enumerate(records, 1):
            lines.append(f"--- Interação #{i} ---")
            lines.append(f"  ID:        {record.get('id', 'N/A')}")
            lines.append(f"  Data/Hora: {record.get('timestamp', 'N/A')}")
            lines.append(f"  Sessão:    {record.get('session_id', 'N/A')}")
            lines.append(f"  Agente:    {record.get('agent_type', 'N/A')}")

            input_data = record.get("input", {})
            lines.append(f"  Entrada:   {json.dumps(input_data, ensure_ascii=False)}")

            output_data = record.get("output", {})
            output_content = output_data.get("content", str(output_data))
            lines.append(f"  Saída:     {output_content}")

            meta = record.get("metadata", {})
            if meta:
                lines.append(f"  Tokens:    {meta.get('tokens_used', 'N/A')}")
                lines.append(f"  Tempo:     {meta.get('response_time_ms', 'N/A')} ms")

            lines.append("")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Retorna estatísticas da telemetria."""
        records = self.get_history(limit=10000)
        traducao_count = sum(
            1 for r in records if r.get("agent_type") == "traducao"
        )
        planejamento_count = sum(
            1 for r in records if r.get("agent_type") == "planejamento"
        )

        return {
            "total_interacoes": len(records),
            "traducoes": traducao_count,
            "planejamentos": planejamento_count,
            "pasta_logs": str(LOGS_DIR),
        }
