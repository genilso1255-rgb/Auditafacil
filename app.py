import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

def limpeza_final_total(arq):
    img = Image.open(arq).convert('L')
    img_cv = np.array(img)
    
    # Aumenta nitidez: essencial para os valores pequenos que faltam
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    img_cv = cv2.filter2D(img_cv, -1, kernel)
    
    # Remove ruídos de caneta (rabiscos circulares)
    img_cv = cv2.fastNlMeansDenoising(img_cv, h=30)
    
    # Binarização com limite dinâmico
    _, final = cv2.threshold(img_cv, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return final

def extrair_precisao_maxima(texto):
    # Regex melhorada: captura números mesmo se o ponto de milhar for lido como vírgula
    # ou se houver um caractere de "check" ao lado.
    padrao = re.compile(r'(\d{1,3}(?:[\.,]\d{3})*,\d{2})')
    
    achados = padrao.findall(texto)
    valores = []
    
    for v in achados:
        try:
            # Normaliza: remove pontos de milhar e troca vírgula decimal por ponto
            v_limpo = v.replace('.', '').replace(',', '.')
            num = float(v_limpo)
            
            # BLOQUEIO DE TOTAIS DE GRUPO (Evita duplicar os valores principais)
            if num in [5425.86, 306.76, 2565.48, 198.37, 55.12, 391.32, 13290.70]:
                continue
            
            if 0.50 < num < 10000.00:
                valores.append(num)
        except: continue
    return valores

# --- INTERFACE DE FECHAMENTO ---
st.title("🏁 Auditoria: Fechamento da Conta")
st.write("Meta: Localizar os R$ 133,43 faltantes.")

files = st.file_uploader("Suba as imagens novamente", accept_multiple_files=True)

if files:
    total_geral = []
    for f in files:
        img = limpeza_final_total(f)
        # PSM 6: Melhor para ler os valores alinhados na direita
        txt = pytesseract.image_to_string(img, lang='por', config='--psm 6')
        
        # O pulo do gato: se não achar nada, tenta com PSM 11 (texto esparso)
        achados = extrair_precisao_maxima(txt)
        if not achados:
            txt = pytesseract.image_to_string(img, lang='por', config='--psm 11')
            achados = extrair_precisao_maxima(txt)
            
