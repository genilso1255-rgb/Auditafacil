import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil - Precisão TUSS", layout="centered")

if 'logado' not in st.session_state: st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha (6 dígitos)", type="password")
    if st.button("Acessar Sistema"):
        if len(senha) == 6: st.session_state.logado = True; st.rerun()

# --- PAINEL DE AUDITORIA ---
else:
    st.markdown("<h1>📊 Painel de Auditoria</h1>", unsafe_allow_html=True)
    st.write("Suba a conta para leitura sequencial")
    arquivos = st.file_uploader("", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)
    
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if arquivos:
        itens_auditados = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por', config='--psm 6')
            
            for linha in texto.split('\n'):
                # 1. Busca o Código TUSS (8 a 10 dígitos)
                tuss = re.search(r'\b(\d{8,10})\b', linha)
                
                # 2. Busca o Valor no final da linha (ex: 1.234,56 ou 1234,56)
                valor_raw = re.findall(r'(\d{1,3}(?:\.?\d{3})*,\d{2})', linha)
                
                if valor_raw:
                    # Limpeza e formatação do valor (Real e Centavos)
                    v_str = valor_raw[-1]
                    # Garante que o ponto de milhar e a vírgula de centavos estejam corretos
                    v_limpo = v_str.replace('.', '').replace(',', '.')
                    v_final = float(v_limpo)
                    
                    # Filtro para evitar somar o total da nota ou lixo
                    if v_final > 13000 or v_final < 0.10: continue

                    # 3. Identifica a Descrição (o que está na frente do código)
                    codigo_str = tuss.group() if tuss else ""
                    descricao = linha.replace(codigo_str, "").replace(v_str, "").strip()
                    desc_up = descricao.upper()

                    # 4. Classificação por "O que está escrito" (Ex: Diárias, Honorários)
                    if any(x in desc_up for x in ["DIARIA", "APARTAMENTO", "ENFERMARIA", "SALA"]):
                        cat = "DIÁRIAS E TAXAS"
                    elif any(x in desc_up for x in ["HONOR", "VISITA", "HM"]):
                        cat = "HONORÁRIOS"
                    elif any(x in desc_up for x in ["DIETA", "NUTRI", "ENTERAL"]):
                        cat = "DIETAS"
                    elif any(x in desc_up for x in ["MEDIC", "SORO", "FARM"]):
                        cat = "MEDICAMENTOS"
                    elif any(x in desc_up for x in ["PROTESE", "ORTESE", "OPME", "FIO"]):
                        cat = "MAT. ESPECIAL (OPME)"
                    else:
                        cat = "MATERIAIS DESCARTÁVEIS"

                    itens_auditados.append({
                        "TUSS": codigo_str if codigo_str else "S/ Código",
                        "Descrição": descricao[:40],
                        "Categoria": cat,
                        "Valor": v_final
                    })

        if itens_auditados:
            df = pd.DataFrame(itens_auditados).drop_duplicates()
            
            # --- TABELA DE RESUMO POR CATEGORIA ---
            st.markdown("### 📈 Resumo de Auditoria")
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            # Formata a exibição com R$ e ponto/vírgula
            st.table(resumo.style.format({"Valor": "R$ {:,.2f}"}))
            
            total = df['Valor'].sum()
            st.success(f"## Total Auditado: R$ {total:,.2f}")
            
            # --- DETALHAMENTO UNIFICADO ---
            st.markdown("### 🔍 Detalhamento (TUSS + Descrição + Valor)")
            st.dataframe(df.style.format({"Valor": "{:.2f}"}), use_container_width=True)
            
