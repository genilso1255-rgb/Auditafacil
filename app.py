import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_universal(texto_linha):
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_imagem_auditoria(arquivo):
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0, "MATERIAL ESPECIAL": 0.0,
        "MEDICAMENTOS": 0.0, "GASES": 0.0, "TAXAS": 0.0,
        "DIÁRIAS": 0.0, "HONORÁRIOS": 0.0, "EXAMES": 0.0, "PACOTES ESPECIAIS": 0.0
    }
    
    img_pil = Image.open(arquivo).convert('RGB')
    img_np = np.array(img_pil)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    img_final = cv2.threshold(gray, 175, 255, cv2.THRESH_BINARY)[1]
    texto = pytesseract.image_to_string(img_final, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.upper().strip()
        if not ln or any(s in ln for s in ["TOTAL DO SETOR", "VALOR TOTAL DA GUIA"]): continue
        
        valor = extrair_valor_universal(ln)
        if valor <= 0: continue

        # --- MESMA LÓGICA QUE DEU CERTO NOS 75K ---
        if "PACOTES ESPECIAIS" in ln: resumo["PACOTES ESPECIAIS"] += valor
        elif any(x in ln for x in ["NARIZ", "CABECA", "PESCOCO", "OLHOS", "SEIOS", "NERVOSO", "SISTEMA", "MUSCULO", "HONORARIO"]): resumo["HONORÁRIOS"] += valor
        elif any(x in ln for x in ["MATERIAIS", "HOSPITALARES", "FIOS", "DESCARTAVEL", "AGULHA"]): resumo["MATERIAL DESCARTÁVEL"] += valor
        elif any(x in ln for x in ["MEDICAM", "RESTRITO", "DIETA", "SOLUCAO", "SORO"]): resumo["MEDICAMENTOS"] += valor
        elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]): resumo["MATERIAL ESPECIAL"] += valor
        elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMINIST"]): resumo["TAXAS"] += valor
        elif any(x in ln for x in ["DIARIA", "PERNOITE"]): resumo["DIÁRIAS"] += valor
        elif any(x in ln for x in ["GASES", "OXIGENIO"]): resumo["GASES"] += valor
        elif any(x in ln for x in ["IMAGEM", "RAIO X"]): resumo["EXAMES"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Comparador", layout="wide")
st.title("🛡️ Auditar Fácil - Confronto Suja vs. Limpa")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📑 1. Conta Hospitalar (SUJA)")
    file_suja = st.file_uploader("Upload da Conta Bruta", type=["jpg", "png", "heic"], key="suja")

with col2:
    st.subheader("✨ 2. Relatório de Auditoria (LIMPA)")
    file_limpa = st.file_uploader("Upload da Conta Auditada", type=["jpg", "png", "heic"], key="limpa")

if file_suja and file_limpa:
    with st.spinner('Realizando o batimento das contas...'):
        dados_suja = processar_imagem_auditoria(file_suja)
        dados_limpa = processar_imagem_auditoria(file_limpa)
        
    st.divider()
    st.header("📊 Diferença Encontrada (Glosas por Categoria)")

    # Montando a Tabela Comparativa
    tabela_final = []
    total_suja = 0
    total_limpa = 0

    for cat in dados_suja.keys():
        v_suja = dados_suja[cat]
        v_limpa = dados_limpa[cat]
        glosa = v_suja - v_limpa
        
        total_suja += v_suja
        total_limpa += v_limpa
        
        tabela_final.append({
            "Categoria": cat,
            "Conta Suja (R$)": f"{v_suja:,.2f}",
            "Conta Limpa (R$)": f"{v_limpa:,.2f}",
            "Diferença / Glosa (R$)": f"{glosa:,.2f}"
        })

    st.table(tabela_final)

    # Métricas de Fechamento
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL CONTA SUJA", f"R$ {total_suja:,.2f}")
    m2.metric("TOTAL CONTA LIMPA", f"R$ {total_limpa:,.2f}")
    m3.metric("VALOR TOTAL GLOSADO", f"R$ {(total_suja - total_limpa):,.2f}", delta=f"{(total_suja - total_limpa):,.2f}", delta_color="inverse")

    if total_suja > 0:
        percentual = ((total_suja - total_limpa) / total_suja) * 100
        st.info(f"O índice de glosa desta conta foi de **{percentual:.2f}%**")
        
