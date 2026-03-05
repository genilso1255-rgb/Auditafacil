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
        
        # ESTRATÉGIA NOVA: Isolar apenas o canal preto para ignorar canetas coloridas
        # Transformamos a imagem para que o que é colorido (caneta) fique cinza claro e suma
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Aumentamos o contraste bruscamente para forçar o texto impresso a aparecer
        _, img_bin = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
        
        # Lemos a página toda focando na estrutura de tabela (psm 6)
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            linha = linha.upper().strip()
            # Pega valores que terminam com centavos (ex: 336,33 ou 1.009,02)
            matches = re.findall(r'(\d+[\.,]\d{2})', linha)
            
            if matches:
                try:
                    # Nas suas fotos, o valor cobrado é SEMPRE o último da direita
                    valor_str = matches[-1]
                    val = float(valor_str.replace('.', '').replace(',', '.'))
                    
                    # Se o valor for um código TUSS (sem vírgula lida), o float falha e pula
                    if val > 15000.0 or val < 0.01: continue 

                    # Classificação robusta baseada nas suas categorias reais
                    cat = "OUTROS"
                    if any(x in linha for x in ["SALA", "TAXA", "ALUG", "REGISTRO", "PORT"]): cat = "TAXAS E ALUGUEIS"
                    elif any(x in linha for x in ["GAS", "OXIG", "AR COMP"]): cat = "GASES"
                    elif any(x in linha for x in ["MEDIC", "DIETA", "SOLU", "AMP", "SORO"]): cat = "MEDICAMENTOS"
                    elif any(x in linha for x in ["MATER", "FIO", "DESC", "AGUL", "LUV", "SERIN"]): cat = "MATERIAL"
                    elif any(x in linha for x in ["DIARIA", "APART", "ENFERM"]): cat = "DIARIA DE ENFERMARIA"
                    elif any(x in linha for x in ["OPME", "ORTE", "PROT", "ESPEC"]): cat = "OPME"
                    elif "HONOR" in linha: cat = "HONORARIOS"
                    
                    if cat in resumo: resumo[cat] += val
                except: continue
    return resumo

# ... (restante do código de login e interface igual ao anterior)
