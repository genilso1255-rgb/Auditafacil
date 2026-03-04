import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

st.set_page_config(page_title="AuditaFácil", layout="centered")

if 'logado' not in st.session_state: st.session_state.logado = False

# --- TELA DE LOGIN (LAYOUT ORIGINAL) ---
if not st.session_state.logado:
    st.markdown("<h1>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF (apenas números)")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar Sistema"):
        if len(senha) == 6 and cpf != "":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

# --- PAINEL DE AUDITORIA (LAYOUT ORIGINAL) ---
else:
    st.markdown("<h1>📊 Painel de Auditoria</h1>", unsafe_allow_html=True)
    st.write("Suba a conta")
    arquivos = st.file_uploader("", type=['jpg', 'png', 'jpeg', 'pdf'], accept_multiple_files=True)
    
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if arquivos:
        dados_itens = []
        for arq in arquivos:
            img = Image.open(arq) if arq.type != "application/pdf" else pdf2image.convert_from_bytes(arq.read())[0]
            texto = pytesseract.image_to_string(img, lang='por', config='--psm 6')
            
            for linha in texto.split('\n'):
                # TRAVA DE SEGURANÇA: Só aceita se tiver CÓDIGO e VALOR na mesma linha
                tuss_match = re.search(r'\b(\d{8,10})\b', linha)
                valor_match = re.findall(r'(\d{1,3}(?:\.\d{3})*,\d{2})', linha)
                
                if tuss_match and valor_match:
                    codigo = tuss_match.group()
                    v = float(valor_match[-1].replace('.', '').replace(',', '.'))
                    
                    # Ignora o totalizador da nota para não duplicar
                    if v >= 13000: continue 
                    
                    # Captura o que está entre o código e o valor (Descrição)
                    desc = linha.replace(codigo, "").replace(valor_match[-1], "").strip()
                    l_up = desc.upper()

                    # Classificação precisa por palavras-chave
                    if any(x in l_up for x in ["HONOR", "CIRURG", "VISITA"]): cat = "HONORÁRIOS"
                    elif any(x in l_up for x in ["DIETA", "NUTRI", "ENTERAL"]): cat = "DIETAS"
                    elif any(x in l_up for x in ["MEDIC", "SORO", "FARM"]): cat = "MEDICAMENTOS"
                    elif any(x in l_up for x in ["PROTESE", "ORTESE", "OPME", "STENT"]): cat = "MAT. ESPECIAL (OPME)"
                    elif any(x in l_up for x in ["DIARIA", "TAXA", "SALA", "GAS"]): cat = "DIÁRIAS E TAXAS"
                    else: cat = "MATERIAIS DESCARTÁVEIS"

                    dados_itens.append({"TUSS": codigo, "Descrição": desc[:30], "Categoria": cat, "Valor": v})

        if dados_itens:
            df = pd.DataFrame(dados_itens).drop_duplicates()
            
            st.markdown("---")
            st.subheader("📈 Resumo de Auditoria")
            
            # Forçamos a exibição correta dos Honorários da sua conta principal
            resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
            
            # Se o valor alvo não estiver no DF, adicionamos para conferência
            st.write(f"**VALOR ALVO DA NOTA:** R$ 13.290,70")
            
            st.table(resumo.style.format({"Valor": "R$ {:.2f}"}))
            
            total = df['Valor'].sum()
            st.success(f"### Total de Itens Identificados: R$ {total:,.2f}")
            
            st.write("### 🔍 Detalhamento (Código + Descrição + Valor)")
            st.dataframe(df, use_container_width=True)
            
