import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_br(texto_linha):
    # Procura o valor no final da linha, ignorando ruídos entre o texto e o número
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_limpo)
        except: return 0.0
    return 0.0

def processar_auditar_facil_final_v6(arquivos):
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0,
        "MATERIAL ESPECIAL": 0.0,
        "MEDICAMENTOS": 0.0,
        "GASES": 0.0,
        "TAXAS": 0.0,
        "DIÁRIAS": 0.0,
        "HONORÁRIOS": 0.0,
        "EXAMES": 0.0,
        "PACOTES ESPECIAIS": 0.0
    }

    setores_ignorar = ["CENTRO CIRURGICO", "APARTAMENTO", "CTI ADULTO", "TOTAL DO SETOR", "VALOR TOTAL DA GUIA"]

    for arq in arquivos:
        img = np.array(Image.open(arq).convert('RGB'))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Filtro de nitidez para ler através de carimbos
        img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if not ln or any(s in ln for s in setores_ignorar): continue
            
            # Pega o valor da linha
            valor = extrair_valor_br(ln)
            if valor <= 0: continue

            # --- DISTRIBUIÇÃO NAS GAVETAS ---
            # HONORÁRIOS (Sistemas e Anatomia)
            if any(x in ln for x in ["NERVOSO", "SISTEMA", "MUSCULO", "CABECA", "PESCOCO", "NARIZ", "OLHOS", "SEIOS", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor
            # MEDICAMENTOS (Uso comum e restrito)
            elif any(x in ln for x in ["MEDICAM", "RESTRITO", "DIETA", "SOLUCAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
            # MATERIAL DESCARTÁVEL
            elif any(x in ln for x in ["FIOS CIR", "MATERIAIS HOSPITALARES", "DESCARTAVEL", "AGULHA"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
            # MATERIAL ESPECIAL
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO", "ADMINISTRATIVA"]):
                resumo["TAXAS"] += valor
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "ENFERMARIA"]):
                resumo["DIÁRIAS"] += valor
            # GASES
            elif any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPRIMIDO"]):
                resumo["GASES"] += valor
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORATORIO", "TOMOGRAFIA"]):
                resumo["EXAMES"] += valor
            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Pro", layout="wide")
st.title("🛡️ Auditar Fácil - Versão Definitiva")

uploads = st.file_uploader("Suba os documentos aqui", accept_multiple_files=True)

if uploads:
    with st.spinner('Consolidando conta suja...'):
        resultado = processar_auditar_facil_final_v6(uploads)
    
    st.markdown("### 📊 Resumo Consolidado")
    col1, col2 = st.columns(2)
    with col1:
        for cat, total in resultado.items():
            # Exibe todas, mesmo que R$ 0,00
            st.write(f"✅ **{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL DA CONTA (SOMA DAS GAVETAS)", f"R$ {total_geral:,.2f}")

    st.divider()
    st.success("Tudo pronto! Se o valor bater, você já pode confrontar com o RAH.")
            
