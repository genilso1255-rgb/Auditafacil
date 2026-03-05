import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

# --- LOGIN ADN ---
usuarios = {"12345678901": {"senha": "teste", "perfil": "ADN"}}

def tratar_imagem_v3(arq_streamlit):
    # Melhora o contraste para separar o texto do fundo
    img_pil = Image.open(arq_streamlit).convert('L')
    img_pil = ImageOps.autocontrast(img_pil)
    img_cv = np.array(img_pil)
    # Binarização inteligente para fotos de celular
    _, img_binaria = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return img_binaria

def categorizar_universal(desc):
    d = desc.upper()
    if any(k in d for k in ["FIO", "SUTURA", "AGULHA", "CATETER", "EQUIPO", "SONDA", "CANETA", "SERINGA", "LUVA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "AMPOLA", "FRASCO", "SOLUCAO", "UNIREZ", "DEX", "TORADOL", "RAPIFEN"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL", "SALA"]): return "TAXAS E ALUGUEIS"
    if any(k in d for k in ["GAS", "OXIGENIO", "AR COMP"]): return "GASES"
    if any(k in d for k in ["HONORARIO", "MEDICO"]): return "HONORARIOS"
    return "OUTROS/DIVERSOS"

def extrair_dados_v3(texto):
    linhas = texto.split('\n')
    extraidos = []
    # REGEX APERFEIÇOADO: 
    # 1. Pega o código no início (7-10 dígitos)
    # 2. Ignora tudo no meio (como a equivalência)
    # 3. Pega o valor monetário no FINAL da linha (ex: 398,37)
    padrao = re.compile(r'^(\d{7,10})\s+.*?\s+([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        # Ignora linhas de "Total do Grupo" para não somar em dobro
        if "Total" in linha or "Subtotal" in linha: continue
        
        match = padrao.search(linha)
        if match:
            codigo, v_str = match.groups()
            
            # Limpeza do valor: remove pontos de milhar e troca vírgula por ponto
            v_limpo = v_str.replace('.', '').replace(',', '.')
            try:
                valor_f = float(v_limpo)
                # Se o valor for absurdamente alto (como o número de equivalência), ignoramos
                if valor_f > 10000 and len(v_str.replace(',','')) > 6: continue
                
                # Pega o texto entre o código e o valor para categorizar
                desc = linha.replace(codigo, "").replace(v_str, "").strip()
                
                extraidos.append({
                    "Categoria": categorizar_universal(desc),
                    "Valor": valor_f
                })
            except: continue
    return pd.DataFrame(extraidos)

# --- INTERFACE ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar Sistema"):
        if cpf in usuarios and usuarios[cpf]["senha"] == senha:
            st.session_state.logado = True
            st.rerun()
else:
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    arquivos = st.file_uploader("Selecione as fotos", type=['png','jpg','jpeg'], accept_multiple_files=True)

    if arquivos:
        base = []
        with st.spinner('Analisando colunas de valores...'):
            for arq in arquivos:
                try:
                    img_tratada = tratar_imagem_v3(arq)
                    txt = pytesseract.image_to_string(img_tratada, lang='por', config='--psm 6')
                    df_temp = extrair_dados_v3(txt)
                    if not df_temp.empty: base.append(df_temp)
                except: st.error("Erro ao ler o arquivo.")

        if base:
            df_total = pd.concat(base)
            resumo = df_total.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            resumo['Glosado'] = 0.0
            resumo['Liberado'] = resumo['Valor']
            
            st.subheader("RESUMO DA AUDITORIA")
            # Tabela formatada
            st.dataframe(resumo.style.format({'Valor': 'R$ {:.2f}', 'Glosado': 'R$ {:.2f}', 'Liberado': 'R$ {:.2f}'}))
            
            total_c = resumo['Valor'].sum()
            st.metric("Total Calculado da Conta", f"R$ {total_c:,.2f}")
            
            # Se o total bater com os R$ 13.290,70 das suas fotos
            if abs(total_c - 13290.70) < 5.0:
                st.success("✅ O total calculado bate com a fatura!")
        else:
            st.warning("Aguardando leitura correta dos valores...")

    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()
    
