import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def limpar_e_extrair_valor(linha):
    # Remove qualquer caractere que não seja número, ponto ou vírgula no final da linha
    # Isso evita que códigos de barras ou datas sujem o valor financeiro
    partes = linha.split()
    if not partes: return 0.0
    
    # Procuramos o valor financeiro da direita para a esquerda (padrão de fatura)
    for p in reversed(partes):
        # Procura o padrão 0.000,00 ou 00,00
        match = re.search(r'(\d[\d\.]*,\d{2})', p)
        if match:
            v_str = match.group(1).replace('.', '').replace(',', '.')
            try: return float(v_str)
            except: continue
    return 0.0

def categorizar_universal(linha):
    ln = linha.upper()
    # Mapeamento por radicais lógicos - funciona em qualquer hospital
    if any(x in ln for x in ["HONOR", "PROCED", "CIRURG", "SISTEMA", "NARIZ", "CABECA", "OLHOS"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIAIS", "MATERIAL", "FIOS", "DESCART", "AGULHA"]): return "MATERIAL DESCARTÁVEL"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "AMPO", "DIETA"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "USO"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA"]): return "DIÁRIAS"
    if any(x in ln for x in ["ORTESE", "PROTESE", "OPME", "ESPECIAL", "SINTESE"]): return "MATERIAL ESPECIAL"
    if any(x in ln for x in ["GASES", "OXIGENIO"]): return "GASES"
    if any(x in ln for x in ["EXAME", "IMAGEM", "RAIO", "LABOR"]): return "EXAMES"
    if "PACOTE" in ln: return "PACOTES ESPECIAIS"
    return None

def motor_processamento(arquivo):
    resumo = {k: 0.0 for k in ["MATERIAL DESCARTÁVEL", "MATERIAL ESPECIAL", "MEDICAMENTOS", "GASES", "TAXAS", "DIÁRIAS", "HONORÁRIOS", "EXAMES", "PACOTES ESPECIAIS"]}
    
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Melhora o contraste para ler números pequenos e carimbos
    img_proc = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_proc, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        # PROTEÇÃO: Ignora rodapés e totais para não somar o valor da conta duas vezes
        if not ln or any(s in ln.upper() for s in ["TOTAL DA CONTA", "TOTAL GERAL", "SUB-TOTAL"]): continue
        
        valor = limpar_e_extrair_valor(ln)
        if valor > 0:
            cat = categorizar_universal(ln)
            if cat: resumo[cat] += valor
            
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Universal", layout="wide")
st.title("🛡️ Auditar Fácil - Batimento Suja vs. Limpa")

c1, c2 = st.columns(2)
with c1: f_suja = st.file_uploader("📂 Conta Hospitalar (SUJA)", key="s")
with c2: f_limpa = st.file_uploader("📂 Relatório RAH (LIMPA)", key="l")

if f_suja and f_limpa:
    dados_suja = motor_processamento(f_suja)
    dados_limpa = motor_processamento(f_limpa)
    
    st.subheader("📊 Batimento de Glosas")
    tabela = []
    for cat in dados_suja.keys():
        s, l = dados_suja[cat], dados_limpa[cat]
        if s > 0 or l > 0:
            tabela.append({"Categoria": cat, "Suja (R$)": f"{s:,.2f}", "Limpa (R$)": f"{l:,.2f}", "Glosa (R$)": f"{(s-l):,.2f}"})
    
    st.table(tabela)
    ts, tl = sum(dados_suja.values()), sum(dados_limpa.values())
    st.metric("GLOSA FINAL CALCULADA", f"R$ {(ts - tl):,.2f}")
    
