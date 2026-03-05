import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

st.set_page_config(page_title="AuditaFácil", layout="centered")

if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.markdown("<h1 style='color: #2e91e5;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar"):
        if len(senha) == 6:
            st.session_state.logado = True
            st.rerun()

def processar_hospital(arquivos):
    resumo = {"HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0, "GASES": 0.0, 
              "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0, "EXAMES": 0.0, "OPME": 0.0}
    
    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # FOCO TOTAL NA COLUNA DE VALORES: Cortamos os últimos 25% da largura da página
        # Isso remove os códigos TUSS e os rabiscos do meio da folha
        h, w = gray.shape
        coluna_valores = gray[:, int(w*0.75):] 
        
        # Limpeza agressiva: o que não for preto vira branco
        _, img_bin = cv2.threshold(coluna_valores, 150, 255, cv2.THRESH_BINARY)
        
        texto_valores = pytesseract.image_to_string(img_bin, config='--psm 6 digits')
        texto_completo = pytesseract.image_to_string(gray, lang='por', config='--psm 6')

        linhas_completas = texto_completo.split('\n')
        
        for linha in linhas_completas:
            linha = linha.upper()
            # Busca valores com vírgula
            matches = re.findall(r'\d+,\d{2}', linha)
            if matches:
                try:
                    val = float(matches[-1].replace(',', '.'))
                    if val > 15000.0: continue # Trava para não ler código como milhão
                    
                    # Classificação por palavras-chave
                    cat = "OUTROS"
                    if any(x in linha for x in ["SALA", "TAXA", "ALUG", "REGISTRO"]): cat = "TAXAS E ALUGUEIS"
                    elif any(x in linha for x in ["GAS", "OXIG", "AR COMP"]): cat = "GASES"
                    elif any(x in linha for x in ["MEDIC", "DIETA", "SOLU", "AMP", "SORO"]): cat = "MEDICAMENTOS"
                    elif any(x in linha for x in ["MATER", "FIO", "DESC", "AGUL", "LUV", "SERIN"]): cat = "MATERIAL"
                    elif any(x in linha for x in ["DIARIA", "APART", "ENFERM"]): cat = "DIARIA DE ENFERMARIA"
                    elif any(x in linha for x in ["OPME", "ORTE", "PROT", "ESPEC"]): cat = "OPME"
                    elif "HONOR" in linha: cat = "HONORARIOS"
                    
                    if cat in resumo: resumo[cat] += val
                except: continue
    return resumo

if not st.session_state.logado:
    tela_login()
else:
    st.title("📊 Auditoria Hospitalar")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    fotos = st.file_uploader("Fotos (HEIF/JPG)", type=['jpg', 'jpeg', 'png', 'heic'], accept_multiple_files=True)
    if fotos and st.button("Calcular Agora"):
        res = processar_hospital(fotos)
        st.subheader("Resumo")
        for c, v in res.items():
            if v > 0:
                st.write(f"**{c}:** R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        st.divider()
        st.metric("TOTAL GERAL", f"R$ {sum(res.values()):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
