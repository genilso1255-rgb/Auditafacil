# arquivo: auditoria_hospitalar.py
# Streamlit App - Auditoria Hospitalar Automática
# Bibliotecas: streamlit, pytesseract, OpenCV, PIL, pandas, numpy

import streamlit as st
from PIL import Image
import cv2
import numpy as np
import pytesseract
import pandas as pd
import re

# -----------------------------
# Funções auxiliares
# -----------------------------

def limpar_imagem(img):
    """
    Limpa a imagem para OCR:
    - converte para cinza
    - remove cores (rabiscos azul/vermelho/amarelo)
    - aumenta contraste
    - aplica threshold
    """
    img_cv = np.array(img)
    # Converter para cinza
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    
    # Threshold adaptativo para realçar o texto
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    # Remover ruído
    blur = cv2.medianBlur(thresh, 3)
    
    return blur

def extrair_valores_linha(linha):
    """
    Extrai valores em formato brasileiro (12.307,09) da linha
    Ignora CPF, CNPJ, códigos, datas
    """
    # Regex para valores BR: ponto opcional de milhar + vírgula + dois centavos
    pattern = r'\d{1,3}(?:\.\d{3})*,\d{2}'
    valores = re.findall(pattern, linha)
    return valores

def categorizar_linha(linha):
    """
    Categoriza a linha com base nas regras que combinamos
    """
    linha_lower = linha.lower()
    
    # Categorias
    if any(x in linha_lower for x in ['medicamento', 'dieta']):
        return 'MEDICAMENTOS'
    elif any(x in linha_lower for x in ['material hospitalar', 'fios cirúrgicos']):
        return 'MATERIAL DESCARTÁVEL'
    elif any(x in linha_lower for x in ['órtese', 'prótese', 'opme']):
        return 'MATERIAL ESPECIAL'
    elif any(x in linha_lower for x in ['honorário', 'cabeça', 'pescoço', 'sistema nervoso', 'sistema muscular', 'olhos', 'nariz', 'seios paranasais']):
        return 'HONORÁRIOS'
    elif any(x in linha_lower for x in ['taxa', 'diária']):
        return 'TAXAS / DIÁRIAS'
    elif any(x in linha_lower for x in ['pacote']):
        return 'PACOTES'
    elif any(x in linha_lower for x in ['exame', 'teste diagnóstico', 'patologia', 'laboratorial', 'histológico', 'biópsia']):
        return 'EXAMES'
    else:
        return 'OUTROS'

def parse_ocr_text(text):
    """
    Recebe texto OCR e retorna dataframe com categorias e valores
    """
    linhas = text.split('\n')
    dados = []
    
    for linha in linhas:
        valores = extrair_valores_linha(linha)
        if valores:
            categoria = categorizar_linha(linha)
            for val in valores:
                # Converter string BR para float
                val_float = float(val.replace('.', '').replace(',', '.'))
                dados.append({'Categoria': categoria, 'Valor (R$)': val_float})
                
    df = pd.DataFrame(dados)
    if df.empty:
        return df
    
    # Somar valores por categoria
    df_sum = df.groupby('Categoria', as_index=False).sum()
    return df_sum

def calcular_glosa(df_suja, df_limpa):
    """
    Recebe dois dataframes (suja e limpa) e retorna glosa por categoria
    """
    # Juntar categorias
    df_merge = pd.merge(df_suja, df_limpa, on='Categoria', how='outer', suffixes=('_Suja', '_Limpa'))
    df_merge.fillna(0, inplace=True)
    df_merge['Glosa (R$)'] = df_merge['Valor (R$)_Suja'] - df_merge['Valor (R$)_Limpa']
    return df_merge

# -----------------------------
# Streamlit Interface
# -----------------------------

st.title("Sistema de Auditoria Hospitalar Automática")

st.markdown("""
Faça upload das contas (imagem ou PDF convertido para imagem):
- Conta Suja (hospital)  
- Conta Limpa (auditada)
""")

arquivo_suja = st.file_uploader("Upload Conta Suja", type=['png', 'jpg', 'jpeg'])
arquivo_limpa = st.file_uploader("Upload Conta Limpa", type=['png', 'jpg', 'jpeg'])

if arquivo_suja and arquivo_limpa:
    # Abrir imagens
    img_suja = Image.open(arquivo_suja)
    img_limpa = Image.open(arquivo_limpa)
    
    # Limpar imagens
    img_suja_clean = limpar_imagem(img_suja)
    img_limpa_clean = limpar_imagem(img_limpa)
    
    # OCR
    texto_suja = pytesseract.image_to_string(img_suja_clean, lang='por')
    texto_limpa = pytesseract.image_to_string(img_limpa_clean, lang='por')
    
    # Parse e categorizar
    df_suja = parse_ocr_text(texto_suja)
    df_limpa = parse_ocr_text(texto_limpa)
    
    if df_suja.empty or df_limpa.empty:
        st.warning("Não foi possível detectar valores. Verifique a qualidade da imagem.")
    else:
        # Calcular glosa
        df_glosa = calcular_glosa(df_suja, df_limpa)
        
        st.subheader("Resumo por Categoria")
        st.dataframe(df_glosa.style.format({"Valor (R$)_Suja": "R$ {:,.2f}",
                                            "Valor (R$)_Limpa": "R$ {:,.2f}",
                                            "Glosa (R$)": "R$ {:,.2f}"}))
        
        # Totais
        total_suja = df_glosa['Valor (R$)_Suja'].sum()
        total_limpa = df_glosa['Valor (R$)_Limpa'].sum()
        total_glosa = df_glosa['Glosa (R$)'].sum()
        
        st.subheader("Totais")
        st.write(f"Total Conta Suja: R$ {total_suja:,.2f}")
        st.write(f"Total Conta Limpa: R$ {total_limpa:,.2f}")
        st.write(f"Glosa Total: R$ {total_glosa:,.2f}")
        
        # Mostrar categorias com glosa
        st.subheader("Categorias com Glosa")
        df_com_glosa = df_glosa[df_glosa['Glosa (R$)'] > 0]
        st.dataframe(df_com_glosa.style.format({"Glosa (R$)": "R$ {:,.2f}"}))

st.markdown("Feito por Xavi - Auditoria Hospitalar Automática")
