import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_br(texto_linha):
    # Captura o último valor da linha no formato 0.000,00
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_auditar_facil_v5(arquivos):
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

    # Títulos de setores para ignorar e evitar duplicidade
    setores_ignorar = ["CENTRO CIRURGICO", "APARTAMENTO", "CTI ADULTO", "TOTAL DO SETOR", "VALOR TOTAL DA GUIA"]

    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        # Melhora o brilho para ler o texto sob o carimbo "Daniele Gondim"
        img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if not ln or any(s in ln for s in setores_ignorar): continue
            
            valor = extrair_valor_br(ln)
            if valor <= 0: continue

            # --- REGRAS DE GAVETA (VERSÃO FINAL) ---
            
            # HONORÁRIOS (Reforçado para capturar Sistemas e Anatomia)
            if any(x in ln for x in ["HONORARIO", "CABECA", "PESCOCO", "NARIZ", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "MUSCULO", "ESQUELET"]):
                resumo["HONORÁRIOS"] += valor
            
            # GASES
            elif any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPRIMIDO"]):
                resumo["GASES"] += valor

            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS CIR", "MATERIAIS HOSPITALARES", "DESCARTAVEL", "AGULHA", "CATETER"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # MEDICAMENTOS (Remédios + Dietas)
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "NUTRICAO", "SORO", "RESTRI"]):
                resumo["MEDICAMENTOS"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO", "ADMINISTRATIVA"]):
                resumo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "ENFERMARIA"]):
                resumo["DIÁRIAS"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORATORIO", "TOMOGRAFIA"]):
                resumo["EXAMES"] += valor

            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Pro", layout="wide")
st.title("🛡️ Auditar Fácil - Versão Final (Ajuste de Anatomia)")

uploads = st.file_uploader("Suba as imagens", accept_multiple_files=True)

if uploads:
    with st.spinner('Processando...'):
        resultado = processar_auditar_facil_v5(uploads)
    
    st.subheader("📊 Resultado Consolidado")
    col1, col2 = st.columns(2)
    with col1:
        for cat, total in resultado.items():
            st.write(f"✅ **{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL DA CONTA", f"R$ {total_geral:,.2f}")
        if total_geral > 0:
            st.success("Sistemas Nervoso e Muscular incluídos em Honorários.")
            
