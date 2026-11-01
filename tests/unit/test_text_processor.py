# -*- coding: utf-8 -*-
"""Testes unitários para o processador textual e higienização de dados."""

from services.text_processor import TextProcessor


def test_clean_extracted_blocks_removes_unwanted_characters():
    """Valida se o processador remove caracteres de controle e ruídos de OCR."""
    raw_blocks = [
        "Capítulo 1: Introdução ao DUA\n\n",
        "O Desenho Universal para a Aprendizagem... \x00\x0c",
        "  Página 1 de 50  ",
    ]
    cleaned = TextProcessor.clean_extracted_blocks(raw_blocks)
    assert "Capítulo 1: Introdução ao DUA" in cleaned
    assert "\x00" not in cleaned
    assert "\x0c" not in cleaned


def test_clean_extracted_blocks_empty_input():
    """Valida comportamento defensivo para entradas vazias."""
    cleaned = TextProcessor.clean_extracted_blocks([])
    assert cleaned == ""

