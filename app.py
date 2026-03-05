import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
import pandas as pd
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AuditaFacil - ADM", layout="centered")

# --- LÓGICA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.title("🏥 AuditaFacil - Acesso Restrito")
    cpf = st.text_input("CPF (Login)")
    senha = st.text_input("Senha (6 dígitos)", type="password")
    
    if st.button("Entrar"):
        if len(senha) == 6: # Aqui você pode colocar seu CPF e senha reais
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha deve ter 6 dígitos.")

def processar_imagem(img_pil):
    # Converter PIL para OpenCV
    img = np.array(img_pil)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # 1. Alinhamento e Limpeza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # 2. OCR (Leitura)
    texto = pytesseract.image_to_string(thresh, lang='por')
    
    # 3. Extração de Dados e Regras de Soma
    dados = []
    resumo = {"MEDICAMENTO": 0.0, "MATERIAL DESCARTAVEL": 0.0, "MATERIAL ESPECIAL": 0.0}
    
    # Regex para capturar Nome e Valor (Ex: R$ 1.250,50 ou 10,00)
    padrao = re.compile(r'([A-Za-z\s]{3,})\s+.*?([\d\.,]+)')
    
    for linha in texto.split('\n'):
        match = padrao.search(linha)
        if match:
            nome, valor_str = match.groups()
            nome = nome.strip().upper()
            try:
                # Limpa o valor para float
                val = float(valor_str.replace('.', '').replace(',', '.'))
                
                # Categorização solicitada
                cat = "OUTROS"
                if "DIETA" in nome: cat = "MEDICAMENTO"
                elif "FIO" in nome: cat = "MATERIAL DESCARTAVEL"
                elif any(x in nome for x in ["ORTESE", "PROTESE", "ESPECIAL", "OPME"]): cat = "MATERIAL ESPECIAL"
                
                if cat in resumo:
                    resumo[cat] += val
                dados.append({"Item": nome, "Valor": val, "Categoria": cat})
            except:
                continue
                
    return resumo, dados

# --- INTERFACE PRINCIPAL ---
if not st.session_state.logado:
    tela_login()
else:
    st.sidebar.write(f"Bem-vindo, Administrador")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.header("📸 Nova Auditoria")
    arquivo = st.file_uploader("Tire a foto da conta ou envie o arquivo", type=['jpg', 'png', 'jpeg'])

    if arquivo is not None:
        img_exibir = Image.open(arquivo)
        st.image(img_exibir, caption="Imagem Carregada", use_column_width=True)
        
        if st.button("Processar e Calcular"):
            with st.spinner('Limpando imagem e somando valores...'):
                resumo, detalhes = processar_imagem(img_exibir)
                
                st.subheader("📊 Resultado da Soma")
                df_resumo = pd.DataFrame([resumo])
                st.table(df_resumo)
                
                with st.expander("Ver itens detalhados"):
                    st.write(pd.DataFrame(detalhes))
                    
                st.success("Cálculo finalizado com sucesso!")

