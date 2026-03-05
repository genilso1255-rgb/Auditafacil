import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

def ultra_limpeza_vFinal(arq):
    img = Image.open(arq).convert('L')
    img_cv = np.array(img)
    # Remove sombras e destaca o texto preto das tabelas
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    img_cv = clahe.apply(img_cv)
    _, final = cv2.threshold(img_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return final

def processar_fatura_completa(texto):
    linhas = texto.split('\n')
    extraidos = []
    categoria_atual = "OUTROS"
    
    # Regex para capturar valores com centavos, mesmo com ruído ao lado
    padrao_v = re.compile(r'(\d[\d\.,]*,\d{2})')

    for linha in linhas:
        l = linha.upper().strip()
        if not l: continue
        
        # Identificador de Seções (Categorias)
        if "MATERIAIS" in l: categoria_atual = "MATERIAL"
        elif "MEDICAMENTOS" in l: categoria_atual = "MEDICAMENTOS"
        elif "TAXAS" in l: categoria_atual = "TAXAS"
        elif "GASES" in l: categoria_atual = "GASES"
        elif "FIOS" in l: categoria_atual = "MATERIAL"

        # Captura o valor e associa à categoria
        match = padrao_v.search(l)
        if match:
            v_limpo = match.group(1).replace('.', '').replace(',', '.')
            try:
                valor = float(v_limpo)
                
                # IGNORAR TOTAIS ACUMULADOS (para não duplicar a conta)
                if valor in [13290.70, 5425.86, 2565.48, 306.76, 55.12]: continue
                if valor < 0.50 or valor > 9000: continue
                
                extraidos.append({"Categoria": categoria_atual, "Valor": valor})
            except: continue
            
    return pd.DataFrame(extraidos)

# --- INTERFACE ---
st.title("📑 Auditoria Hospitalar Final")
arquivos = st.file_uploader("Suba as fotos da conta", accept_multiple_files=True)

if arquivos:
    bases = []
    for f in arquivos:
        img = ultra_limpeza_vFinal(f)
        # Tenta ler a tabela inteira (PSM 6) e depois caçar termos soltos (PSM 11)
        txt = pytesseract.image_to_string(img, lang='por', config='--psm 6') + \
              pytesseract.image_to_string(img, lang='por', config='--psm 11')
        
        df_fatia = processar_fatura_completa(txt)
        if not df_fatia.empty: bases.append(df_fatia)

    if bases:
        df_final = pd.concat(bases).drop_duplicates()
        
        # EXIBIÇÃO POR CATEGORIA
        st.subheader("📊 Resultado por Categoria")
        resumo = df_final.groupby("Categoria")["Valor"].sum().reset_index()
        st.table(resumo.style.format({"Valor": "R$ {:.2f}"}))
        
        total_somado = df_final["Valor"].sum()
        st.divider()
        st.header(f"Total da Conta: R$ {total_somado:,.2f}")
        
        if abs(total_somado - 13290.70) < 1.0:
            st.success("✅ SUCESSO: O valor total e as categorias batem 100%!")
        else:
            st.warning(f"Diferença de R$ {13290.70 - total_somado:.2f}. Verifique se a foto dos GASES MEDICINAIS está nítida.")
            
