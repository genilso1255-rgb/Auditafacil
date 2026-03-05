import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_fiel(linha):
    # Procura o valor financeiro na ponta direita da linha (ex: 75.575,47)
    matches = re.findall(r'(\d[\d\.]*,\d{2})', linha)
    if matches:
        v_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def categorizar_conforme_usuario(linha):
    ln = linha.upper()
    
    # 🛑 BLOQUEIO DE TÍTULOS (Negritos que não devem somar)
    # Se a linha contiver esses termos EXATOS de grupo, ela é descartada
    bloqueios = ["632 -", "652 -", "658 -", "TOTAL DA CONTA", "SUB-TOTAL", "SETOR / GRUPO"]
    if any(b in ln for b in bloqueios):
        return None

    # 📋 CATEGORIAS OFICIAIS (Baseado nos seus prints)
    if any(x in ln for x in ["HONOR", "PROCED", "NARIZ", "CABECA", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "ESQUELET"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIAL", "FIOS", "DESCART", "AGULHA", "LUVAS", "GAZE", "HOSPITALARES"]): return "MATERIAL DESCARTÁVEL"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "DIETA", "AMPO", "COMUM", "RESTRITO"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMIN", "USO"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "APARTAMENTO"]): return "DIÁRIAS"
    if any(x in ln for x in ["ORTESE", "PROTESE", "OPME", "ESPECIAL", "SINTESE"]): return "MATERIAL ESPECIAL"
    if any(x in ln for x in ["GASES", "OXIGENIO"]): return "GASES"
    if any(x in ln for x in ["EXAME", "IMAGEM", "RAIO", "LABOR"]): return "EXAMES"
    if "PACOTE" in ln: return "PACOTES ESPECIAIS"
    
    return None

def processar_fatura(arquivo):
    resumo = {k: 0.0 for k in [
        "HONORÁRIOS", "MATERIAL DESCARTÁVEL", "MEDICAMENTOS", 
        "TAXAS", "DIÁRIAS", "MATERIAL ESPECIAL", 
        "GASES", "EXAMES", "PACOTES ESPECIAIS"
    ]}
    
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Filtro para destacar números pequenos e centavos
    img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        if not ln: continue
        
        cat = categorizar_conforme_usuario(ln)
        if cat: 
            valor = extrair_valor_fiel(ln)
            if valor > 0:
                resumo[cat] += valor
            
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Pro", layout="wide")
st.title("🛡️ Auditar Fácil - Batimento de Precisão")

c1, c2 = st.columns(2)
with c1: f_suja = st.file_uploader("📂 Conta Hospitalar (SUJA)", key="suja")
with c2: f_limpa = st.file_uploader("📂 Relatório RAH (LIMPA)", key="limpa")

if f_suja and f_limpa:
    with st.spinner('Calculando...'):
        dados_s = processar_fatura(f_suja)
        dados_l = processar_fatura(f_limpa)
    
    st.subheader("📊 Resultado do Batimento")
    tabela = []
    for cat in dados_s.keys():
        s, l = dados_s[cat], dados_l[cat]
        if s > 0 or l > 0:
            tabela.append({
                "Categoria": cat,
                "Conta Suja (R$)": f"{s:,.2f}",
                "Conta Limpa (R$)": f"{l:,.2f}",
                "Glosa (R$)": f"{(s-l):,.2f}"
            })
    
    st.table(tabela)
    
    total_s, total_l = sum(dados_s.values()), sum(dados_l.values())
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("SOMA TOTAL SUJA", f"R$ {total_s:,.2f}")
    m2.metric("SOMA TOTAL LIMPA", f"R$ {total_l:,.2f}")
    m3.metric("GLOSA TOTAL FINAL", f"R$ {(total_s - total_l):,.2f}")
    
