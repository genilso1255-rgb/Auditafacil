import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def processar_hospital(arquivos):
    resumo = {"HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0, "GASES": 0.0, 
              "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0, "EXAMES": 0.0, "OPME": 0.0}
    
    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        
        # Converte para cinza e aplica um filtro para destacar apenas o texto preto
        # Isso ajuda a ignorar os riscos de caneta colorida
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        img_bin = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            linha = linha.upper().strip()
            
            # 1. Busca valores com vírgula (R$ 0,00)
            # 2. Ignora números sem vírgula (Códigos TUSS) para evitar os "milhões"
            matches = re.findall(r'\d+,\d{2}', linha)
            
            if matches:
                try:
                    # Pegamos o último valor da linha (Coluna VI Total)
                    valor_str = matches[-1]
                    val = float(valor_str.replace(',', '.'))
                    
                    # Se o valor for maior que 10.000, provavelmente é um erro de leitura do código
                    if val > 10000.0: continue 

                    # Classificação por termos que aparecem nas suas fotos
                    cat = "OUTROS"
                    if any(x in linha for x in ["SALA", "TAXA", "ALUG", "INTERN", "PORT"]): cat = "TAXAS E ALUGUEIS"
                    elif any(x in linha for x in ["GAS", "OXIG", "AR COMP"]): cat = "GASES"
                    elif any(x in linha for x in ["MEDIC", "DIETA", "SOLU", "AMP", "VUL", "SORO"]): cat = "MEDICAMENTOS"
                    elif any(x in linha for x in ["MATER", "FIO", "DESC", "AGUL", "LUV", "SERIN", "CURAT"]): cat = "MATERIAL"
                    elif any(x in linha for x in ["DIARIA", "APART", "ENFERM"]): cat = "DIARIA DE ENFERMARIA"
                    elif any(x in linha for x in ["OPME", "ORTE", "PROT", "ESPEC", "SINT"]): cat = "OPME"
                    elif "HONOR" in linha: cat = "HONORARIOS"
                    
                    if cat in resumo: resumo[cat] += val
                except: continue
    return resumo
    
