import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

# --- CONFIGURAÇÃO DE AMBIENTE ---
# No Streamlit Cloud, o Tesseract precisa estar no PATH. 
# Se rodar local, descomente a linha abaixo e aponte para seu .exe
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocessar_para_ocr(arquivo):
    # Converte para escala de cinza e melhora o contraste para eliminar sombras da foto
    img = Image.open(arquivo).convert('L')
    img = ImageOps.autocontrast(img, cutoff=2)
    img_cv = np.array(img)
    
    # Binarização adaptativa: transforma o papel em branco puro e o texto em preto nítido
    # Isso ajuda a ler através de rabiscos de caneta e sombras
    processada = cv2.adaptiveThreshold(
        img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 31, 15
    )
    return processada

def extrair_dados_fina_sintonia(texto):
    linhas = texto.split('\n')
    itens_extraidos = []
    categoria_atual = "OUTROS"
    
    # Padrão para identificar valores monetários brasileiros (ex: 1.107,80 ou 398,37)
    # Focamos na vírgula e nos dois centavos obrigatórios
    padrao_preco = re.compile(r'(\d[\d\.,]*,\d{2})$')

    for linha in linhas:
        l = linha.strip().upper()
        if not l: continue
        
        # Identifica mudança de seção na fatura para categorizar corretamente
        if "MATERIAIS" in l: categoria_atual = "MATERIAL"
        elif "MEDICAMENTOS" in l: categoria_atual = "MEDICAMENTOS"
        elif "TAXAS" in l: categoria_atual = "TAXAS"
        elif "GASES" in l: categoria_atual = "GASES"
        elif "FIOS" in l: categoria_atual = "MATERIAL" # Fios cirúrgicos são materiais
        
        # Ignora linhas de resumo para não somar o total duas vezes
        if "TOTAL DO GRUPO" in l or "TOTAL DA CONTA" in l: continue

        match = padrao_preco.search(l)
        if match:
            valor_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                valor_f = float(valor_str)
                # Trava de segurança para não ler números de equivalência/atendimento como dinheiro
                if valor_f > 10000: continue 
                
                itens_extraidos.append({
                    "Categoria": categoria_atual,
                    "Valor": valor_f,
                    "Texto": l # Guardamos para conferência
                })
            except:
                continue
    return pd.DataFrame(itens_extraidos)

# --- INTERFACE DE AUDITORIA ---
st.title("🔍 AuditaFácil - Debug de Precisão")
st.write("Foco: Atingir o valor real de R$ 13.290,70")

upload = st.file_uploader("Envie as fotos da fatura", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

if upload:
    lista_dfs = []
    with st.spinner("Processando imagens com binarização adaptativa..."):
        for arq in upload:
            try:
                img_proc = preprocessar_para_ocr(arq)
                # PSM 6: Assume um bloco único de texto (ideal para tabelas hospitalares)
                conteudo = pytesseract.image_to_string(img_proc, lang='por', config='--psm 6')
                
                # Mostra o texto bruto para o usuário ver o que o robô está enxergando
                with st.expander(f"Texto extraído de {arq.name}"):
                    st.text(conteudo)
                
                df_parcial = extrair_dados_fina_sintonia(conteudo)
                if not df_parcial.empty:
                    lista_dfs.append(df_parcial)
            except Exception as e:
                st.error(f"Erro ao processar {arq.name}. Verifique a iluminação da foto.")

    if lista_dfs:
        df_final = pd.concat(lista_dfs)
        
        # Agrupamento por categoria
        resumo = df_final.groupby("Categoria")["Valor"].sum().reset_index()
        
        st.subheader("📊 Resultado da Captura")
        st.table(resumo.style.format({"Valor": "R$ {:.2f}"}))
        
        soma_total = df_final["Valor"].sum()
        diferenca = 13290.70 - soma_total
        
        col1, col2 = st.columns(2)
        col1.metric("Total Detectado", f"R$ {soma_total:,.2f}")
        col2.metric("Diferença p/ Real", f"R$ {diferenca:,.2f}", delta_color="inverse")
        
        if abs(diferenca) < 1.0:
            st.success("🎯 Sucesso! O valor capturado bate com a fatura original.")
        else:
            st.warning("Ainda há divergência. Verifique no 'Texto extraído' se os valores com rabisco foram lidos.")
        
