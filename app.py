import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
import pandas as pd
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

# --- ESTADO DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN (ESTILO ORIGINAL) ---
def tela_login_original():
    # Estilização para aproximar do visual da sua foto
    st.markdown("<h1 style='color: #2e91e5; display: flex; align-items: center;'><span style='font-size: 40px; margin-right: 10px;'>🌐</span> AuditaFácil</h1>", unsafe_allow_html=True)
    
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha", type="password")
    
    # Botão "Acessar" alinhado à esquerda como na imagem
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Acessar"):
            if len(senha) == 6:
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Senha de 6 dígitos obrigatória.")

# --- MOTOR DE AUDITORIA ---
def realizar_auditoria(lista_fotos):
    resumo = {
        "HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0,
        "GASES": 0.0, "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0,
        "EXAMES": 0.0, "MATERIAL ESPECIAL (OPME)": 0.0
    }
    itens_processados = []

    for arq in lista_fotos:
        img_pil = Image.open(arq)
        img = np.array(img_pil.convert('RGB'))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Alinhamento e limpeza para "Contas Sujas"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        texto = pytesseract.image_to_string(thresh, lang='por')

        # Regex para Código TUSS e Valor Cobrado
        padrao = re.compile(r'(\d{8,10})?\s*([A-Z\s]{3,})\s+.*?([\d\.,]+)$')

        for linha in texto.split('\n'):
            match = padrao.search(linha.strip().upper())
            if match:
                codigo, nome, valor_str = match.groups()
                try:
                    val = float(valor_str.replace('.', '').replace(',', '.'))
                    
                    # Regras de Agrupamento
                    cat = "OUTROS"
                    if "HONOR" in nome: cat = "HONORARIOS"
                    elif "MEDIC" in nome or "DIETA" in nome: cat = "MEDICAMENTOS"
                    elif "FIO" in nome or "DESCART" in nome or "MATERIAL" in nome: cat = "MATERIAL"
                    elif "GAS" in nome: cat = "GASES"
                    elif "TAXA" in nome or "ALUGUE" in nome: cat = "TAXAS E ALUGUEIS"
                    elif "DIARIA" in nome or "ENFERM" in nome: cat = "DIARIA DE ENFERMARIA"
                    elif "EXAME" in nome: cat = "EXAMES"
                    elif any(x in nome for x in ["ORTESE", "PROTESE", "OPME", "ESPECIAL"]): 
                        cat = "MATERIAL ESPECIAL (OPME)"

                    if cat in resumo: resumo[cat] += val
                    itens_processados.append({"Cód": codigo, "Item": nome, "Cat": cat, "R$": val})
                except: continue
    return resumo, itens_processados

# --- TELA PRINCIPAL (ADMINISTRADOR) ---
if not st.session_state.logado:
    tela_login_original()
else:
    st.title("📊 Painel de Auditoria")
    st.write("Auditor Administrativo")
    
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.divider()

    # Suporte para múltiplas fotos (Limpa e Suja) em 3:4/HEIF
    arquivos = st.file_uploader("Upload de Contas", type=['jpg', 'jpeg', 'png', 'heic'], accept_multiple_files=True)

    if arquivos:
        if st.button("Processar Contas"):
            res, detalhe = realizar_auditoria(arquivos)
            
            st.subheader("Resumo por Categoria")
            # Tabela igual à do Hospital Brasília
            df_resumo = pd.DataFrame(list(res.items()), columns=['Descrição do Item', 'Valor Cobrado'])
            st.table(df_resumo[df_resumo['Valor Cobrado'] > 0])
            
            total_conta = sum(res.values())
            st.metric("Total Cobrado", f"R$ {total_conta:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            with st.expander("Ver lista de itens detalhados"):
                st.dataframe(pd.DataFrame(detalhe))
                
