"""
IncluSign AI — Processador Textual
===================================
Higienização, remoção de ruídos de OCR e normalização estrutural de documentos.
"""

from __future__ import annotations

import re


class TextProcessor:
    """
    Serviço especializado em higienização e formatação de textos extraídos de PDFs.
    Padrão de Projeto: Strategy / Single Responsibility Principle
    """

    @staticmethod
    def clean_extracted_blocks(blocks: list[str]) -> str:
        """Limpa blocos de texto extraídos de PDFs, eliminando ruídos e caracteres de controle."""
        final_text = ""

        for block in blocks:
            # 0. Remove caracteres nulos e caracteres de controle não imprimíveis
            block_clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", block)
            block_clean = block_clean.strip()

            # 1. Filtra blocos vazios ou cadeias exclusivamente numéricas/simbólicas
            if not block_clean or re.match(r"^[\d\s\W]+$", block_clean):
                continue

            # 2. Filtra linhas de índices e sumários com pontilhados
            if re.search(r"\.{4,}", block_clean):
                continue

            # 3. Filtra cabeçalhos e seções de referências documentais
            upper_block = block_clean.upper()
            if upper_block in [
                "SUMÁRIO",
                "GLOSSÁRIO",
                "ÍNDICE",
                "REFERÊNCIAS",
                "REFERÊNCIAS BIBLIOGRÁFICAS",
                "BIBLIOGRAFIA",
            ]:
                continue

            # 4. Reconstitui termos com quebra de hifenização entre linhas
            block_clean = re.sub(r"(\w+)-\s*[\n\r]*\s*(\w+)", r"\1\2", block_clean)

            # 5. Normaliza quebras de linha internas preservando o fluxo textual
            block_clean = block_clean.replace("\n", " ")

            # 6. Remove espaços redundantes e normaliza ligaduras tipográficas
            block_clean = re.sub(r"[ \t]{2,}", " ", block_clean)
            block_clean = (
                block_clean.replace("ﬁ ", "fi")
                .replace("ﬂ ", "fl")
                .replace("ﬁ", "fi")
                .replace("ﬂ", "fl")
            )

            # 7. Concatena blocos textuais conforme pontuação final
            if final_text:
                if not final_text.strip().endswith((".", ";", "!", "?", ":")):
                    final_text += " " + block_clean
                else:
                    final_text += "\n\n" + block_clean
            else:
                final_text = block_clean

        return final_text
