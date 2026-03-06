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

# Função para processar imagem e extrair texto
def process_image(uploaded_file):
    try:
        image = Image.open(uploaded_file)

        # Converter HEIC para RGB se necessário
        if image.format == "HEIC":
            image = pillow_heif.from_bytes(uploaded_file.read()).to_pil()
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Converter para numpy array
        img_np = np.array(image)
        # Escala de cinza
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        # Threshold para melhorar OCR
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        # OCR
        text = pytesseract.image_to_string(thresh, lang='por')
        return text
    except Exception as e:
        st.error(f"Erro ao processar a imagem: {e}")
        return ""

# Extrair valores monetários
def extract_values(text):
    linhas = text.split("\n")
    dados = []
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        # Ignorar CPFs, CNPJs ou códigos
        if re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', linha) or re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', linha):
            continue
        # Procurar valores monetários no formato brasileiro
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

# Gerar DataFrame final
def generate_dataframe(dados):
    df = pd.DataFrame(columns=["Categoria Final", "Subtotal Conta Suja (R$)"])
    for cat in CATEGORIAS:
        df = pd.concat([df, pd.DataFrame({"Categoria Final": [cat], "Subtotal Conta Suja (R$)": [0.0]})], ignore_index=True)
    for linha, valor in dados:
        categoria = categorize_line(linha)
        if categoria:
            df.loc[df["Categoria Final"] == categoria, "Subtotal Conta Suja (R$)"] += valor
    df = df.sort_values("Categoria Final").reset_index(drop=True)
    df["Subtotal Conta Limpa (R$)"] = 0.0
    df["Glosa (R$)"] = 0.0
    return df

# Streamlit interface
st.title("Auditoria de Contas Hospitalares")

uploaded_file = st.file_uploader("Carregue a foto da conta (PNG, JPG, JPEG, HEIC):", type=None)

if uploaded_file:
    st.image(uploaded_file, caption="Conta carregada", use_column_width=True)
    texto_extraido = process_image(uploaded_file)
    dados_extraidos = extract_values(texto_extraido)
    
    if not dados_extraidos:
        st.warning("Nenhum valor monetário encontrado. Verifique a imagem ou o formato do arquivo.")
    else:
        df_final = generate_dataframe(dados_extraidos)
        st.dataframe(df_final)
        towrite = BytesIO()
        df_final.to_excel(towrite, index=False, sheet_name="Auditoria")
        towrite.seek(0)
        st.download_button(
            label="Baixar Planilha Excel",
            data=towrite,
            file_name="auditoria_conta.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
