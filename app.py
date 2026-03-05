import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
import pandas as pd
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="AuditaFacil - Painel ADM", layout="centered")

# --- SISTEMA DE LOGIN (COMO ERA ANTES) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.title("🏥 AuditaFacil")
    st.subheader("Acesso do Administrador")
    
    # Login por CPF e Senha de 6 dígitos como você definiu
    cpf = st.text_input("Digite seu CPF")
    senha = st.text_input("Digite sua senha (6 dígitos)", type="password")
    
    if st.button("Entrar no Sistema"):
        if len(senha) == 6:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta ou incompleta.")

# --- LÓGICA DE PROCESSAMENTO ---
def processar_auditoria(arquivos):
    resumo = {
        "HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0,
        "GASES": 0.0, "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0,
        "EXAMES": 0.0, "MATERIAL ESPECIAL (OPME)": 0.0
    }
    lista_conferencia = []

    for arq in arquivos:
        img_pil = Image.open(arq)
        img = np.array(img_pil.convert('RGB'))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Alinhamento e Limpeza para Contas Sujas
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        texto = pytesseract.image_to_string(thresh, lang='por')

        # Busca por Código TUSS, Nome e Valor Cobrado
        padrao = re.compile(r'(\d{8,10})?\s*([A-Z\s]{3,})\s+.*?([\d\.,]+)$')

        for linha in texto.split('\n'):
            match = padrao.search(linha.strip().upper())
            if match:
                codigo, nome, valor_str = match.groups()
                try:
                    val = float(valor_str.replace('.', '').replace(',', '.'))
                    
                    # Regras de Categoria (Dieta, Fios, OPME)
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
                    lista_conferencia.append({"Cód": codigo, "Item": nome, "Cat": cat, "R$": val})
                except: continue
    return resumo, lista_conferencia

# --- TELA PRINCIPAL (LAYOUT ANTERIOR) ---
if not st.session_state.logado:
    tela_login()
else:
    st.title("📊 Painel de Auditoria")
    st.write("Bem-vindo, Administrador.")
    
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    st.divider()

    # Upload configurado para a sua câmera (3:4 e HEIF)
    fotos = st.file_uploader("Enviar Contas (Limpa/Suja)", type=['jpg', 'jpeg', 'png', 'heic'], accept_multiple_files=True)

    if fotos:
        if st.button("Iniciar Auditoria"):
            res, itens = processar_auditoria(fotos)
            
            st.subheader("Resumo por Categoria")
            # Tabela igual ao exemplo da foto
            df_resumo = pd.DataFrame(list(res.items()), columns=['Descrição', 'Valor Cobrado'])
            st.table(df_resumo[df_resumo['Valor Cobrado'] > 0])
            
            total = sum(res.values())
            st.metric("Total da Conta", f"R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            with st.expander("Conferir Itens Detalhados"):
                st.dataframe(pd.DataFrame(itens))
                
