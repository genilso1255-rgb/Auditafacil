import streamlit as st
import pandas as pd
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re

# Configuração para o Streamlit Cloud encontrar o leitor de texto
# No Linux (Streamlit Cloud), o tesseract já vem instalado se configurado corretamente
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

st.set_page_config(page_title="AuditaFácil OCR", layout="centered")

# --- LOGIN (Mantendo o que você já usa) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🌐 AuditaFácil")
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar"):
        if cpf == "12345678900" and senha == "123456":
            st.session_state.autenticado = True
            st.rerun()
        else: st.error("Incorreto")
else:
    st.title("📊 Auditoria Real por Imagem")
    
    arquivo = st.file_uploader("Suba a foto nítida da conta", type=["jpg", "png", "jpeg"])
    
    if arquivo:
        # Converter imagem para formato que o computador entende
        img = Image.open(arquivo)
        st.image(img, caption="Imagem carregada", use_container_width=True)
        
        with st.spinner('Lendo dados da conta...'):
            # Transformar imagem em texto
            texto_extraido = pytesseract.image_to_string(img, lang='por')
            
            # Procurar por padrões de valores (ex: 1.234,56 ou 123,45)
            valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', texto_extraido)
            
            if valores:
                # Converter os textos encontrados em números reais (float)
                numeros = [float(v.replace('.', '').replace(',', '.')) for v in valores]
                
                st.subheader("✅ Valores encontrados na conta:")
                df_real = pd.DataFrame({
                    'Item Encontrado': [f"Valor {i+1}" for i in range(len(numeros))],
                    'Valor (R$)': numeros
                })
                
                st.table(df_real.style.format("R$ {:.2f}"))
                
                total_somado = sum(numeros)
                st.info(f"🧾 Soma total detectada na imagem: R$ {total_somado:,.2f}")
            else:
                st.warning("⚠️ Não consegui ler valores numéricos. A foto está nítida?")
                st.text("Texto que o robô conseguiu ler:")
                st.code(texto_extraido)

    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()
        
