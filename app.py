import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
import pandas as pd
from PIL import Image
from pillow_heif import register_heif_opener

# Habilita suporte para as fotos HEIF do seu celular
register_heif_opener()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN (ESTILO DA SUA FOTO) ---
def tela_login():
    # Logo azul e ícones conforme sua imagem
    st.markdown("<h1 style='color: #2e91e5;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha", type="password")
    
    # Botão "Acessar" alinhado à esquerda
    if st.button("Acessar"):
        if len(senha) == 6:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha de 6 dígitos necessária.")

# --- MOTOR DE CÁLCULO (TUSS + CATEGORIAS) ---
def processar_contas(arquivos):
    resumo = {
        "HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0,
        "GASES": 0.0, "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0,
        "EXAMES": 0.0, "MATERIAL ESPECIAL (OPME)": 0.0
    }
    itens_detalhados = []

    for arq in arquivos:
        img_pil = Image.open(arq)
        img = np.array(img_pil.convert('RGB'))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Limpeza para "Contas Sujas" e Alinhamento
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        texto = pytesseract.image_to_string(thresh, lang='por')

        # Regex para capturar Código TUSS e Valor Cobrado
        padrao = re.compile(r'(\d{8,10})?\s*([A-Z\s]{3,})\s+.*?([\d\.,]+)$')

        for linha in texto.split('\n'):
            match = padrao.search(linha.strip().upper())
            if match:
                codigo, nome, valor_str = match.groups()
                try:
                    # Trata ponto e vírgula nos valores
                    val = float(valor_str.replace('.', '').replace(',', '.'))
                    
                    # Regras de Categoria (Dietas, Fios e OPME)
                    cat = "OUTROS"
                    if "HONOR" in nome: cat = "HONORARIOS"
                    elif "MEDIC" in nome or "DIETA" in nome: cat = "MEDICAMENTOS"
                    elif "FIO" in nome or "DESCART" in nome or "MATERIAL" in nome: cat = "MATERIAL"
                    elif "GAS" in nome: cat = "GASES"
                    elif "TAXA" in nome or "ALUGUE" in nome: cat = "TAXAS E ALUGUEIS"
                    elif "DIARIA" in nome or "ENFERM" in nome: cat = "DIARIA DE ENFERMARIA"
                    elif "EXAME" in nome: cat = "EXAMES"
                    elif any(x in nome for x in ["ORTESE", "PROTESE", "OPME", "ESPECIAL"]): 
                        cat = "MATERIAL ESPECIAL (OPME)"

                    if cat in resumo: resumo[cat] += val
                    itens_detalhados.append({"Item": nome, "Cat": cat, "Valor": val})
                except: continue
    return resumo, itens_detalhados

# --- FLUXO DO SISTEMA ---
if not st.session_state.logado:
    tela_login()
else:
    st.title("📊 Auditoria Hospitalar")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.write("Administrador logado.")
    st.divider()

    # Aceita várias fotos (Limpa e Suja)
    fotos = st.file_uploader("Selecione as fotos das contas", type=['jpg', 'jpeg', 'png', 'heic'], accept_multiple_files=True)

    if fotos:
        if st.button("Calcular Total"):
            res, detalhes = processar_contas(fotos)
            
            st.subheader("Resumo de Cobrança")
            # Tabela igual à do Hospital Brasília
            df_res = pd.DataFrame(list(res.items()), columns=['Descrição', 'Total Cobrado'])
            st.table(df_res[df_res['Total Cobrado'] > 0])
            
            total_geral = sum(res.values())
            st.metric("TOTAL GERAL", f"R$ {total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            with st.expander("Conferir itens lidos"):
                st.dataframe(pd.DataFrame(detalhes))
                
