import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_final(linha_texto):
    # Procura todos os padrões de valores financeiros na linha (ex: 1.234,56 ou 123,45)
    valores = re.findall(r'(\d[\d\.]*,\d{2})', linha_texto)
    if valores:
        # A regra de ouro da auditoria: o valor total/liberado é SEMPRE o último da direita
        v_str = valores[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def identificar_categoria_universal(linha):
    ln = linha.upper()
    # Categorização por radicais de palavras (mais abrangente que nomes fixos)
    if any(x in ln for x in ["MATERIA", "FIOS", "DESCART", "AGULHA", "LUVAS", "SERINGA"]): return "MATERIAIS"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "DIETA", "AMPO"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["HONOR", "PROCED", "SISTEMA", "CIRURG", "ASSIST"]): return "HONORÁRIOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "USO", "ADMIN"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "APART"]): return "DIÁRIAS"
    if any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "OPME", "ESPECIAL"]): return "OPME/ESPECIAL"
    if "PACOTE" in ln: return "PACOTES"
    return "OUTROS"

def processar_motor_universal(arquivo):
    resumo = {}
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Binarização adaptativa para ler documentos com carimbos ou sombras
    img_proc = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_proc, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        if not ln or any(s in ln.upper() for s in ["TOTAL DA CONTA", "TOTAL GERAL", "DESCONTO"]): continue
        
        valor = extrair_valor_final(ln)
        if valor <= 0: continue
        
        cat = identificar_categoria_universal(ln)
        resumo[cat] = resumo.get(cat, 0.0) + valor
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Universal", layout="wide")
st.title("🛡️ Auditar Fácil - Sistema de Auditoria Aberto")

col1, col2 = st.columns(2)
with col1: f_suja = st.file_uploader("📂 Subir Conta Original (SUJA)", key="s")
with col2: f_limpa = st.file_uploader("📂 Subir Relatório (LIMPA/RAH)", key="l")

if f_suja and f_limpa:
    suja = processar_motor_universal(f_suja)
    limpa = processar_motor_universal(f_limpa)
    
    # Consolidação de categorias para a tabela
    todas_categorias = sorted(list(set(suja.keys()) | set(limpa.keys())))
    
    st.subheader("📊 Batimento de Glosas")
    dados_tabela = []
    for c in todas_categorias:
        v_s, v_l = suja.get(c, 0.0), limpa.get(c, 0.0)
        dados_tabela.append({
            "Categoria": c,
            "Cobrado (R$)": f"{v_s:,.2f}",
            "Liberado (R$)": f"{v_l:,.2f}",
            "Glosa (R$)": f"{max(0, v_s - v_l):,.2f}"
        })
    
    st.table(dados_tabela)
    
    total_s, total_l = sum(suja.values()), sum(limpa.values())
    st.metric("TOTAL GLOSADO", f"R$ {total_s - total_l:,.2f}", delta=f"R$ {total_s - total_l:,.2f}", delta_color="inverse")
    
