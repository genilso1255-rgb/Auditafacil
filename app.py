import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil Pro - Inteligência TUSS", layout="wide")

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🌐 AuditaFácil - Nacional")
    if st.button("Entrar"): st.session_state.logado = True; st.rerun()
else:
    st.title("📄 Auditoria por Inteligência de Códigos e Palavras")
    arquivos = st.file_uploader("Upload de Contas", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por')
            
            for linha in texto.split('\n'):
                tuss_match = re.search(r'\b(\d{8,10})\b', linha)
                valores_na_linha = re.findall(r'(\d[\d\.,]*)', linha)

                if tuss_match and valores_na_linha:
                    codigo = tuss_match.group()
                    # Regra de centavos: pega o último número e força as 2 últimas casas
                    num_limpo = re.sub(r'[^\d]', '', valores_na_linha[-1])
                    if len(num_limpo) >= 3:
                        v = float(num_limpo[:-2] + '.' + num_limpo[-2:])
                        if v == float(codigo): continue # Ignora se o valor lido for o próprio código
                        
                        l_up = linha.upper()
                        
                        # --- CLASSIFICAÇÃO POR CÓDIGO (PREFERENCIAL) ---
                        if codigo.startswith(('1', '2', '3')): 
                            cat = "HONORÁRIOS / PROCEDIMENTOS"
                        elif codigo.startswith('0'): 
                            cat = "MAT. ESPECIAL (OPME)"
                        elif codigo.startswith(('9', '6')): 
                            cat = "MEDICAMENTOS / DIETAS"
                        # --- REFINAMENTO POR PALAVRA-CHAVE ---
                        elif any(x in l_up for x in ["PROTESE", "ORTESE", "STENT", "OPME", "PARAFUSO"]):
                            cat = "MAT. ESPECIAL (OPME)"
                        elif any(x in l_up for x in ["DIETA", "NUTRI", "ENTERAL", "LEITE"]):
                            cat = "MEDICAMENTOS / DIETAS"
                        elif any(x in l_up for x in ["DIARIA", "TAXA", "GAS", "SALA", "ENFERM"]):
                            cat = "DIÁRIAS E TAXAS"
                        else:
                            cat = "MATERIAIS / DESCARTÁVEIS"

                        dados_itens.append({"TUSS": codigo, "Categoria": cat, "Valor": v})

        if dados_itens:
            df = pd.DataFrame(dados_itens)
            st.write("### 📊 Resumo por Categoria")
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            st.dataframe(resumo.style.format({"Valor": "R$ {:.2f}"}))
            
            st.write("### 🔍 Detalhamento de Itens")
            st.table(df.style.format({"Valor": "{:.2f}"}))
            st.success(f"## Total Auditado: R$ {df['Valor'].sum():,.2f}")
            
