import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def processar_auditar_facil_v3(arquivos):
    # GAVETAS PURAS (Somente as que você definiu)
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0, # Materiais + Fios
        "MATERIAL ESPECIAL": 0.0,    # OPME
        "MEDICAMENTOS": 0.0,         # Medicamentos + Dietas
        "GASES": 0.0,                # APENAS Gases
        "TAXAS": 0.0,                # Sala, Equipamentos, Administrativa
        "DIÁRIAS": 0.0,              # Apartamento/Enfermaria
        "PACOTES ESPECIAIS": 0.0,    # Apenas o que for Pacote
        "EXAMES": 0.0                # Imagem/Laboratório
    }
    
    for arq in arquivos:
        img = np.array(Image.open(arq).convert('RGB'))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Limpeza pesada para ler apenas o texto impresso
        _, img_bin = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            # Pega o valor da direita
            matches = re.findall(r'(\d+[\.,]\d{2})', ln)
            if not matches: continue
            try:
                valor = float(matches[-1].replace('.', '').replace(',', '.'))
            except: continue

            # --- REGRAS DE OURO DO AUDITAR FÁCIL ---
            
            # GASES (Isolado conforme sua regra)
            if any(x in ln for x in ["GASES MEDICINAIS", "GASES", "OXIGENIO"]):
                resumo["GASES"] += valor
            
            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS CIRURGICOS", "MATERIAIS HOSPITALARES"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESES", "PROTESES", "SINTESE", "MATERIAL ESPECIAL"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # MEDICAMENTOS (Medicamentos + Dietas)
            elif any(x in ln for x in ["MEDICAMENTOS", "DIETA", "USO COMUM", "RESTRITO"]):
                resumo["MEDICAMENTOS"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXAS ADMINISTRATIVE", "USO DE SALA", "EQUIPAMENTOS", "TAXAS"]):
                resumo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "APARTAMENTO"]):
                resumo["DIÁRIAS"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICOS", "IMAGEM", "RAIO X"]):
                resumo["EXAMES"] += valor

            # PACOTES
            elif "PACOTES ESPECIAIS" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# Interface simples e limpa
st.title("🛡️ Auditar Fácil - Versão Corrigida")
uploads = st.file_uploader("Upload", accept_multiple_files=True)

if uploads:
    res = processar_auditar_facil_v3(uploads)
    for cat, total in res.items():
        if total > 0:
            st.write(f"**{cat}:** R$ {total:,.2f}")
    st.subheader(f"Total Bruto: R$ {sum(res.values()):,.2f}")
    
