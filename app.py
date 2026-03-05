import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO E LAYOUT ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

# CSS para manter o padrão escuro das fotos
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2127; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF (apenas números)")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar Sistema"):
        if cpf == "12345678901" and senha == "teste":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Dados de teste: 12345678901 / teste")

# --- INTERFACE INTERNA ---
else:
    st.markdown("# 📑 Auditoria de Contas Hospitalares")
    
    st.info("Agora você pode selecionar vários arquivos (PDF ou Imagem) segurando a tecla Ctrl ou pressionando cada um no celular.")

    arquivos = st.file_uploader("Selecione as fotos ou PDFs das contas", 
                               type=["pdf", "jpg", "jpeg", "png"], 
                               accept_multiple_files=True)

    if arquivos:
        st.success(f"{len(arquivos)} arquivo(s) carregado(s). Iniciando leitura...")
        
        # --- TABELA DE ITENS DA CONTA (O que você pediu) ---
        st.subheader("ITENS DA CONTA")
        
        # Simulando os dados extraídos pelo seu OCR/TUSS
        dados_exemplo = {
            'Descrição do Item:': ['HONORARIOS', 'MEDICAMENTOS', 'MATERIAL', 'GASES', 'TAXAS E ALUGUEIS', 'DIARIA DE ENFERMARIA', 'EXAMES'],
            'Quantidade:': [1, 1, 1, 1, 1, 2, 1],
            'Cobrado:': [1573.34, 419.50, 2613.10, 9.78, 1959.43, 3714.00, 23.30],
            'Glosado:': [0.00, 17.40, 416.80, 0.00, 425.80, 0.00, 0.00]
        }
        
        df = pd.DataFrame(dados_exemplo)
        df['Liberado:'] = df['Cobrado:'] - df['Glosado:']
        
        # Formatação para moeda R$
        df_style = df.style.format({
            'Cobrado:': 'R$ {:.2f}', 
            'Glosado:': 'R$ {:.2f}', 
            'Liberado:': 'R$ {:.2f}'
        })
        
        st.table(df_style)

        # --- RESUMO TOTAL (Logo em seguida) ---
        total_cobrado = df['Cobrado:'].sum()
        total_glosado = df['Glosado:'].sum()
        total_liberado = df['Liberado:'].sum()
        perc_glosa = (total_glosado / total_cobrado) * 100

        # Layout de colunas para o rodapé financeiro
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Cobrado", f"R$ {total_cobrado:,.2f}")
        c2.metric("Total Glosado", f"R$ {total_glosado:,.2f}")
        c3.metric("% Glosa", f"{perc_glosa:.1f}%")
        c4.metric("Total Liberado", f"R$ {total_liberado:,.2f}")

    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()
        
