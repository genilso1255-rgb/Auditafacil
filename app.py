import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pillow_heif
import cv2
import numpy as np
from io import BytesIO
import re

# Configuração do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # ajuste conforme sua instalação

# Categorias finais
CATEGORIAS = [
    "Diárias",
    "Exames",
    "Gases Médicos",
    "Honorários",
    "Material Descartável",
    "Material Especial",
    "Medicamentos",
    "Pacotes Especiais",
    "Taxas"
]

# Função para abrir imagem e converter HEIC se necessário
def open_image(uploaded_file):
    try:
        if uploaded_file.name.lower().endswith(".heic"):
            heif_file = pillow_heif.from_bytes(uploaded_file.read())
            image = heif_file.to_pil()
        else:
            image = Image.open(uploaded_file)
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image
    except Exception as e:
        st.error(f"Erro ao abrir a imagem {uploaded_file.name}: {e}")
        return None

# Função para processar OCR
def ocr_image(image):
    img_np = np.array(image)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh, lang='por')
    return text

# Extrair valores monetários
def extract_values(text):
    linhas = text.split("\n")
    dados = []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        # Ignorar CPF, CNPJ ou códigos
        if re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', linha) or re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', linha):
            continue
        valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
        if valores:
            valor = valores[-1]
            valor_float = float(valor.replace('.', '').replace(',', '.'))
            dados.append((linha, valor_float))
    return dados

# Categorizar linha
def categorize_line(linha):
    linha_lower = linha.lower()
    if any(x in linha_lower for x in ["cabeça", "pescoço", "nariz", "olhos", "seios", "sistema", "honorário"]):
        return "Honorários"
    if any(x in linha_lower for x in ["fio cirúrgico", "material descartável", "material hospitalar"]):
        return "Material Descartável"
    if any(x in linha_lower for x in ["prótese", "órtese", "opme", "material especial"]):
        return "Material Especial"
    if any(x in linha_lower for x in ["medicamento", "dieta"]):
        return "Medicamentos"
    if "pacote especial" in linha_lower:
        return "Pacotes Especiais"
    if "diária" in linha_lower:
        return "Diárias"
    if "gás" in linha_lower:
        return "Gases Médicos"
    if "taxa" in linha_lower or "sala" in linha_lower:
        return "Taxas"
    if any(x in linha_lower for x in ["teste diagnóstico", "patologia", "exame"]):
        return "Exames"
    return None

# Gerar DataFrame por conta
def generate_dataframe(dados):
    df = pd.DataFrame(columns=["Categoria Final", "Subtotal (R$)"])
    for cat in CATEGORIAS:
        df = pd.concat([df, pd.DataFrame({"Categoria Final": [cat], "Subtotal (R$)": [0.0]})], ignore_index=True)
    for linha, valor in dados:
        categoria = categorize_line(linha)
        if categoria:
            df.loc[df["Categoria Final"] == categoria, "Subtotal (R$)"] += valor
    df = df.sort_values("Categoria Final").reset_index(drop=True)
    return df

# Interface Streamlit
st.title("Auditoria de Contas Hospitalares")

uploaded_suja = st.file_uploader("Carregue a foto da conta SUJA (PNG, JPG, JPEG, HEIC):", type=None)
uploaded_limpa = st.file_uploader("Carregue a foto da conta LIMPA (PNG, JPG, JPEG, HEIC):", type=None)

if uploaded_suja and uploaded_limpa:
    image_suja = open_image(uploaded_suja)
    image_limpa = open_image(uploaded_limpa)
    
    if image_suja and image_limpa:
        st.image([image_suja, image_limpa], caption=["Conta Suja", "Conta Limpa"], use_column_width=True)
        
        # OCR
        texto_suja = ocr_image(image_suja)
        texto_limpa = ocr_image(image_limpa)
        
        dados_suja = extract_values(texto_suja)
        dados_limpa = extract_values(texto_limpa)
        
        if not dados_suja or not dados_limpa:
            st.warning("Nenhum valor monetário encontrado em uma ou ambas as contas.")
        else:
            df_suja = generate_dataframe(dados_suja)
            df_limpa = generate_dataframe(dados_limpa)
            
            # Juntar as duas contas e calcular glosa
            df_final = df_suja.copy()
            df_final = df_final.rename(columns={"Subtotal (R$)": "Subtotal Conta Suja (R$)"})
            df_final["Subtotal Conta Limpa (R$)"] = df_limpa["Subtotal (R$)"]
            df_final["Glosa (R$)"] = df_final["Subtotal Conta Suja (R$)"] - df_final["Subtotal Conta Limpa (R$)"]
            
            st.dataframe(df_final)
            
            # Download Excel
            towrite = BytesIO()
            df_final.to_excel(towrite, index=False, sheet_name="Auditoria")
            towrite.seek(0)
            st.download_button(
                label="Baixar Planilha Excel",
                data=towrite,
                file_name="auditoria_contas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
