import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

st.set_page_config(page_title="AuditaFácil", layout="centered")

if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.markdown("<h1 style='color: #2e91e5;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar"):
        if len(senha) == 6:
            st.session_state.logado = True
            st.rerun()

def processar_hospital(arquivos):
    resumo = {"HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0, "GASES": 0.0, 
              "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0, "EXAMES": 0.0, "OPME": 0.0}
    
    for arq in arquivos:
        img = Image.open(arq).convert('L')
        img_np = np.array(img)
        img_bin = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        texto = pytesseract.image_to_string(img_bin, lang='por')

        for linha in texto.split('\n'):
            linha = linha.upper()
            # REGRA DE OURO: Captura apenas números que tenham vírgula (formato de real)
            # Isso evita ler o código TUSS como se fosse valor.
            valores = re.findall(r'\d+,\d{2}', linha)
            
            if valores:
                try:
                    # Pegamos o último valor da linha (Coluna VI Total)
                    valor_str = valores[-1]
                    val = float(valor_str.replace(',', '.'))
                    
                    # Filtro de segurança: se o valor for absurdamente alto para um único item, ignoramos
                    if val > 50000.00: continue 
                    
                    cat = "OUTROS"
                    if any(x in linha for x in ["SALA", "TAXA", "ALUGUE", "REGISTRO"]): cat = "TAXAS E ALUGUEIS"
                    elif any(x in linha for x in ["GAS", "OXIG", "AR COMP"]): cat = "GASES"
                    elif any(x in linha for x in ["MEDIC", "DIETA", "SOLU", "AMP", "VUL"]): cat = "MEDICAMENTOS"
                    elif any(x in linha for x in ["MATER", "FIO", "DESC", "AGUL", "LUV", "SERINGA"]): cat = "MATERIAL"
                    elif any(x in linha for x in ["DIARIA", "APART", "ENFERM"]): cat = "DIARIA DE ENFERMARIA"
                    elif any(x in linha for x in ["OPME", "ORTESE", "PROTESE", "ESPEC"]): cat = "OPME"
                    elif "HONOR" in linha: cat = "HONORARIOS"
                    
                    if cat in resumo: resumo[cat] += val
                except: continue
    return resumo

if not st.session_state.logado:
    tela_login()
else:
    st.title("📊 Auditoria Hospitalar")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    fotos = st.file_uploader("Enviar Contas", type=['jpg', 'jpeg', 'png', 'heic'], accept_multiple_files=True)
    if fotos and st.button("Calcular Total"):
        res = processar_hospital(fotos)
        st.subheader("Resultado por Categoria")
        for c, v in res.items():
            if v > 0:
                st.write(f"**{c}:** R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        total_geral = sum(res.values())
        st.divider()
        st.metric("TOTAL GERAL DA CONTA", f"R$ {total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
