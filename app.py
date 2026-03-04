import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil - Precisão Total", layout="wide")

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🌐 AuditaFácil")
    if st.button("Acessar"): st.session_state.logado = True; st.rerun()
else:
    st.title("📄 Auditoria de Alta Precisão (Filtro Anti-Código)")
    arquivos = st.file_uploader("Upload das Contas", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por')
            
            for linha in texto.split('\n'):
                tuss_match = re.search(r'\b(\d{7,10})\b', linha)
                # Busca valores apenas com vírgula ou ponto decimal explícito no fim da linha
                valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', linha)

                if tuss_match and valores:
                    codigo = tuss_match.group()
                    # Pegamos sempre o último valor da linha (onde fica o preço total do item)
                    v_str = valores[-1]
                    v = float(v_str.replace('.', '').replace(',', '.'))
                    
                    # TRAVA DE SEGURANÇA: Se o valor for > 80% igual ao código, ignore (é erro de leitura)
                    if v > 1000 and codigo[:5] in str(int(v)): continue
                    if v == float(codigo): continue

                    l_up = linha.upper()
                    if codigo.startswith(('1', '2', '3')): cat = "HONORÁRIOS"
                    elif any(x in l_up for x in ["PROTESE", "ORTESE", "OPME", "STENT", "PARAFUSO", "PLACA"]): cat = "MAT. ESPECIAL (OPME)"
                    elif any(x in l_up for x in ["DIETA", "NUTRI", "ENTERAL", "MEDIC", "SORO"]): cat = "MEDICAMENTOS / DIETAS"
                    elif any(x in l_up for x in ["DIARIA", "TAXA", "GAS", "SALA"]): cat = "DIÁRIAS E TAXAS"
                    else: cat = "MATERIAIS / DESCARTÁVEIS"

                    dados_itens.append({"TUSS": codigo, "Categoria": cat, "Valor": v})

        if dados_itens:
            df = pd.DataFrame(dados_itens).drop_duplicates()
            st.write("### 📊 Resumo Consolidado")
            st.dataframe(df.groupby('Categoria')['Valor'].sum().reset_index().style.format({"Valor": "R$ {:.2f}"}))
            st.write("### 🔍 Itens Auditados")
            st.table(df.style.format({"Valor": "{:.2f}"}))
            st.success(f"## Total Real Identificado: R$ {df['Valor'].sum():,.2f}")
            
