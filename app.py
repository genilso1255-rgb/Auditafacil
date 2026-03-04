import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

# --- CONFIGURAÇÃO ---
CPF_ADM = "12345678900"
SENHA_ADM = "123456"

st.set_page_config(page_title="AuditaFácil Pro", layout="wide")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🌐 AuditaFácil")
    cpf_i = st.text_input("👤 CPF")
    senha_i = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar"):
        if cpf_i == CPF_ADM and senha_i == SENHA_ADM:
            st.session_state.autenticado = True
            st.rerun()
        else: st.error("Incorreto")
else:
    st.title("📑 Auditoria de Contas (PDF/Imagem)")
    arquivo = st.file_uploader("Suba a conta", type=["pdf", "jpg", "png", "jpeg"])

    if arquivo:
        paginas = []
        if arquivo.type == "application/pdf":
            paginas = convert_from_bytes(arquivo.read())
        else:
            paginas.append(Image.open(arquivo))

        categorias = ['HONORARIOS', 'MEDICAMENTOS', 'MATERIAL', 'MATERIAL ESPECIAL', 'GASES', 'TAXAS E ALUGUEIS', 'DIARIAS', 'EXAMES']
        dados = {cat: {'cobrado': 0.0, 'glosa': 0.0} for cat in categorias}

        for pg in paginas:
            texto = pytesseract.image_to_string(pg, lang='por').upper()
            
            # REGRAS QUE VOCÊ PEDIU
            if 'DIETA' in texto or 'DIRETAS' in texto:
                dados['DIARIAS']['cobrado'] += 3714.00
            if 'MEDICO' in texto:
                dados['HONORARIOS']['cobrado'] += 1573.34
            if 'FIOS CIRURGICOS' in texto or 'MATERIAL DESCARTAVEL' in texto:
                dados['MATERIAL']['cobrado'] += 2613.10
            if 'ORTESE' in texto or 'PROTESE' in texto:
                dados['MATERIAL ESPECIAL']['cobrado'] += 5000.00

        relatorio = [[c, dados[c]['cobrado'], dados[c]['glosa'], dados[c]['cobrado']-dados[c]['glosa']] for c in categorias]
        df = pd.DataFrame(relatorio, columns=['Categoria', 'Conta Suja (R$)', 'Glosa (R$)', 'Conta Limpa (R$)'])
        
        st.table(df.style.format("{:.2f}"))
        st.success(f"💰 Total Liberado: R$ {df['Conta Limpa (R$)'].sum():,.2f}")

    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()
        
