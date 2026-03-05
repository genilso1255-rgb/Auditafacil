import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_universal(linha):
    # Procura o valor financeiro na extrema direita, ignorando textos no meio
    matches = re.findall(r'(\d[\d\.]*,\d{2})', linha)
    if matches:
        # Pega sempre o último valor (padrão de fatura/RAH)
        v_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def categorizar_por_radical(linha):
    ln = linha.upper()
    # Radicais que funcionam em qualquer relatório hospitalar
    if any(x in ln for x in ["HONOR", "PROCED", "NARIZ", "CABECA", "SISTEMA", "OLHOS", "CIRURG"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIAL", "FIOS", "DESCART", "AGULHA", "LUVAS"]): return "MATERIAL DESCARTÁVEL"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "DIETA"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "USO"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "APART"]): return "DIÁRIAS"
    if any(x in ln for x in ["ORTESE", "PROTESE", "OPME", "ESPECIAL", "SINTESE"]): return "MATERIAL ESPECIAL"
    if any(x in ln for x in ["GASES", "OXIGENIO"]): return "GASES"
    if any(x in ln for x in ["EXAME", "IMAGEM", "RAIO", "LABOR"]): return "EXAMES"
    if "PACOTE" in ln: return "PACOTES ESPECIAIS"
    return None

def processar_auditoria(arquivo):
    resumo = {k: 0.0 for k in ["MATERIAL DESCARTÁVEL", "MATERIAL ESPECIAL", "MEDICAMENTOS", "GASES", "TAXAS", "DIÁRIAS", "HONORÁRIOS", "EXAMES", "PACOTES ESPECIAIS"]}
    
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Threshold adaptativo para lidar com fotos de celular (sombras e brilho)
    img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        # FILTRO CRÍTICO: Ignora linhas que são resumos de grupos para não duplicar valores
        if not ln or any(s in ln.upper() for s in ["TOTAL DA CONTA", "SUB-TOTAL", "TOTAL DO SETOR", "TOTAL GERAL"]): continue
        
        valor = extrair_valor_universal(ln)
        if valor > 0:
            cat = categorizar_por_radical(ln)
            if cat: resumo[cat] += valor
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Pro", layout="wide")
st.title("🛡️ Auditoria Dinâmica - Qualquer Conta")

c1, c2 = st.columns(2)
with c1: f_suja = st.file_uploader("📂 Conta Hospitalar (SUJA)", key="s")
with c2: f_limpa = st.file_uploader("📂 Relatório RAH (LIMPA)", key="l")

if f_suja and f_limpa:
    res_s = processar_auditoria(f_suja)
    res_l = processar_auditoria(f_limpa)
    
    st.subheader("📊 Confronto de Valores")
    tab = []
    for cat in res_s.keys():
        s, l = res_s[cat], res_l[cat]
        if s > 0 or l > 0:
            tab.append({"Categoria": cat, "Cobrado (R$)": f"{s:,.2f}", "Liberado (R$)": f"{l:,.2f}", "Glosa (R$)": f"{(s-l):,.2f}"})
    
    st.table(tab)
    
    total_s, total_l = sum(res_s.values()), sum(res_l.values())
    st.metric("GLOSA TOTAL FINAL", f"R$ {(total_s - total_l):,.2f}")
    
