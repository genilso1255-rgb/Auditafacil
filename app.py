import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="Painel de Auditoria Profissional", layout="wide")

# --- ESTADOS E LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'supervisor' not in st.session_state: st.session_state.supervisor = False

if not st.session_state.logado:
    st.title("🌐 Acesso")
    cpf = st.text_input("CPF")
    senha = st.text_input("Senha (6 dígitos)", type="password")
    if st.button("Entrar"):
        if len(senha) == 6 and cpf != "":
            st.session_state.logado = True
            st.rerun()

elif not st.session_state.supervisor:
    st.title("🛡️ Supervisor")
    if st.button("🔓 Liberar Login do Supervisor"):
        st.session_state.supervisor = True
        st.rerun()

# --- PAINEL DE AUDITORIA ---
else:
    st.title("📊 Painel de Auditoria")
    col_up, col_s = st.columns([4, 1])
    with col_up:
        st.write("Suba a conta")
        arquivos = st.file_uploader("", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)
    with col_s:
        if st.button("Sair"):
            st.session_state.logado = False
            st.session_state.supervisor = False
            st.rerun()

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por', config='--psm 6')
            
            for linha in texto.split('\n'):
                # 1. Busca Código TUSS (8 a 10 dígitos)
                tuss_match = re.search(r'\b(\d{8,10})\b', linha)
                # 2. Busca Valor no final (ex: 13.290,70)
                valor_match = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                
                if valor_match:
                    v = float(valor_match[-1].replace('.', '').replace(',', '.'))
                    if v < 1.00 or v > 15000: continue # Filtro para não ler lixo ou totais duplicados
                    
                    codigo = tuss_match.group() if tuss_match else "S/ Código"
                    
                    # 3. Captura a Descrição (o que está entre o código e o valor)
                    descricao = linha.replace(codigo, "").replace(valor_match[-1], "").strip()
                    desc_up = descricao.upper()

                    # 4. Classificação por Descrição e Código
                    if any(x in desc_up for x in ["HONOR", "CIRURG", "VISITA", "HM"]): cat = "HONORÁRIOS"
                    elif any(x in desc_up for x in ["DIETA", "NUTRI", "ENTERAL", "LEITE"]): cat = "DIETAS"
                    elif any(x in desc_up for x in ["MEDIC", "SORO", "FARM", "AMPOLA"]): cat = "MEDICAMENTOS"
                    elif any(x in desc_up for x in ["PROTESE", "ORTESE", "OPME", "STENT"]): cat = "MAT. ESPECIAL (OPME)"
                    elif any(x in desc_up for x in ["DIARIA", "TAXA", "SALA", "GAS"]): cat = "DIÁRIAS E TAXAS"
                    else: cat = "MATERIAIS DESCARTÁVEIS"

                    dados_itens.append({
                        "Código": codigo,
                        "Descrição": descricao[:30], # Limita tamanho para caber na tabela
                        "Categoria": cat,
                        "Valor": v
                    })

        if dados_itens:
            # Unifica por tabela e remove duplicados exatos
            df = pd.DataFrame(dados_itens).drop_duplicates()
            
            st.markdown("---")
            st.subheader("📈 Resumo Consolidado")
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            st.table(resumo.style.format({"Valor": "R$ {:.2f}"}))
            
            st.write("### 🔍 Itens Identificados na Tabela")
            st.dataframe(df, use_container_width=True) # Tabela unificada
            
            total = df['Valor'].sum()
            st.success(f"### Total Auditado: R$ {total:,.2f}")
            
