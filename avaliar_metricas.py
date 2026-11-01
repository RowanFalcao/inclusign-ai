# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path
import sacrebleu
from sentence_transformers import SentenceTransformer, util
from evaluate import load
import numpy as np
import warnings

# Supressão de avisos de truncamento de tokens durante a avaliação
warnings.filterwarnings("ignore")

print("Inicializando módulos de avaliação em PLN (BERTScore, SARI, SBERT)...")

# --- 1. CARREGAMENTO DAS CALCULADORAS ---
bertscore = load("bertscore")
sari = load("sari")
modelo_sbert = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

# --- 2. CAMINHOS DINÂMICOS E AGNÓSTICOS ---
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
KB_DIR = BASE_DIR / "base-conhecimento"

DICIONARIOS = {
    "computacao": KB_DIR / "dicionario_computacao_libras.txt",
    "agronomia": KB_DIR / "dicionario_agronomia_libras.txt",
    "medicina": KB_DIR / "dicionario_medicina_libras.txt"
}

MANUAIS = {
    "tdah": KB_DIR / "Manual_Pedagogico_Formativo_em_TDAH_2024.txt",
    "tea": KB_DIR / "Guia_Pratico_para_Professores-Estrategias_e_Recursos_para_Inclusao_de_Estudantes_Autistas_C.M.Sousa_L.A.Lourinho_UDESC_2022.txt",
    "surdez": KB_DIR / "Caderno_Pedagogico_da_Politica_Nac_de_Educacao_Especial_Inclusiva_Colecao_2026_2026-4-5-cadermec-vol-2_compressed.txt"
}

