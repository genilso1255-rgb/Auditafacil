import streamlit as st
import pandas as pd
from fpdf import FPDF

# --- CONFIGURAÇÃO DO DONO ---
CPF_ADM = "12345678900" 
SENHA_ADM = "123456"

st.set_page_config(page_title="AuditaFácil", layout="centered")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center; color: #1a73e8;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf_input = st.text_input("👤 CPF")
    senha_input = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar"):
        if cpf_input == CPF_ADM and senha_input == SENHA_ADM:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Incorreto")
else:
    st.title("📊 Painel de Auditoria")
    arquivo = st.file_uploader("Suba a conta", type=["jpg", "png"])
    if arquivo:
        dados = {
            'Categoria': ['EXAMES', 'MEDICAMENTOS', 'MATERIAIS', 'TAXAS', 'HONORÁRIOS'],
            'Conta Hospital': [410.25, 2529.32, 16153.85, 2779.21, 14612.63],
            'Valor Auditado': [410.25, 2529.32, 10923.64, 2779.21, 14612.63]
        }
        df = pd.DataFrame(dados)
        df['Diferença'] = df['Conta Hospital'] - df['Valor Auditado']
        st.table(df)
        t_dif = df['Diferença'].sum()
        st.markdown(f"<div style='background:#202124;color:white;padding:20px;border-radius:12px;'><h3>💰 TOTAL DA GLOSA: R$ {t_dif:,.2f}</h3></div>", unsafe_allow_html=True)
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()
      
