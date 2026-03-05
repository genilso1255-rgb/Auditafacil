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
    # Categorias oficiais do seu exemplo
    resumo = {"HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0, "GASES": 0.0, 
              "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0, "EXAMES": 0.0, "OPME": 0.0}
    
    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        
        # TRANSFORMAÇÃO PARA CONTA SUJA: Aumenta o contraste e remove sombras
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 15)
        
        # Configuração do Tesseract para focar em tabelas (psm 6)
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            linha = linha.upper().strip()
            # Pega números que parecem valores (ex: 1.434,79 ou 89,44)
            nums = re.findall(r'(\d+[\.,]\d{2})', linha)
            
            if nums:
                try:
                    # O valor cobrado na sua conta é sempre o último da direita (VI Total)
                    valor_str = nums[-1]
                    val = float(valor_str.replace('.', '').replace(',', '.'))
                    
                    # Ignora códigos TUSS e erros de milhões
                    if val > 15000.0 or val < 0.05: continue 
                    
                    # Classificação por palavras-chave reais das suas fotos
                    cat = "OUTROS"
                    if any(x in linha for x in ["SALA", "TAXA", "ALUG", "REGISTRO", "PORT"]): cat = "TAXAS E ALUGUEIS"
                    elif any(x in linha for x in ["GAS", "OXIG", "AR COMP", "VUL"]): cat = "GASES"
                    elif any(x in linha for x in ["MEDIC", "DIETA", "SOLU", "AMP", "VUL"]): cat = "MEDICAMENTOS"
                    elif any(x in linha for x in ["MATER", "FIO", "DESC", "AGUL", "LUV", "SERINGA", "CURATIVO"]): cat = "MATERIAL"
                    elif any(x in linha for x in ["DIARIA", "APART", "ENFERM", "PACOTE"]): cat = "DIARIA DE ENFERMARIA"
                    elif any(x in linha for x in ["OPME", "ORTESE", "PROTESE", "ESPEC", "SINTESE"]): cat = "OPME"
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

    st.write("---")
    fotos = st.file_uploader("Selecione as fotos (HEIF/JPG/PNG)", type=['jpg', 'jpeg', 'png', 'heic'], accept_multiple_files=True)
    
    if fotos:
        if st.button("Calcular Total da Conta"):
            with st.spinner("Limpando imagem e somando categorias..."):
                res = processar_hospital(fotos)
                
                st.subheader("Resumo por Categoria")
                for c, v in res.items():
                    if v > 0:
                        # Formatação de moeda brasileira
                        valor_fmt = f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        st.write(f"**{c}:** {valor_fmt}")
                
                total = sum(res.values())
                st.divider()
                st.metric("VALOR TOTAL COBRADO", f"R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                
