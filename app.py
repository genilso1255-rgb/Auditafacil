import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil Pro", layout="centered")

if 'logado' not in st.session_state: st.session_state.logado = False

# --- ACESSO SEGURO ---
if not st.session_state.logado:
    st.markdown("<h1>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF (apenas números)")
    senha = st.text_input("🔑 Senha (6 dígitos)", type="password")
    if st.button("Acessar Sistema"):
        if len(senha) == 6 and cpf != "":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

# --- PAINEL DE AUDITORIA ---
else:
    st.markdown("<h1>📊 Painel de Auditoria</h1>", unsafe_allow_html=True)
    st.write("Suba as imagens para processamento sequencial")
    arquivos = st.file_uploader("", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)
    
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if arquivos:
        dados_finais = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por', config='--psm 6')
            
            for linha in texto.split('\n'):
                # 1. Identifica o Código TUSS (8 a 10 dígitos)
                tuss_match = re.search(r'\b(\d{8,10})\b', linha)
                # 2. Identifica o Valor no final (trata real e centavo)
                valor_match = re.findall(r'(\d{1,3}(?:\.?\d{3})*,\d{2})', linha)
                
                if valor_match:
                    v_str = valor_match[-1]
                    v_float = float(v_str.replace('.', '').replace(',', '.'))
                    
                    # Filtro para ignorar o total da nota e ruídos menores que 1 real
                    if v_float >= 13000 or v_float < 0.50: continue

                    codigo = tuss_match.group() if tuss_match else "S/ Código"
                    
                    # 3. Extrai a DESCRIÇÃO (o que está entre o código e o valor)
                    # Remove o código e o valor da linha para sobrar só o texto
                    descricao = linha.replace(codigo, "").replace(v_str, "").strip()
                    desc_up = descricao.upper()

                    # 4. Classificação por texto (Ex: Diárias, Honorários, etc.)
                    if any(x in desc_up for x in ["DIARIA", "APART", "ENFERM", "SALA", "GAS"]):
                        cat = "DIÁRIAS E TAXAS"
                    elif any(x in desc_up for x in ["HONOR", "VISITA", "HM", "PROCED"]):
                        cat = "HONORÁRIOS"
                    elif any(x in desc_up for x in ["DIETA", "NUTRI", "ENTERAL", "LEITE"]):
                        cat = "DIETAS"
                    elif any(x in desc_up for x in ["MEDIC", "SORO", "FARM", "AMPOLA"]):
                        cat = "MEDICAMENTOS"
                    elif any(x in desc_up for x in ["PROTESE", "ORTESE", "OPME", "STENT", "FIO"]):
                        cat = "MAT. ESPECIAL (OPME)"
                    else:
                        cat = "MATERIAIS DESCARTÁVEIS"

                    dados_finais.append({
                        "Código": codigo,
                        "Descrição": descricao[:40],
                        "Categoria": cat,
                        "Valor": v_float
                    })

        if dados_finais:
            df = pd.DataFrame(dados_finais).drop_duplicates()
            
            st.markdown("---")
            st.subheader("📈 Resumo por Categoria")
            # Agrupa e soma cada categoria para bater com o papel
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            st.table(resumo.style.format({"Valor": "R$ {:,.2f}"}))
            
            total = df['Valor'].sum()
            st.success(f"### Total Auditado: R$ {total:,.2f}")
            
            st.write("### 🔍 Detalhamento Sequencial (Código > Descrição > Valor)")
            st.dataframe(df.style.format({"Valor": "{:.2f}"}), use_container_width=True)
            
