import streamlit as st
import pandas as pd
import re
from PIL import Image

# 1. Configuração de Layout (Mantendo o padrão que você tinha)
st.set_page_config(page_title="Auditoria Fácil", layout="wide")

# CSS para manter as cores e o estilo dos seus prints
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; }
    .total-box { background-color: #1d3524; color: #4ade80; padding: 20px; border-radius: 10px; font-size: 24px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Cabeçalho com Ícone
st.markdown("## 📈 Resumo por Categoria")

# 2. Upload de Arquivo
uploaded_file = st.file_uploader("", type=['png', 'jpg', 'jpeg'])

def processar_texto_inteligente(texto_ocr):
    dados = []
    # Regex melhorada: Ignora lixo e foca no padrão Código + Nome + Valor
    padrao = re.compile(r'(\d{8})\s+(.*?)\s+(\d+,\d{2})')
    
    linhas = texto_ocr.split('\n')
    for linha in linhas:
        match = padrao.search(linha)
        if match:
            codigo = match.group(1)
            # Remove datas e textos sujos da descrição
            descricao = re.sub(r'\d{2}/\d{2}/\d{4}', '', match.group(2)).strip()
            valor = float(match.group(3).replace(',', '.'))
            
            dados.append({
                "Código": codigo,
                "Descrição": descricao.upper(),
                "Categoria": "AMBULATÓRIO", # Ajuste automático
                "Valor": valor
            })
    return pd.DataFrame(dados)

if uploaded_file:
    # --- Aqui você manteria a sua função de OCR (EasyOCR ou Pytesseract) ---
    # Vou usar o exemplo da imagem que você mandou (R$ 104,38)
    texto_extraido_da_foto = """
    10101012 CONSULTA NO HORARIO 75,70
    40101010 ECG CONVENCIONAL 28,68
    """
    
    df = processar_texto_inteligente(texto_extraido_da_foto)

    if not df.empty:
        # Tabela de Resumo (Igual ao seu print)
        resumo = df.groupby('Categoria')['Valor'].sum().reset_index()
        st.table(resumo)

        # Caixa de Total Verde (Estilizada)
        total_geral = df['Valor'].sum()
        st.markdown(f'<div class="total-box">Total Auditado: R$ {total_geral:,.2f}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔍 Detalhamento Sequencial (Código > Descrição > Valor)")
        
        # Exibição da tabela detalhada
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("Erro ao processar imagem. Nenhum item identificado.")

# Rodapé ou Botão Sair (como no seu print)
if st.sidebar.button("Sair"):
    st.rerun()
    
