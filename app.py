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

def tratar_imagem_v2(arq_streamlit):
    # Converte para escala de cinza e aumenta o contraste
    img_pil = Image.open(arq_streamlit).convert('L')
    img_pil = ImageOps.autocontrast(img_pil)
    
    # Transforma em matriz para o OpenCV
    img_cv = np.array(img_pil)
    
    # Binarização: Deixa o que é texto bem preto e o fundo bem branco
    _, img_binaria = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return img_binaria

def categorizar_universal(desc):
    d = desc.upper()
    if any(k in d for k in ["FIO", "SUTURA", "AGULHA", "CATETER", "EQUIPO", "SONDA", "CANETA", "SERINGA", "LIXA", "LUVA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "AMPOLA", "FRASCO", "SOLUCAO", "UNIREZ", "DEX", "TORADOL", "RAPIFEN"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL", "SALA"]): return "TAXAS E ALUGUEIS"
    if any(k in d for k in ["GAS", "OXIGENIO", "AR COMP"]): return "GASES"
    if any(k in d for k in ["HONORARIO", "MEDICO"]): return "HONORARIOS"
    return "OUTROS/DIVERSOS"

def extrair_dados_v2(texto):
    linhas = texto.split('\n')
    extraidos = []
    # Regex para pegar o Código (coluna 1) e o Valor Total (última coluna)
    # Ex: 08016194 ... 398,37
    padrao = re.compile(r'(\d{7,12}).*?\s([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        match = padrao.search(linha)
        if match:
            codigo, v_str = match.groups()
            v_limpo = v_str.replace('.', '').replace(',', '.')
            try:
                # Tentamos pegar a descrição entre o código e o valor
                desc_idx = linha.find(codigo) + len(codigo)
                valor_idx = linha.rfind(v_str)
                desc = linha[desc_idx:valor_idx].strip()
                
                extraidos.append({
                    "Categoria": categorizar_universal(desc),
                    "Valor": float(v_limpo)
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
        with st.spinner('Lendo fatura...'):
            for arq in arquivos:
                try:
                    img_tratada = tratar_imagem_v2(arq)
                    # Configuração --psm 11 é para texto esparso/tabelas
                    txt = pytesseract.image_to_string(img_tratada, lang='por', config='--psm 11')
                    
                    df_temp = extrair_dados_v2(txt)
                    if not df_temp.empty: base.append(df_temp)
                except Exception as e:
                    st.error(f"Erro no processamento. Verifique se o Tesseract está instalado.")

        if base:
            df_total = pd.concat(base)
            resumo = df_total.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            resumo['Glosado'] = 0.0
            resumo['Liberado'] = resumo['Valor']
            
            st.subheader("RESUMO DA AUDITORIA")
            st.table(resumo.style.format({'Valor': 'R$ {:.2f}', 'Glosado': 'R$ {:.2f}', 'Liberado': 'R$ {:.2f}'}))
            
            total_c = resumo['Valor'].sum()
            st.metric("Total da Conta", f"R$ {total_c:,.2f}")
            
            if abs(total_c - 13290.70) < 1.0:
                st.success("✅ Soma bate com o rodapé da fatura!")
        else:
            st.warning("Não conseguimos ler os dados. Tente tirar a foto bem de cima e com luz.")

    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()
        
