import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
import pandas as pd
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AuditaFacil ADM", layout="wide")

# --- ESTADO DE SESSÃO (LOGIN) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.title("🏥 AuditaFacil - Acesso Administrativo")
    cpf = st.text_input("CPF do Administrador")
    senha = st.text_input("Senha (6 dígitos)", type="password")
    
    if st.button("Acessar Painel"):
        if len(senha) == 6:
            st.session_state.logado = True
            st.success("Acesso liberado!")
            st.rerun()
        else:
            st.error("Senha inválida.")

# --- MOTOR DE PROCESSAMENTO DE IMAGEM ---
def processar_imagem(img_pil):
    # Converter para OpenCV e Alinhar
    img = np.array(img_pil.convert('RGB'))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Alinhamento Automático e Limpeza (Trata 'Conta Suja')
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # OCR - Leitura do texto
    texto = pytesseract.image_to_string(thresh, lang='por')
    return texto

def categorizar_por_codigo_e_nome(codigo, nome):
    cod = str(codigo)
    nome = nome.upper()
    
    # Regras de Negócio Específicas
    if "DIETA" in nome: return "MEDICAMENTOS"
    if "FIO" in nome: return "MATERIAL DESCARTAVEL"
    if any(x in nome for x in ["ORTESE", "PROTESE", "ESPECIAL", "OPME"]): return "MATERIAL ESPECIAL"
    
    # Classificação por Faixa de Código TUSS (Exemplos comuns)
    if cod.startswith(('1', '2')): return "HONORARIOS"
    if cod.startswith('6'): return "MEDICAMENTOS"
    if cod.startswith('3'): return "EXAMES"
    if cod.startswith('9'): return "TAXAS E ALUGUEIS"
    if cod.startswith('0'): return "GASES"
    if "DIARIA" in nome: return "DIARIA DE ENFERMARIA"
    
    return "OUTROS"

# --- INTERFACE PRINCIPAL ---
if not st.session_state.logado:
    tela_login()
else:
    st.sidebar.header("⚙️ Opções")
    if st.sidebar.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    st.header("📸 Auditoria de Contas (Brasília/DF Star/Sírio)")
    
    # Permite subir várias fotos (Limpa e Suja do mesmo paciente)
    arquivos = st.file_uploader("Selecione as fotos (Múltiplas)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

    if arquivos:
        todos_itens = []
        resumo_financeiro = {
            "HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL DESCARTAVEL": 0.0,
            "GASES": 0.0, "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0,
            "EXAMES": 0.0, "MATERIAL ESPECIAL": 0.0, "OUTROS": 0.0
        }

        with st.spinner('Analisando imagens e consolidando valores...'):
            for arq in arquivos:
                img_pil = Image.open(arq)
                texto_extraido = processar_imagem(img_pil)
                
                # Regex para extrair Código, Nome e Valor
                padrao = re.compile(r'(\d{8,10})?\s*([A-Z\s]{3,})\s+.*?([\d\.,]+)$')
                
                for linha in texto_extraido.split('\n'):
                    match = padrao.search(linha.strip().upper())
                    if match:
                        codigo, nome, valor_str = match.groups()
                        try:
                            valor = float(valor_str.replace('.', '').replace(',', '.'))
                            cat = categorizar_por_codigo_e_nome(codigo if codigo else "", nome)
                            
                            resumo_financeiro[cat] += valor
                            todos_itens.append({"Código": codigo, "Item": nome, "Categoria": cat, "Valor": valor})
                        except:
                            continue

        # Exibição dos Resultados Consolidados
        st.subheader("📊 Fechamento Consolidado")
        df_resumo = pd.DataFrame(list(resumo_financeiro.items()), columns=['Categoria', 'Total (R$)'])
        st.table(df_resumo[df_resumo['Total (R$)'] > 0])

        st.metric("VALOR TOTAL DA CONTA", f"R$ {df_resumo['Total (R$)'].sum():,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        with st.expander("🔍 Ver Detalhes (Item por Item)"):
            st.dataframe(pd.DataFrame(todos_itens))
            
