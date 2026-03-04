import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Auditoria de Faturas - Genilson", layout="wide")

st.title("📊 Sistema de Auditoria de Faturas")
st.write("Projeto: Instituto de Cardiologia / Auditoria Hospitalar")

# 1. Upload do Arquivo
uploaded_file = st.file_uploader("Arraste aqui o arquivo da fatura (PDF ou Imagem)", type=['pdf', 'png', 'jpg'])

def extrair_dados_corrigidos(texto):
    dados = []
    # Regex para pegar: CODIGO (8 digitos) + DESCRICAO + VALOR (00,00)
    # Ignora datas no meio do texto
    padrao = re.compile(r'(\d{8})\s+(.*?)\s+(\d+,\d{2})')
    
    linhas = texto.split('\n')
    for linha in linhas:
        match = padrao.search(linha)
        if match:
            codigo = match.group(1)
            # Limpa a descrição removendo datas (ex: 27/11/2025)
            desc_limpa = re.sub(r'\d{2}/\d{2}/\d{4}', '', match.group(2)).strip()
            valor = float(match.group(3).replace(',', '.'))
            
            # Categoria inteligente
            categoria = "AMBULATÓRIO"
            if "MATERIAIS" in desc_limpa.upper():
                categoria = "MATERIAIS DESCARTÁVEIS"
            
            dados.append({
                "Código": codigo,
                "Descrição": desc_limpa,
                "Categoria": categoria,
                "Valor": valor
            })
    return pd.DataFrame(dados)

if uploaded_file:
    # Simulando a leitura do texto (Aqui entra o seu motor de OCR atual)
    # Se você usa EasyOCR ou Tesseract, passe o resultado para a função abaixo
    texto_exemplo = """
    10101012 27/11/2025 CONSULTA CARDIOLOGICA 75,70
    40101010 ECG CONVENCIONAL 28,68
    """
    
    df = extrair_dados_corrigidos(texto_exemplo)

    if not df.empty:
        # Exibição dos Totais
        total_auditado = df['Valor'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Total Auditado", f"R$ {total_auditado:,.2f}")
        col2.metric("Itens Encontrados", len(df))

        st.subheader("Detalhamento Sequencial")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Não foi possível extrair dados. Verifique a qualidade da imagem.")

st.sidebar.info("Versão 2.0 - Ajustada para faturas do Instituto de Cardiologia.")
