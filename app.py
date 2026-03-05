import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image
import pytesseract

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    label { color: white !important; }
    .stMetric { background-color: #1e2127; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ADN ---
usuarios = {"12345678901": {"senha": "teste", "perfil": "ADN"}}

def limpar_e_preparar(arq_streamlit):
    # CORREÇÃO DEFINITIVA: Abre o arquivo como imagem PIL primeiro
    img_pil = Image.open(arq_streamlit).convert('RGB')
    # Transforma em matriz que o OpenCV entende (Numpy Array)
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # Filtro para manter apenas o texto impresso (preto) e ignorar canetas
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 120])
    mask = cv2.inrange(hsv, lower_black, upper_black)
    return mask

def categorizar_universal(desc):
    d = desc.upper()
    # Regras universais por palavras-chave
    if any(k in d for k in ["FIO", "SUTURA", "AGULHA", "CATETER", "EQUIPO", "SONDA", "CANETA", "SERINGA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "AMPOLA", "FRASCO", "SOLUCAO", "UNIREZ", "DEX"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL", "SALA"]): return "TAXAS E ALUGUEIS"
    if "GAS" in d or "OXIGENIO" in d: return "GASES"
    return "OUTROS/DIVERSOS"

def extrair_dados(texto):
    linhas = texto.split('\n')
    extraidos = []
    # Captura códigos (8-12 dígitos) + descrição + valor final
    padrao = re.compile(r'(\d{8,12})\s+(.*?)\s+([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        match = padrao.search(linha)
        if match:
            codigo, desc, v_str = match.groups()
            v_limpo = v_str.replace('.', '').replace(',', '.')
            try:
                extraidos.append({"Categoria": categorizar_universal(desc), "Valor": float(v_limpo)})
            except: continue
    return pd.DataFrame(extraidos)

# --- INTERFACE ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF (apenas números)")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar Sistema"):
        if cpf in usuarios and usuarios[cpf]["senha"] == senha:
            st.session_state.logado = True
            st.rerun()
        else: st.error("Dados incorretos.")
else:
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    st.write("Bem-vindo, Administrador (ADN)")
    
    arquivos = st.file_uploader("Selecione os arquivos", type=['png','jpg','jpeg','pdf'], accept_multiple_files=True)

    if arquivos:
        base = []
        with st.spinner('Limpando imagem e processando...'):
            for arq in arquivos:
                try:
                    img_final = limpar_e_preparar(arq)
                    txt = pytesseract.image_to_string(img_final, lang='por')
                    df_temp = extrair_dados(txt)
                    if not df_temp.empty: base.append(df_temp)
                except Exception:
                    st.error(f"Erro no arquivo {arq.name}. Tente tirar a foto com mais luz.")

        if base:
            df_total = pd.concat(base)
            resumo = df_total.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            resumo['Glosado'] = 0.0
            resumo['Liberado'] = resumo['Valor']
            
            st.subheader("ITENS DA CONTA")
            st.table(resumo.style.format({'Valor': 'R$ {:.2f}', 'Glosado': 'R$ {:.2f}', 'Liberado': 'R$ {:.2f}'}))

            t_c = resumo['Valor'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cobrado", f"R$ {t_c:,.2f}")
            c2.metric("Total Glosado", "R$ 0,00")
            c3.metric("Total Liberado", f"R$ {t_c:,.2f}")
            
            # Validação para sua conta real de R$ 13.290,70
            if abs(t_c - 13290.70) < 1.0:
                st.success("✅ Valores batem com a conta real!")

    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()
                
