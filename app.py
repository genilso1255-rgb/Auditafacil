import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import cv2
import numpy as np
from io import BytesIO

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
def process_image(file):
    # Abrir imagem
    image = Image.open(file)
    
    # Converter HEIC para RGB se necessário
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Converter para numpy array para processamento
    img_np = np.array(image)
    
    # Converter para escala de cinza
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    
    # Aplicar threshold para melhorar OCR
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # OCR
    text = pytesseract.image_to_string(thresh, lang='por')
    return text

# Função para extrair valores monetários do texto
def extract_values(text):
    """
    Extrai linhas que contém valores em formato monetário português (R$ 12.345,67)
    Ignora CPFs, CNPJs, códigos TUSS e números isolados
    """
    linhas = text.split("\n")
    dados = []
    for linha in linhas:
        linha = linha.strip()
        # Ignorar linhas vazias
        if not linha:
            continue
        # Procurar valores monetários no formato 12.345,67
        import re
        valores = re.findall(r'\d{1,3}(?:\.\d{3})*,\d{2}', linha)
        if valores:
            # Pega o último valor da linha (geralmente é o valor do procedimento)
            valor = valores[-1]
            # Converte para float
            valor_float = float(valor.replace('.', '').replace(',', '.'))
            # Adiciona linha e valor
            dados.append((linha, valor_float))
    return dados

# Função para classificar categoria baseado no nome da linha
def categorize_line(linha):
    linha_lower = linha.lower()
    
    # Honorários: qualquer linha relacionada a regiões do corpo ou honorários
    if any(x in linha_lower for x in ["cabeça", "pescoço", "nariz", "olhos", "seios", "sistema", "honorário"]):
        return "Honorários"
    
    # Material Descartável: fios cirúrgicos ou materiais simples
    if any(x in linha_lower for x in ["fio cirúrgico", "material descartável", "material hospitalar"]):
        return "Material Descartável"
    
    # Material Especial: OPME, prótese, órtese
    if any(x in linha_lower for x in ["prótese", "órtese", "opme", "material especial"]):
        return "Material Especial"
    
    # Medicamentos: dieta, medicamento, restrito
    if any(x in linha_lower for x in ["medicamento", "dieta"]):
        return "Medicamentos"
    
    # Pacotes Especiais
    if any(x in linha_lower for x in ["pacote especial"]):
        return "Pacotes Especiais"
    
    # Diárias
    if "diária" in linha_lower:
        return "Diárias"
    
    # Gases Médicos
    if "gás" in linha_lower:
        return "Gases Médicos"
    
    # Taxas
    if "taxa" in linha_lower or "sala" in linha_lower:
        return "Taxas"
    
    # Exames: teste diagnóstico ou patologia
    if any(x in linha_lower for x in ["teste diagnóstico", "patologia", "exame"]):
        return "Exames"
    
    # Se não encaixar em nada, ignorar
    return None

# Função para processar os dados extraídos e gerar DataFrame final
def generate_dataframe(dados):
    df = pd.DataFrame(columns=["Categoria Final", "Subtotal Conta Suja (R$)"])
    
    # Inicializar categorias com zero
    for cat in CATEGORIAS:
        df = pd.concat([df, pd.DataFrame({"Categoria Final": [cat], "Subtotal Conta Suja (R$)": [0.0]})], ignore_index=True)
    
    # Somar valores por categoria
    for linha, valor in dados:
        categoria = categorize_line(linha)
        if categoria:
            df.loc[df["Categoria Final"] == categoria, "Subtotal Conta Suja (R$)"] += valor
    
    # Ordenar alfabeticamente
    df = df.sort_values("Categoria Final").reset_index(drop=True)
    # Inicializar coluna Conta Limpa e Glosa zeradas (preparar para comparar duas contas)
    df["Subtotal Conta Limpa (R$)"] = 0.0
    df["Glosa (R$)"] = 0.0
    
    return df

# Streamlit interface
st.title("Auditoria de Contas Hospitalares")

uploaded_file = st.file_uploader("Carregue a foto da conta (PNG, JPG, JPEG, HEIC convertido):", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Conta carregada", use_column_width=True)
    texto_extraido = process_image(uploaded_file)
    dados_extraidos = extract_values(texto_extraido)
    
    if not dados_extraidos:
        st.warning("Nenhum valor monetário encontrado. Verifique a imagem ou o formato do arquivo.")
    else:
        df_final = generate_dataframe(dados_extraidos)
        st.dataframe(df_final)
        # Botão para download
        towrite = BytesIO()
        df_final.to_excel(towrite, index=False, sheet_name="Auditoria")
        towrite.seek(0)
        st.download_button(
            label="Baixar Planilha Excel",
            data=towrite,
            file_name="auditoria_conta.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
