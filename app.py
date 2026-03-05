import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_fiel(linha):
    # Padrão universal: busca o último valor financeiro à direita da linha
    matches = re.findall(r'(\d[\d\.]*,\d{2})', linha)
    if matches:
        v_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def categorizar_estrito(linha):
    ln = linha.upper()
    # Identificação por radicais (funciona para qualquer conta hospitalar)
    if any(x in ln for x in ["HONOR", "NARIZ", "SISTEMA", "CABECA", "OLHOS", "SEIOS", "PROCED", "NERVOSO", "MUSCULO"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIAL", "FIOS", "DESCART", "AGULHA", "LUVAS", "MATERIAIS"]): return "MATERIAL DESCARTÁVEL"
    if any(x in ln for x in ["MEDICAM", "SORO", "DIETA", "SOLUCAO", "AMPO"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMIN", "USO"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "APART"]): return "DIÁRIAS"
    if any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]): return "MATERIAL ESPECIAL"
    if any(x in ln for x in ["GASES", "OXIGENIO"]): return "GASES"
    if any(x in ln for x in ["EXAME", "IMAGEM", "RAIO", "LABOR"]): return "EXAMES"
    if "PACOTE" in ln: return "PACOTES ESPECIAIS"
    return None

def processar_fatura(arquivo):
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0, "MATERIAL ESPECIAL": 0.0,
        "MEDICAMENTOS": 0.0, "GASES": 0.0, "TAXAS": 0.0,
        "DIÁRIAS": 0.0, "HONORÁRIOS": 0.0, "EXAMES": 0.0, "PACOTES ESPECIAIS": 0.0
    }
    
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Filtro de nitidez para garantir a leitura de centavos
    _, img_bin = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY)
    texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        # PROTEÇÃO: Ignora linhas de resumo que somam valores já lidos
        if not ln or any(s in ln.upper() for s in ["TOTAL DA CONTA", "TOTAL GERAL", "SUB-TOTAL", "TOTAL DO SETOR"]): continue
        
        valor = extrair_valor_fiel(ln)
        if valor > 0:
            cat = categorizar_estrito(ln) # Função corrigida para evitar o NameError
            if cat:
                resumo[cat] += valor
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Oficial", layout="wide")
st.title("🛡️ Auditar Fácil - Batimento Suja vs. Limpa")

c1, c2 = st.columns(2)
with c1: f_suja = st.file_uploader("📂 Conta Hospitalar (SUJA)", key="suja")
with c2: f_limpa = st.file_uploader("📂 Relatório RAH (LIMPA)", key="limpa")

if f_suja and f_limpa:
    suja = processar_fatura(f_suja)
    limpa = processar_fatura(f_limpa)
    
    st.subheader("📊 Confronto de Glosas")
    tabela = []
    for cat in suja.keys():
        v_s, v_l = suja[cat], limpa[cat]
        if v_s > 0 or v_l > 0:
            tabela.append({
                "Categoria": cat, 
                "Suja (R$)": f"{v_s:,.2f}", 
                "Limpa (R$)": f"{v_l:,.2f}", 
                "Glosa (R$)": f"{(v_s - v_l):,.2f}"
            })
    
    st.table(tabela)
    ts, tl = sum(suja.values()), sum(limpa.values())
    st.metric("GLOSA TOTAL", f"R$ {(ts - tl):,.2f}")
    
