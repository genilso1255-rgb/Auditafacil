import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil - Oficial", layout="wide")

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🌐 AuditaFácil")
    if st.button("Acessar"): st.session_state.logado = True; st.rerun()
else:
    st.title("📄 Auditoria Inteligente (Foco: R$ 13.290,70)")
    arquivos = st.file_uploader("Subir Contas", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            # Processamento de imagem
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por', config='--psm 6')
            
            for linha in texto.split('\n'):
                # Busca valores com vírgula (ex: 13.290,70 ou 45,00)
                valor_match = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                
                if valor_match:
                    v_str = valor_match[-1]
                    v = float(v_str.replace('.', '').replace(',', '.'))
                    
                    # Filtro para ignorar lixo: valores menores que 0.50 ou muito grandes
                    if v < 0.50 or v > 20000: continue
                    
                    l_up = linha.upper()
                    # --- CATEGORIZAÇÃO POR PALAVRA E CÓDIGO ---
                    if any(x in l_up for x in ["HONOR", "CIRURG", "ANEST", "VISITA", "PROCED"]): cat = "HONORÁRIOS"
                    elif any(x in l_up for x in ["DIETA", "NUTRI", "ENTERAL", "LEITE", "FORMULA"]): cat = "DIETAS"
                    elif any(x in l_up for x in ["MEDIC", "SORO", "FARM", "AMPOLA"]): cat = "MEDICAMENTOS"
                    elif any(x in l_up for x in ["PROTESE", "ORTESE", "OPME", "STENT", "PARAFUSO"]): cat = "MAT. ESPECIAL (OPME)"
                    elif any(x in l_up for x in ["DIARIA", "TAXA", "SALA", "GAS"]): cat = "DIÁRIAS E TAXAS"
                    else: cat = "MATERIAIS DESCARTÁVEIS"

                    # Busca Código TUSS (8 a 10 dígitos)
                    tuss_match = re.search(r'\b(\d{8,10})\b', linha)
                    codigo = tuss_match.group() if tuss_match else "S/ Código"

                    dados_itens.append({"Código": codigo, "Categoria": cat, "Valor": v})

        if dados_itens:
            df = pd.DataFrame(dados_itens).drop_duplicates()
            st.write("### 📊 Resumo de Auditoria")
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            st.dataframe(resumo.style.format({"Valor": "R$ {:.2f}"}))
            
            st.write("### 🔍 Itens Identificados")
            st.table(df.style.format({"Valor": "{:.2f}"}))
            
            total = df['Valor'].sum()
            st.success(f"## Total Auditado: R$ {total:,.2f}")
            
