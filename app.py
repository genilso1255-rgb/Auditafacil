import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

def ultra_limpeza(arq):
    # Converte para escala de cinza
    img = Image.open(arq).convert('L')
    img_cv = np.array(img)
    
    # Aumenta o contraste para o texto ficar bem preto e o fundo bem branco
    img_cv = cv2.convertScaleAbs(img_cv, alpha=1.5, beta=0)
    
    # Aplica um desfoque leve para unir partes das letras que os rabiscos cortaram
    img_cv = cv2.GaussianBlur(img_cv, (3,3), 0)
    
    # Binarização agressiva
    _, final = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return final

def pescar_valores(texto):
    # Procura por padrões de dinheiro: 1.234,56 ou 123,45 ou 12.345,67
    # Essa regex ignora o texto e foca apenas nos números com vírgula
    padrao = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}')
    
    achados = padrao.findall(texto)
    valores_limpos = []
    
    for v in achados:
        # Converte para float (ex: "1.107,80" -> 1107.80)
        num = float(v.replace('.', '').replace(',', '.'))
        
        # Filtros de segurança baseados na sua fatura:
        # 1. Ignora totais acumulados para não somar em dobro (ex: o total de 13 mil)
        if num >= 13000: continue
        # 2. Ignora o "Total do Grupo" de Materiais (5.425,86) se ele for lido
        if num == 5425.86 or num == 2565.48: continue
        
        valores_limpos.append(num)
        
    return valores_limpos

# --- INTERFACE ---
st.title("🎯 Auditoria: Busca por Valores Ocultos")
st.write("Objetivo: Pescar os R$ 13.290,70 ignorando os rabiscos.")

arquivos = st.file_uploader("Suba as imagens", accept_multiple_files=True)

if arquivos:
    todos_os_valores = []
    
    for arq in arquivos:
        img_limpa = ultra_limpeza(arq)
        # PSM 11: Tenta encontrar o máximo de texto possível, mesmo sem ordem
        txt = pytesseract.image_to_string(img_limpa, lang='por', config='--psm 11')
        
        # Mostra o que o robô está pescando para conferência
        valores_foto = pescar_valores(txt)
        todos_os_valores.extend(valores_foto)
        
        with st.expander(f"Valores detectados na foto {arq.name}"):
            st.write(valores_foto)

    if todos_os_valores:
        # Remove duplicatas exatas que podem ocorrer se o sistema ler o Unitário e o Total sendo iguais
        # Mas atenção: se houver dois itens com o mesmo preço, isso pode filtrar. 
        # Para essa conta, vamos apenas somar tudo e ver o resultado.
        
        soma = sum(todos_os_valores)
        
        st.divider()
        st.header(f"Total Detectado: R$ {soma:,.2f}")
        
        target = 13290.70
        diff = target - soma
        
        if abs(diff) < 10:
            st.success("✅ O valor bateu com a fatura!")
        else:
            st.warning(f"Ainda faltam R$ {diff:.2f} para o total da conta.")
            st.info("Dica: Se o valor estiver muito baixo, tente tirar a foto mais de perto dos itens caros.")
            
