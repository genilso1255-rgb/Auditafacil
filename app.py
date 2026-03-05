import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_br(texto_linha):
    # Padrão para pegar 22.831,31 ou 575,81 (sempre o último da linha)
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_auditar_facil_blindado(arquivos):
    # ESTRUTURA FIXA (Sempre exibe estas categorias)
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

    setores_ignorar = ["CENTRO CIRURGICO", "APARTAMENTO", "CTI ADULTO", "TOTAL DO SETOR", "VALOR TOTAL DA GUIA"]

    for arq in arquivos:
        img = np.array(Image.open(arq).convert('RGB'))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Limpeza para OCR em documentos com sombras
        img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if any(s in ln for s in setores_ignorar): continue
            
            valor = extrair_valor_br(ln)
            if valor <= 0: continue

            # --- REGRAS DE GAVETA (PONTO FINAL) ---
            
            # HONORÁRIOS (Incluindo Anatomia e Sistemas)
            if any(x in ln for x in ["HONORARIO", "CABECA", "PESCOCO", "NARIZ", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "MUSCULAR"]):
                resumo["HONORÁRIOS"] += valor
            
            # GASES
            elif any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPRIMIDO"]):
                resumo["GASES"] += valor

            # MATERIAL DESCARTÁVEL
            elif any(x in ln for x in ["FIOS CIR", "MATERIAIS HOSPITALARES", "DESCARTAVEL", "AGULHA"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # MEDICAMENTOS
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "NUTRICAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO"]):
                resumo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA"]):
                resumo["DIÁRIAS"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORATORIO", "TOMOGRAFIA"]):
                resumo["EXAMES"] += valor

            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Blindado", layout="wide")
st.title("🛡️ Auditar Fácil - Versão 100% Blindada")

uploads = st.file_uploader("Suba as imagens", accept_multiple_files=True)

if uploads:
    resultado = processar_auditar_facil_blindado(uploads)
    
    st.subheader("📋 Resumo Consolidado (Conta Suja)")
    
    col1, col2 = st.columns(2)
    with col1:
        # Exibe TODAS as categorias, mesmo as zeradas
        for cat, total in resultado.items():
            cor = "green" if total > 0 else "gray"
            st.markdown(f":{cor}[**{cat}:** R$ {total:,.2f}]")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL BRUTO IDENTIFICADO", f"R$ {total_geral:,.2f}")
        
    st.divider()
    st.info("O sistema agora soma 'Seios', 'Sistemas' e 'Anatomia' em HONORÁRIOS.")
    
