import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_total_linha(texto_linha):
    # Regex robusta para capturar o último valor financeiro da linha (Coluna Total)
    # Suporta formatos como 22.831,31 ou 817,31
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_auditar_facil_75k(arquivos):
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
        
        # OCR com PSM 6 para ler a linha como uma unidade de dados
        texto = pytesseract.image_to_string(gray, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if not ln or any(s in ln for s in setores_ignorar): continue
            
            valor = extrair_valor_total_linha(ln)
            if valor <= 0: continue

            # --- MAPEAMENTO DEFINITIVO ---
            
            # HONORÁRIOS (Sistemas, Anatomia e Honorários)
            if any(x in ln for x in ["NARIZ", "CABECA", "PESCOCO", "OLHOS", "SEIOS", "NERVOSO", "SISTEMA", "MUSCULO", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor
            
            # MATERIAL DESCARTÁVEL (Materiais Hospitalares e Fios)
            elif any(x in ln for x in ["MATERIAIS", "HOSPITALARES", "FIOS", "DESCARTAVEL", "AGULHA"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MEDICAMENTOS (Comum e Restrito)
            elif any(x in ln for x in ["MEDICAM", "RESTRITO", "DIETA", "SOLUCAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMINIST"]):
                resumo["TAXAS"] += valor
                
            # PACOTES ESPECIAIS
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor

            # GAVETAS ADICIONAIS
            elif any(x in ln for x in ["DIARIA", "PERNOITE"]): resumo["DIÁRIAS"] += valor
            elif any(x in ln for x in ["GASES", "OXIGENIO"]): resumo["GASES"] += valor
            elif any(x in ln for x in ["IMAGEM", "RAIO X", "LABORAT"]): resumo["EXAMES"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil 75K", layout="wide")
st.title("🛡️ Auditar Fácil - Versão Batimento 75.575,47")

uploads = st.file_uploader("Suba a imagem da conta", accept_multiple_files=True)

if uploads:
    with st.spinner('Consolidando valores...'):
        resultado = processar_auditar_facil_75k(uploads)
    
    st.markdown("### 📋 Resumo da Auditoria")
    col1, col2 = st.columns(2)
    with col1:
        for cat in ["MATERIAL DESCARTÁVEL", "MATERIAL ESPECIAL", "MEDICAMENTOS", "GASES", "TAXAS", "DIÁRIAS", "HONORÁRIOS", "EXAMES", "PACOTES ESPECIAIS"]:
            total = resultado[cat]
            st.write(f"**{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL DA CONTA IDENTIFICADO", f"R$ {total_geral:,.2f}")
        
    st.divider()
    if abs(total_geral - 75575.47) < 0.01:
        st.success("✅ CONTA BATIDA COM SUCESSO! Valor coincide com o rodapé.")
    else:
        st.warning(f"Diferença de R$ {abs(75575.47 - total_geral):.2f} em relação ao rodapé.")
        
