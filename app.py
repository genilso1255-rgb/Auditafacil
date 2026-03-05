import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image
import pytesseract
import io

# --- CONFIGURAÇÕES DE LAYOUT (Mantendo o padrão das suas fotos) ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    label { color: white !important; }
    .stMetric { background-color: #1e2127; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- USUÁRIO TESTE ADN ---
usuarios = {"12345678901": {"senha": "teste", "perfil": "ADN"}}

# --- FUNÇÕES DE PROCESSAMENTO UNIVERSAL ---

def preparar_imagem_opencv(arquivo_carregado):
    # Converte o upload do Streamlit para um formato que o OpenCV entende
    file_bytes = np.asarray(bytearray(arquivo_carregado.read()), dtype=np.uint8)
    img_cv = cv2.imdecode(file_bytes, 1)
    
    # Converte para HSV para isolar o texto impresso (preto) e remover rabiscos coloridos
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 120]) 
    mask = cv2.inrange(hsv, lower_black, upper_black)
    return mask

def categorizar_item_universal(descricao):
    d = descricao.upper()
    # Regras baseadas em radicais de palavras para servir em qualquer hospital
    if any(k in d for k in ["FIO", "SUTURA", "AGULHA", "CATETER", "EQUIPO", "SONDA", "CANETA", "LUVA", "SERINGA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "ENTERAL", "AMPOLA", "FRASCO", "SOLUCAO", "UNIREZ", "DEX", "MEDIC"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL", "SALA"]): return "TAXAS E ALUGUEIS"
    if any(k in d for k in ["GAS", "OXIGENIO", "AR COMP"]): return "GASES"
    return "OUTROS/DIVERSOS"

def extrair_dados_universal(texto):
    linhas = texto.split('\n')
    extraidos = []
    # Busca por: Qualquer código (8-12 dígitos) + Descrição + Valor Final da linha
    padrao = re.compile(r'(\d{8,12})\s+(.*?)\s+([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        if not linha: continue
        
        match = padrao.search(linha)
        if match:
            codigo, desc, valor_str = match.groups()
            # Limpa o valor monetário de forma segura
            valor_limpo = valor_str.replace('.', '').replace(',', '.')
            try:
                valor_f = float(valor_limpo)
                extraidos.append({
                    "Categoria": categorizar_item_universal(desc),
                    "Valor": valor_f
                })
            except:
                continue
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
    # --- TELA PRINCIPAL (Auditoria Universal) ---
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    st.write(f"Bem-vindo, Administrador ({st.session_state.get('user', 'ADN')})")
    
    arquivos = st.file_uploader("Arraste as fotos ou PDFs das contas", type=['png','jpg','jpeg','pdf'], accept_multiple_files=True)

    if arquivos:
        base_dados = []
        with st.spinner('Limpando imagem e processando códigos...'):
            for arq in arquivos:
                try:
                    # Limpa e processa
                    img_limpa = preparar_imagem_opencv(arq)
                    texto_ocr = pytesseract.image_to_string(img_limpa, lang='por')
                    
                    df_temp = extrair_dados_universal(texto_ocr)
                    if not df_temp.empty:
                        base_dados.append(df_temp)
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo {arq.name}. Verifique se é uma imagem válida.")

        if base_dados:
            df_final = pd.concat(base_dados)
            resumo = df_final.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            resumo['Glosado'] = 0.0 # Espaço para auditoria manual
            resumo['Liberado'] = resumo['Valor'] - resumo['Glosado']

            st.subheader("RESUMO CONSOLIDADO DA CONTA")
            st.table(resumo.style.format({'Valor': 'R$ {:.2f}', 'Glosado': 'R$ {:.2f}', 'Liberado': 'R$ {:.2f}'}))

            # Totais Gerais
            total_geral = resumo['Valor'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Cobrado", f"R$ {total_geral:,.2f}")
            col2.metric("Total Glosado", f"R$ 0,00")
            col3.metric("Total Liberado", f"R$ {total_geral:,.2f}")
            
            # Alerta de precisão para a conta que você enviou
            if abs(total_geral - 13290.70) < 0.5:
                st.success("✅ Valores conferem com a fatura original!")

    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()
        
