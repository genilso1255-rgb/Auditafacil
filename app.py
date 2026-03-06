# app.py
import streamlit as st
from PIL import Image
import pytesseract
from pillow_heif import register_heif_opener

register_heif_opener()

# Função para garantir que a imagem seja compatível com pytesseract
def abrir_imagem(file):
    img = Image.open(file)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

# Função para processar a conta e extrair valores por categoria
def processar_conta(imagem):
    texto = pytesseract.image_to_string(imagem, lang='por')
    
    categorias = {
        "HONORÁRIOS MÉDICOS": 0,
        "EXAMES": 0,
        "MEDICAMENTOS": 0,
        "MATERIAIS DESCARTÁVEIS": 0,
        "GASES MÉDICOS": 0,
        "MATERIAIS ESPECIAIS (OPME)": 0,
        "TAXAS HOSPITALARES": 0,
        "DIÁRIAS HOSPITALARES": 0
    }
    
    linhas = texto.split('\n')
    for linha in linhas:
        for cat in categorias:
            if cat.lower() in linha.lower():
                numeros = [float(s.replace(',', '.')) for s in linha.split() if s.replace(',', '.').replace('.', '').isdigit()]
                if numeros:
                    categorias[cat] += numeros[0]
    return categorias

# Função para calcular glosa entre conta suja e limpa
def calcular_glosa(conta_suja, conta_limpa):
    glosas = {}
    for cat in conta_suja:
        glosas[cat] = conta_suja[cat] - conta_limpa.get(cat, 0)
        if glosas[cat] < 0:
            glosas[cat] = 0
    return glosas

# Streamlit app
st.title("Auditoria Hospitalar")

st.write("📸 Suba as fotos da conta suja e da conta limpa (PNG, JPG, JPEG ou HEIC)")

foto_suja = st.file_uploader("Conta Suja", type=["png", "jpg", "jpeg", "heic"])
foto_limpa = st.file_uploader("Conta Limpa", type=["png", "jpg", "jpeg", "heic"])

if foto_suja and foto_limpa:
    img_suja = abrir_imagem(foto_suja)
    img_limpa = abrir_imagem(foto_limpa)
    
    st.image([img_suja, img_limpa], caption=["Conta Suja", "Conta Limpa"], width=300)
    
    conta_suja = processar_conta(img_suja)
    conta_limpa = processar_conta(img_limpa)
    glosas = calcular_glosa(conta_suja, conta_limpa)
    
    st.write("### Resultado Conta Suja")
    st.json(conta_suja)
    
    st.write("### Resultado Conta Limpa")
    st.json(conta_limpa)
    
    st.write("### Glosas por Categoria")
    st.json(glosas)
