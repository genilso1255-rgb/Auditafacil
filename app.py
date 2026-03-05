import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_preciso(texto_linha):
    # Captura valores como 2.164,77 garantindo que o ponto do milhar seja lido
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_auditar_facil_v7(arquivos):
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0,
        "MATERIAL ESPECIAL": 0.0,
        "MEDICAMENTOS": 0.0,
        "GASES": 0.0,
        "TAXAS": 0.0,
        "DIÁRIAS": 0.0,
        "HONORÁRIOS": 0.0,
        "EXAMES": 0.0,
        "PACOTES ESPECIAIS": 0.0
    }

    setores_ignorar = ["632 -", "652 -", "658 -", "TOTAL DO SETOR", "VALOR TOTAL DA GUIA"]

    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # OCR com configuração para tabelas (PSM 6)
        texto = pytesseract.image_to_string(gray, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if not ln or any(s in ln for s in setores_ignorar): continue
            
            valor = extrair_valor_preciso(ln)
            if valor <= 0: continue

            # --- GAVETAS (REFINADO) ---
            
            # HONORÁRIOS (NARIZ incluído com força total)
            if any(x in ln for x in ["NARIZ", "CABECA", "PESCOCO", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "MUSCULO", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor
            
            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS", "MATERIAIS", "DESCARTAVEL", "AGULHA"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MEDICAMENTOS
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
                
            # MATERIAL ESPECIAL
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMINIST"]):
                resumo["TAXAS"] += valor
                
            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor

            # Demais gavetas (Gases, Diárias, Exames) seguem a mesma lógica...
            elif any(x in ln for x in ["DIARIA", "PERNOITE"]): resumo["DIÁRIAS"] += valor
            elif any(x in ln for x in ["GASES", "OXIGENIO"]): resumo["GASES"] += valor
            elif any(x in ln for x in ["RAIO X", "IMAGEM", "LABORAT"]): resumo["EXAMES"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Batimento Final", layout="wide")
st.title("🛡️ Auditar Fácil - Batimento de Conta")

uploads = st.file_uploader("Suba as imagens", accept_multiple_files=True)

if uploads:
    resultado = processar_auditar_facil_v7(uploads)
    st.subheader("📋 Resumo da Conta")
    col1, col2 = st.columns(2)
    with col1:
        for cat, total in resultado.items():
            st.write(f"**{cat}:** R$ {total:,.2f}")
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL DA CONTA", f"R$ {total_geral:,.2f}")
        
