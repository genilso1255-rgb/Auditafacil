import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_milhar(texto_linha):
    # Procura especificamente o padrão de milhares: XX.XXX,XX
    # Se não achar, procura o padrão simples: XXX,XX
    match = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', texto_linha)
    if match:
        # Pega o último valor da linha (coluna Total)
        valor_str = match[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_auditar_facil_v_perfeita(arquivos):
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
        
        # OCR com foco em manter a estrutura da linha
        texto = pytesseract.image_to_string(gray, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if not ln or any(s in ln for s in setores_ignorar): continue
            
            valor = extrair_valor_milhar(ln)
            if valor <= 0: continue

            # --- REGRAS DE GAVETA (PRIORIDADE TOTAL) ---
            
            # 1. HONORÁRIOS (Sistemas e Anatomia)
            if any(x in ln for x in ["NARIZ", "CABECA", "PESCOCO", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "MUSCULO", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor
            
            # 2. MATERIAL DESCARTÁVEL (Materiais e Fios)
            elif any(x in ln for x in ["MATERIAIS", "HOSPITALARES", "FIOS", "DESCARTAVEL", "AGULHA"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # 3. MEDICAMENTOS
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
                
            # 4. MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # 5. TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMINIST"]):
                resumo["TAXAS"] += valor
                
            # 6. PACOTES / OUTROS
            elif "PACOTE" in ln: resumo["PACOTES ESPECIAIS"] += valor
            elif any(x in ln for x in ["DIARIA", "PERNOITE"]): resumo["DIÁRIAS"] += valor
            elif any(x in ln for x in ["GASES", "OXIGENIO"]): resumo["GASES"] += valor
            elif any(x in ln for x in ["IMAGEM", "RAIO X"]): resumo["EXAMES"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - VERSÃO 75K", layout="wide")
st.title("🛡️ Auditar Fácil - Ajuste Final de Milhares")

uploads = st.file_uploader("Suba a imagem da conta", accept_multiple_files=True)

if uploads:
    resultado = processar_auditar_facil_v_perfeita(uploads)
    
    st.subheader("📊 Relatório Final")
    col1, col2 = st.columns(2)
    with col1:
        for cat, total in resultado.items():
            st.write(f"✅ **{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL DA CONTA IDENTIFICADO", f"R$ {total_geral:,.2f}")
        
    st.divider()
    st.warning("Verifique se MATERIAIS HOSPITALARES somou os R$ 22.831,31 corretamente.")
            
