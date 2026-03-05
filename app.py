import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def limpar_imagem(imagem_pil):
    """Remove ruídos e marcas de caneta para focar no texto impresso."""
    img_np = np.array(imagem_pil.convert('RGB'))
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    # Threshold ajustado para ignorar carimbos e canetas coloridas
    _, img_bin = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY)
    return img_bin

def extrair_dados_rah(texto):
    """Captura a tabela de glosas do documento RAH."""
    glosas = {}
    padrao = r"(MATERIAL|GASES|MEDICAMENTOS|MATERIAL ESPECIAL|TAXAS E ALUGUEIS|DIARIA)\s+1\s+R\$\s+[\d\.,]+\s+R\$\s+([\d\.,]+)"
    matches = re.findall(padrao, texto.upper())
    for cat, valor in matches:
        glosas[cat] = float(valor.replace('.', '').replace(',', '.'))
    return glosas

def processar_auditar_facil(arquivos):
    # Gavetas de agrupamento definidas pelo usuário
    resumo_categorias = {
        "MATERIAL DESCARTÁVEL": 0.0,
        "MATERIAL ESPECIAL (OPME)": 0.0,
        "MEDICAMENTOS E DIETAS": 0.0,
        "DIÁRIAS": 0.0,
        "TAXAS E GASES": 0.0,
        "EXAMES": 0.0,
        "OUTROS": 0.0
    }
    
    texto_completo = ""
    for arq in arquivos:
        img_bin = limpar_imagem(Image.open(arq))
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')
        texto_completo += texto + "\n"

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            # Pega o último valor da linha (Total do item)
            valores = re.findall(r'(\d+[\.,]\d{2})', ln)
            if not valores: continue
            
            val = float(valores[-1].replace('.', '').replace(',', '.'))
            
            # Lógica de agrupamento por nome (ignora códigos TUSS)
            if any(x in ln for x in ["FIOS", "MATERIAIS HOSPITALARES", "DESC", "AGULHA"]):
                resumo_categorias["MATERIAL DESCARTÁVEL"] += val
            elif any(x in ln for x in ["ORTESES", "PROTESES", "SINTESE", "MATERIAL ESPECIAL"]):
                resumo_categorias["MATERIAL ESPECIAL (OPME)"] += val
            elif any(x in ln for x in ["MEDICAMENTOS", "DIETA", "SOLUCAO", "SORO"]):
                resumo_categorias["MEDICAMENTOS E DIETAS"] += val
            elif any(x in ln for x in ["DIARIA", "APARTAMENTO", "ENFERMARIA"]):
                resumo_categorias["DIÁRIAS"] += val
            elif any(x in ln for x in ["TAXA", "SALA", "ALUGUEL", "GASES", "OXIGENIO"]):
                resumo_categorias["TAXAS E GASES"] += val
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORATORIO"]):
                resumo_categorias["EXAMES"] += val
            else:
                resumo_categorias["OUTROS"] += val

    glosas_rah = extrair_dados_rah(texto_completo)
    return resumo_categorias, glosas_rah

# --- Interface Auditar Fácil ---
st.set_page_config(page_title="Auditar Fácil", layout="wide")
st.title("🛡️ Auditar Fácil - 2026")
st.markdown("### Processamento de Conta Suja vs. Conta Limpa")

uploads = st.file_uploader("Upload das fotos da Conta e do RAH", accept_multiple_files=True)

if uploads:
    dados_sujos, glosas = processar_auditar_facil(uploads)
    
    # Criando o painel comparativo
    col1, col2, col3 = st.columns(3)
    total_sujo = sum(dados_sujos.values())
    total_glosa = sum(glosas.values())
    
    col1.metric("Conta Suja (Bruto)", f"R$ {total_sujo:,.2f}")
    col2.metric("Total Glosado", f"R$ {total_glosa:,.2f}", delta_color="inverse")
    col3.metric("Conta Limpa (Líquido)", f"R$ {total_sujo - total_glosa:,.2f}")

    st.write("#### Detalhamento por Categoria")
    tabela_final = []
    for cat, valor in dados_sujos.items():
        if valor > 0:
            # Mapeamento simples para cruzar categorias da conta com categorias do RAH
            glosa_correspondente = 0.0
            if "MATERIAL DESCARTÁVEL" in cat: glosa_correspondente = glosas.get("MATERIAL", 0)
            elif "MEDICAMENTOS" in cat: glosa_correspondente = glosas.get("MEDICAMENTOS", 0)
            
            tabela_final.append({
                "Categoria": cat,
                "Conta Suja": f"R$ {valor:,.2f}",
                "Glosa": f"R$ {glosa_correspondente:,.2f}",
                "Conta Limpa": f"R$ {valor - glosa_correspondente:,.2f}"
            })
    
    st.table(tabela_final)
    
