import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_final(texto_linha):
    # Procura qualquer número que termine com vírgula e dois dígitos (ex: 22.831,31)
    # Ele pega desde o primeiro dígito até os centavos, ignorando o que tiver no meio
    match = re.search(r'(\d[\d\.,]*\d,\d{2})|(\d+,\d{2})', texto_linha)
    if match:
        valor_str = match.group().replace('.', '').replace(',', '.')
        try:
            return float(valor_str)
        except:
            return 0.0
    return 0.0

def processar_conta_suja(arquivos):
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
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        
        # Processamento simples e eficaz: Cinza + Nitidez
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        texto = pytesseract.image_to_string(gray, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            
            # 1. Filtro de títulos (para não duplicar)
            if any(s in ln for s in setores_ignorar):
                continue
            
            # 2. Busca o valor (Milhares e Centavos)
            valor = extrair_valor_final(ln)
            if valor <= 0:
                continue

            # 3. Distribuição nas Gavetas (Ajustada com os itens que faltavam)
            
            # HONORÁRIOS (Sistemas, Anatomia e Honorários Médicos)
            if any(x in ln for x in ["HONORARIO", "CABECA", "PESCOCO", "NARIZ", "OLHOS", "SEIOS", "NERVOSO", "SISTEMA", "MUSCULO"]):
                resumo["HONORÁRIOS"] += valor
            
            # MEDICAMENTOS (Comum e Restrito)
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "NUTRICAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
                
            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS CIR", "MATERIAIS HOSPITALARES", "DESCARTAVEL", "AGULHA", "LUVAS"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO", "ADMINIST"]):
                resumo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA"]):
                resumo["DIÁRIAS"] += valor

            # GASES
            elif any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPR"]):
                resumo["GASES"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORAT", "TOMOGRAFIA"]):
                resumo["EXAMES"] += valor

            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Final", layout="wide")
st.title("🛡️ Auditar Fácil - Versão Restaurada")

uploads = st.file_uploader("Suba as imagens", accept_multiple_files=True)

if uploads:
    with st.spinner('Processando...'):
        resultado = processar_conta_suja(uploads)
    
    st.subheader("📋 Resumo da Conta")
    
    col1, col2 = st.columns(2)
    with col1:
        for cat in ["MATERIAL DESCARTÁVEL", "MATERIAL ESPECIAL", "MEDICAMENTOS", "GASES", "TAXAS", "DIÁRIAS", "HONORÁRIOS", "EXAMES", "PACOTES ESPECIAIS"]:
            total = resultado[cat]
            st.write(f"**{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL DA CONTA", f"R$ {total_geral:,.2f}")
        
    st.success("Busca de valores restaurada. Verifique se os R$ 75 mil apareceram.")
    
