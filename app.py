import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil Pro", layout="wide")

if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🌐 AuditaFácil")
    if st.button("Acessar"): st.session_state.logado = True; st.rerun()
else:
    st.title("📄 Auditoria Inteligente por Categorias")
    arquivos = st.file_uploader("Upload das Contas", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            # Aumentamos a precisão do OCR para tabelas
            texto = pytesseract.image_to_string(img, lang='por', config='--psm 6')
            
            for linha in texto.split('\n'):
                # Busca valores (ex: 1.234,56 ou 45,90)
                valores = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                
                if valores:
                    v_str = valores[-1]
                    v = float(v_str.replace('.', '').replace(',', '.'))
                    
                    # Filtro para ignorar datas ou números muito pequenos que não são itens da conta
                    if v < 1.0: continue
                    
                    l_up = linha.upper()
                    # --- GAVETAS DE CATEGORIAS REFINADAS ---
                    if any(x in l_up for x in ["CIRURG", "ANEST", "VISITA", "HM", "HONOR", "MEDICO", "PROCED"]):
                        cat = "HONORÁRIOS"
                    elif any(x in l_up for x in ["DIARIA", "TAXA", "GAS", "SALA", "PERNOITE", "ALUGUEL"]):
                        cat = "DIÁRIAS E TAXAS"
                    elif any(x in l_up for x in ["PROTESE", "ORTESE", "OPME", "STENT", "PARAFUSO", "PLACA", "ESPECIAL"]):
                        cat = "MAT. ESPECIAL (OPME)"
                    elif any(x in l_up for x in ["MEDIC", "FARM", "DIETA", "NUTRI", "ENTERAL", "SORO", "AMPOLA"]):
                        cat = "MEDICAMENTOS / DIETAS"
                    else:
                        cat = "MATERIAIS DESCARTÁVEIS"

                    # Pegamos o código TUSS se existir, senão marcamos como 'S/C'
                    tuss_match = re.search(r'\b(\d{7,10})\b', linha)
                    codigo = tuss_match.group() if tuss_match else "S/ Código"
                    
                    # Evita somar o código como valor
                    if v == float(codigo.replace('S/ Código', '0')): continue

                    dados_itens.append({"Código/TUSS": codigo, "Categoria": cat, "Valor": v})

        if dados_itens:
            df = pd.DataFrame(dados_itens).drop_duplicates()
            st.write("### 📊 Resumo por Categoria")
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            st.dataframe(resumo.style.format({"Valor": "R$ {:.2f}"}))
            
            st.write("### 🔍 Detalhamento dos Itens")
            st.table(df.style.format({"Valor": "{:.2f}"}))
            
            total_geral = df['Valor'].sum()
            st.success(f"## Total Auditado: R$ {total_geral:,.2f}")
            
