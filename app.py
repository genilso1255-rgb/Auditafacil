import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def limpar_imagem(imagem_pil):
    img_np = np.array(imagem_pil.convert('RGB'))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # Threshold agressivo para manter apenas o texto impresso (preto)
    _, img_bin = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
    return img_bin

def processar_auditar_facil(arquivos):
    # AS GAVETAS REAIS DO AUDITAR FÁCIL
    resumo_sujo = {
        "MATERIAL DESCARTÁVEL": 0.0, # Materiais + Fios Cirúrgicos
        "MATERIAL ESPECIAL": 0.0,    # Órteses e Próteses
        "MEDICAMENTOS": 0.0,         # Medicamentos + Dietas
        "GASES": 0.0,                # Apenas Gases Médicos
        "TAXAS": 0.0,                # Taxas e Aluguéis
        "DIÁRIAS": 0.0,              # Diárias de Apartamento/Enfermaria
        "PACOTES ESPECIAIS": 0.0,    # Apenas Pacotes
        "EXAMES": 0.0                # Diagnósticos e Imagem
    }
    
    for arq in arquivos:
        img_bin = limpar_imagem(Image.open(arq))
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            
            # Captura o valor monetário (último da direita)
            matches = re.findall(r'(\d+[\.,]\d{2})', ln)
            if not matches: continue
            try:
                valor = float(matches[-1].replace('.', '').replace(',', '.'))
            except: continue

            # --- LÓGICA DE GAVETAS PURAS ---
            
            # GASES (Isolado)
            if any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPRIMIDO", "GAS MEDICINAIS"]):
                resumo_sujo["GASES"] += valor
            
            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS CIRURGICOS", "MATERIAIS HOSPITALARES", "MATERIAL DESCARTAVEL"]):
                resumo_sujo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (Apenas OPME)
            elif any(x in ln for x in ["ORTESES", "PROTESES", "SINTESE", "MATERIAL ESPECIAL"]):
                resumo_sujo["MATERIAL ESPECIAL"] += valor
                
            # MEDICAMENTOS (Medicamentos + Dietas)
            elif any(x in ln for x in ["MEDICAMENTOS", "DIETA", "SOLUCAO", "COMUM", "RESTRITO"]):
                resumo_sujo["MEDICAMENTOS"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXAS", "ALUGUEIS", "USO DE SALA", "EQUIPAMENTOS", "ADMINISTRATIVAS"]):
                resumo_sujo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "APARTAMENTO", "ENFERMARIA"]):
                resumo_sujo["DIÁRIAS"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["METODOS DIAGNOSTICOS", "IMAGEM", "RAIO X", "LABORATORIO"]):
                resumo_sujo["EXAMES"] += valor

            # PACOTES
            elif "PACOTES ESPECIAIS" in ln:
                resumo_sujo["PACOTES ESPECIAIS"] += valor
                
    return resumo_sujo

# --- INTERFACE ---
st.title("🛡️ Auditar Fácil - 2026")

uploads = st.file_uploader("Arraste os documentos aqui", accept_multiple_files=True)

if uploads:
    resultado = processar_auditar_facil(uploads)
    
    st.markdown("### Resumo da Conta Suja (Acumulado)")
    
    # Exibe apenas categorias que têm valor, sem "Outros" ou misturas
    for cat, total in resultado.items():
        if total > 0:
            st.write(f"**{cat}:** R$ {total:,.2f}")
    
    total_geral = sum(resultado.values())
    st.divider()
    st.subheader(f"Total Bruto: R$ {total_geral:,.2f}")
    
