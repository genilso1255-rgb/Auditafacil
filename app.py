import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

def limpeza_profunda(arq):
    # Converte para cinza e aplica normalização para remover sombras de dobras no papel
    img = Image.open(arq).convert('L')
    img_cv = np.array(img)
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization) para destacar o texto fraco
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img_cv = clahe.apply(img_cv)
    
    # Binarização com preservação de detalhes (ajuda a ler através de vistos e carimbos)
    img_bin = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 25, 12)
    return img_bin

def extrair_dados_resilientes(texto):
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    extraidos = []
    cat_atual = "OUTROS"
    
    # Regex flexível para capturar valores mesmo com ruído ao redor
    re_valor = re.compile(r'(\d[\d\.,]*,\d{2})')

    for i, linha in enumerate(linhas):
        # Atualiza a categoria baseada nos cabeçalhos da fatura
        if "MATERIAIS" in linha: cat_atual = "MATERIAL"
        elif "MEDICAMENTOS" in linha: cat_atual = "MEDICAMENTOS"
        elif "TAXAS" in linha: cat_atual = "TAXAS"
        
        # Ignora linhas que somam grupos (evita duplicidade)
        if "TOTAL DO GRUPO" in linha or "TOTAL DA CONTA" in linha: continue

        match = re_valor.search(linha)
        if match:
            v_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                valor = float(v_limpo)
                if valor > 13000: continue # Ignora o total geral se lido na linha
                
                # Busca a descrição: se a linha for curta, tenta pegar a linha anterior (quebra de linha)
                desc = linha.replace(match.group(1), "").strip()
                if len(desc) < 5 and i > 0:
                    desc = linhas[i-1] + " " + desc
                
                extraidos.append({"Categoria": cat_atual, "Valor": valor, "Item": desc[:30]})
            except: continue
            
    return pd.DataFrame(extraidos)

# --- INTERFACE DE CONFERÊNCIA ---
st.title("Auditoria Hospitalar: Ajuste Fino")
st.info("Foco: Recuperar os R$ 9.163,54 que faltaram na última leitura.")

arquivos = st.file_uploader("Suba as imagens", type=['jpg','png','jpeg'], accept_multiple_files=True)

if arquivos:
    lista_itens = []
    for arq in arquivos:
        img_proc = limpeza_profunda(arq)
        # PSM 3: Detecta automaticamente blocos de texto, ideal para descrições quebradas
        txt = pytesseract.image_to_string(img_proc, lang='por', config='--psm 3')
        
        df_parcial = extrair_dados_resilientes(txt)
        if not df_parcial.empty:
            lista_itens.append(df_parcial)
            
    if lista_itens:
        df_final = pd.concat(lista_itens).drop_duplicates()
        st.subheader("📋 Itens Identificados (Conferência)")
        st.dataframe(df_final, use_container_width=True)
        
        total = df_final["Valor"].sum()
        st.metric("Soma Total Calculada", f"R$ {total:,.2f}", delta=f"R$ {total - 13290.70:.2f}")
        
