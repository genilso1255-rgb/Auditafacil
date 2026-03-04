import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil Nacional", layout="wide")

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🌐 AuditaFácil - Nacional")
    if st.button("Entrar"): st.session_state.logado = True; st.rerun()
else:
    st.title("📄 Auditoria Inteligente (Padrão TUSS Nacional)")
    arquivos = st.file_uploader("Upload de Contas (Fotos ou PDF)", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            # Processa PDF ou Imagem
            if arq.type == "application/pdf":
                paginas = pdf2image.convert_from_bytes(arq.read())
            else:
                paginas = [Image.open(arq)]
            
            for img in paginas:
                texto = pytesseract.image_to_string(img, lang='por')
                for linha in texto.split('\n'):
                    # Busca Código TUSS (8 a 10 dígitos) e Valor Monetário
                    tuss = re.search(r'\b\d{8,10}\b', linha)
                    valor = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', linha)

                    if tuss and valor:
                        v = float(valor[-1].replace('.', '').replace(',', '.'))
                        l_up = linha.upper()
                        
                        # --- GAVETAS DE CLASSIFICAÇÃO NACIONAL ---
                        if any(x in l_up for x in ["CIRURG", "ANEST", "VISITA", "HM", "HONOR", "PROCED"]): 
                            cat = "HONORÁRIOS / PROCEDIMENTOS"
                        elif any(x in l_up for x in ["PROTESE", "ORTESE", "OPME", "ESPECIAL", "STENT", "MARCAPASSO"]): 
                            cat = "MAT. ESPECIAL (OPME)"
                        elif any(x in l_up for x in ["MEDIC", "FARM", "SOLUCAO", "AMP", "DIETA", "NUTRI", "ENTERAL"]): 
                            cat = "MEDICAMENTOS / DIETAS"
                        elif any(x in l_up for x in ["DIARIA", "TAXA", "GAS", "OXIG", "ENFERM"]): 
                            cat = "DIÁRIAS E TAXAS"
                        else: 
                            cat = "MATERIAIS / DESCARTÁVEIS"

                        dados_itens.append({"TUSS": tuss.group(), "Categoria": cat, "Valor": v})

        if dados_itens:
            df = pd.DataFrame(dados_itens)
            st.write("### 📊 Resumo por Categoria")
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            st.dataframe(resumo.style.format({"Valor": "R$ {:.2f}"}))
            
            st.write("### 🔍 Detalhamento de Itens")
            st.table(df)
            
            total_geral = df['Valor'].sum()
            st.success(f"## Total Auditado: R$ {total_geral:,.2f}")
            