# --- 3. FUNÇÕES DE EXTRAÇÃO ---
def extrair_padrao_ouro(termo, ficheiro_dicionario):
    try:
        conteudo = ficheiro_dicionario.read_text(encoding="utf-8")
        padrao = rf"TERMO TÉCNICO: \d{{2}} - {re.escape(termo)}.*?CONCEITO: (.*?)\nDESCRIÇÃO GLOSADA \(LIBRAS\): (.*?)\n"
        match = re.search(padrao, conteudo, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    except Exception:
        pass
    return "", ""

def extrair_glosa_ia(texto_completo):
    # Extração exclusiva da seção de glosa para cálculo de métricas estruturais (TER e chrF)
    match = re.search(r"3\.1 Transcrição em Glosa.*?\n\n(.*?)(?=\n### 4)", texto_completo, re.DOTALL)
    if match:
        glosa = match.group(1).replace("[Aviso: Termo não encontrado no dicionário. Sugestão gerada por IA sujeita a validação.]", "").strip()
        # Remoção do identificador de cabeçalho do termo para isolar a transcrição
        glosa = re.sub(r"^\*\*.*?\*\*:?\s*", "", glosa).strip()
        return glosa
    return texto_completo

# --- 4. PROCESSAMENTO DOS MÓDULOS ---
def avaliar_modulo_traducao():
    log_file = LOGS_DIR / "inclusign_telemetry_2026-10-06.jsonl"
    if not log_file.exists():
        return None
    
    inputs, refs_glosa, outputs_ia = [], [], []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for linha in f:
            if not linha.strip(): continue
            registro = json.loads(linha)
            if registro.get("agent_type") == "traducao":
                termo = registro["input"].get("termo", "")
                dominio = registro["input"].get("dominio", "")
                output_texto = registro["output"].get("content", "")
                
                ficheiro_dic = DICIONARIOS.get(dominio)
                if ficheiro_dic and ficheiro_dic.exists():
                    conceito_orig, glosa_ouro = extrair_padrao_ouro(termo, ficheiro_dic)
                    glosa_ia = extrair_glosa_ia(output_texto)
                    
                    if conceito_orig and glosa_ouro and glosa_ia:
                        inputs.append(conceito_orig)
                        refs_glosa.append(glosa_ouro)
                        outputs_ia.append(glosa_ia)

    if not outputs_ia: return None

    # Cálculos
    refs_sacrebleu = [[ref] for ref in refs_glosa]
    nota_sari = sari.compute(sources=inputs, predictions=outputs_ia, references=[[r] for r in refs_glosa])
    res_bert = bertscore.compute(predictions=outputs_ia, references=refs_glosa, lang="pt")
    media_bert = np.mean(res_bert['f1'])
    
    emb_ref = modelo_sbert.encode(refs_glosa)
    emb_cand = modelo_sbert.encode(outputs_ia)
    similaridade = np.mean([util.cos_sim(r, c).item() for r, c in zip(emb_ref, emb_cand)])
    
    nota_chrf = sacrebleu.corpus_chrf(outputs_ia, refs_sacrebleu).score
    nota_ter = sacrebleu.corpus_ter(outputs_ia, refs_sacrebleu).score / 100

    return {
        "bertscore": media_bert, "sari": nota_sari['sari'], 
        "sbert": similaridade, "chrf": nota_chrf, "ter": nota_ter, "amostra": len(outputs_ia)
    }

def avaliar_modulo_planeamento():
    log_file = LOGS_DIR / "inclusign_telemetry_2026-10-07.jsonl"
    if not log_file.exists():
        return None
    
    refs_manuais, outputs_ia = [], []
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for linha in f:
            if not linha.strip(): continue
            registro = json.loads(linha)
            if registro.get("agent_type") == "planejamento":
                perfil = registro["input"].get("perfil", "")
                output_texto = registro["output"].get("content", "")
                
                ficheiro_manual = MANUAIS.get(perfil)
                if ficheiro_manual and ficheiro_manual.exists():
                    # Carregamento do documento pedagógico integral como referência semântica
                    texto_manual = ficheiro_manual.read_text(encoding="utf-8")
                    refs_manuais.append(texto_manual)
                    outputs_ia.append(output_texto)
                    
    if not outputs_ia: return None

    # Avaliação semântica via BERTScore e SBERT para documentos extensos
    res_bert = bertscore.compute(predictions=outputs_ia, references=refs_manuais, lang="pt")
    media_bert = np.mean(res_bert['f1'])
    
    emb_ref = modelo_sbert.encode(refs_manuais)
    emb_cand = modelo_sbert.encode(outputs_ia)
    similaridade = np.mean([util.cos_sim(r, c).item() for r, c in zip(emb_ref, emb_cand)])
    
    return {"bertscore": media_bert, "sbert": similaridade, "amostra": len(outputs_ia)}

# --- 5. EXECUÇÃO E RELATÓRIO ---
print("\n" + "="*60)
print(" RELATÓRIO DE MÉTRICAS CIENTÍFICAS - INCLUSIGN AI")
print("="*60)

res_trad = avaliar_modulo_traducao()
if res_trad:
    print(f"\n[MÓDULO 2 - TRADUÇÃO CONTEXTUAL PARA LIBRAS] (Amostra: {res_trad['amostra']} testes)")
    print(f"1. CLAREZA (BERTScore): {res_trad['bertscore']:.2f} (Retenção semântica)")
    print(f"   CLAREZA (SARI):      {res_trad['sari']:.1f} (Simplificação lexical)")
    print(f"2. ADERÊNCIA (SBERT):   {res_trad['sbert']:.2f} (Alinhamento ao contexto educacional)")
    print(f"3. VISUALIZAÇÃO (chrF): {res_trad['chrf']:.1f} (Sobreposição de traços não-manuais)")
    print(f"4. FACILIDADE (TER):    {res_trad['ter']:.2f} (Esforço de edição estrutural)")
else:
    print("\n[MÓDULO 2] - Sem dados encontrados no log de 2026-10-06.")

res_plan = avaliar_modulo_planeamento()
if res_plan:
    print(f"\n[MÓDULO 3 - PLANEAMENTO PEDAGÓGICO ADAPTADO] (Amostra: {res_plan['amostra']} testes)")
    print(f"1. RETENÇÃO FACTUAL (BERTScore): {res_plan['bertscore']:.2f} (Alinhamento com os manuais oficiais)")
    print(f"2. ADERÊNCIA AO DUA (SBERT):     {res_plan['sbert']:.2f} (Relevância das estratégias sugeridas)")
else:
    print("\n[MÓDULO 3] - Sem dados encontrados no log de 2026-10-07.")

print("\n" + "="*60 + "\n")