import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_fiel(linha):
    # Busca o valor financeiro sempre à direita
    matches = re.findall(r'(\d[\d\.]*,\d{2})', linha)
    if matches:
        v_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def categorizar_conforme_usuario(linha):
    ln = linha.upper()
    
    # 🛑 REGRA DE OURO: Ignorar títulos de setores e subtotais (Negritos/Fortes)
    palavras_bloqueadas = ["CENTRO CIRURGICO", "CTI ADULTO", "APARTAMENTO - UNID", "SUB-TOTAL", "TOTAL DA CONTA", "TOTAL DO SETOR"]
    if any(pb in ln for pb in palavras_bloqueadas):
        return "IGNORAR"

    # Categorias solicitadas por você
    if any(x in ln for x in ["HONOR", "PROCED", "NARIZ", "CABECA", "OLHOS", "SEIOS", "SISTEMA"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIAL", "FIOS", "DESCART", "AGULHA", "LUVAS"]): return "MATERIAL DESCARTÁVEL"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "DIETA"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "USO"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA"]): return "DIÁRIAS"
    if any(x in ln for x in ["ORTESE", "PROTESE", "OPME", "ESPECIAL", "SINTESE"]): return "MATERIAL ESPECIAL"
    if any(x in ln for x in ["GASES", "OXIGENIO"]): return "GASES"
    if any(x in ln for x in ["EXAME", "IMAGEM", "RAIO", "LABOR"]): return "EXAMES"
    if "PACOTE" in ln: return "PACOTES ESPECIAIS"
    return "OUTROS"

def processar_auditoria(arquivo):
    resumo = {k: 0.0 for k in ["MATERIAL DESCARTÁVEL", "MATERIAL ESPECIAL", "MEDICAMENTOS", "GASES", "TAXAS", "DIÁRIAS", "HONORÁRIOS", "EXAMES", "PACOTES ESPECIAIS"]}
    
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        if not ln: continue
        
        cat = categorizar_conforme_usuario(ln)
        if cat == "IGNORAR": 
            continue # Aqui matamos a duplicação dos negritos
            
        valor = extrair_valor_fiel(ln)
        if valor > 0 and cat in resumo:
            resumo[cat] += valor
            
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Oficial", layout="wide")
st.title("🛡️ Auditar Fácil - Batimento Suja vs. Limpa")

c1, c2 = st.columns(2)
with c1: f_suja = st.file_uploader("📂 Conta Hospitalar (SUJA)", key="suja")
with c2: f_limpa = st.file_uploader("📂 Relatório RAH (LIMPA)", key="limpa")

if f_suja and f_limpa:
    dados_suja = processar_auditoria(f_suja)
    dados_limpa = processar_auditoria(f_limpa)
    
    st.subheader("📊 Batimento de Glosas")
    tabela = []
    for cat in dados_suja.keys():
        s, l = dados_suja[cat], dados_limpa[cat]
        if s > 0 or l > 0:
            tabela.append({"Categoria": cat, "Suja (R$)": f"{s:,.2f}", "Limpa (R$)": f"{l:,.2f}", "Glosa (R$)": f"{(s-l):,.2f}"})
    
    st.table(tabela)
    ts, tl = sum(dados_suja.values()), sum(dados_limpa.values())
    st.metric("GLOSA TOTAL", f"R$ {(ts - tl):,.2f}")
    
