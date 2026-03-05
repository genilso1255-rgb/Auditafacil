import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image
import pytesseract

# --- CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    label { color: white !important; }
    .stMetric { background-color: #1e2127; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- USUÁRIO TESTE ---
usuarios = {"12345678901": {"senha": "teste", "perfil": "ADN"}}

# --- FUNÇÕES DE PROCESSAMENTO ---

def limpar_imagem(imagem_pil):
    # CORREÇÃO DO ERRO: Converter PIL para formato OpenCV corretamente
    img_array = np.array(imagem_pil.convert('RGB')) 
    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    # Filtro para ignorar caneta e manter apenas o preto impresso
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 100])
    mask = cv2.inrange(hsv, lower_black, upper_black)
    return mask

def extrair_categoria(descricao):
    d = descricao.upper()
    if any(k in d for k in ["FIO", "SUTURA", "CATETER", "EQUIPO", "SONDA", "CANETA", "AGULHA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "ENTERAL", "AMPOLA", "FRASCO", "SOLUCAO", "UNIREZ", "DEX"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL"]): return "TAXAS E ALUGUEIS"
    if "GAS" in d or "OXIGENIO" in d: return "GASES"
    return "OUTROS/DIVERSOS"

def processar_fatura(texto):
    linhas = texto.split('\n')
    extraidos = []
    # REGEX FLEXÍVEL: Código (8 a 12 dígitos) + Descrição + Valor Final
    padrao = re.compile(r'(\d{8,12})\s+(.*?)\s+([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        if not linha or "Total do Grupo" in linha: continue
        
        match = padrao.search(linha)
        if match:
            codigo, desc, valor_str = match.groups()
            # Limpa o valor (ex: 1.107,80 -> 1107.80)
            valor = float(valor_str.replace('.', '').replace(',', '.'))
            extraidos.append({
                "Categoria": extrair_categoria(desc),
                "Valor": valor
            })
    return pd.DataFrame(extraidos)

# --- SISTEMA DE LOGIN ---
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
        else:
            st.error("Dados incorretos.")
else:
    # --- TELA PRINCIPAL ---
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    arquivos = st.file_uploader("Arraste as fotos ou PDFs", type=['png','jpg','jpeg','pdf'], accept_multiple_files=True)

    if arquivos:
        base_dados = []
        with st.spinner('Limpando imagem e processando...'):
            for arq in arquivos:
                img_pil = Image.open(arq)
                mascara = limpar_imagem(img_pil)
                # OCR configurado para português
                texto = pytesseract.image_to_string(mascara, lang='por')
                df_temp = processar_fatura(texto)
                if not df_temp.empty:
                    base_dados.append(df_temp)
        
        if base_dados:
            df_final = pd.concat(base_dados)
            resumo = df_final.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            resumo['Glosado'] = 0.0
            resumo['Liberado'] = resumo['Valor'] - resumo['Glosado']

            st.subheader("ITENS DA CONTA")
            st.table(resumo.style.format({'Valor': 'R$ {:.2f}', 'Glosado': 'R$ {:.2f}', 'Liberado': 'R$ {:.2f}'}))

            # Totais
            total_c = resumo['Valor'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Cobrado", f"R$ {total_c:,.2f}")
            c2.metric("Total Glosado", f"R$ 0,00")
            c3.metric("Total Liberado", f"R$ {total_c:,.2f}")
            
            if total_c == 13290.70:
                st.success("✅ A conta bateu perfeitamente com o Hospital Brasília!")

    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()
        
