import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_fiel(linha):
    # Padrão: Busca o último valor financeiro à direita da linha
    matches = re.findall(r'(\d[\d\.]*,\d{2})', linha)
    if matches:
        v_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def categorizar_estrito(linha):
    ln = linha.upper()
    
    # 🚫 TRAVA DE SEGURANÇA: Ignorar títulos de setores e subtotais (Negritos)
    # Se a linha contiver esses termos, o sistema pula para não duplicar a soma
    bloqueios = [
        "CENTRO CIRURGICO", "CTI ADULTO", "APARTAMENTO", 
        "UNID", "SUB-TOTAL", "TOTAL DO SETOR", "TOTAL GERAL", 
        "VALOR TOTAL", "TOTAL DA CONTA"
    ]
    if any(b in ln for b in bloqueios):
        return None

    # 📋 CATEGORIAS DEFINIDAS POR VOCÊ
    if any(x in ln for x in ["HONOR", "PROCED", "NARIZ", "CABECA", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "MUSCULO"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIAL", "FIOS", "DESCART", "AGULHA", "LUVAS", "GAZE"]): return "MATERIAL DESCARTÁVEL"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "DIETA", "AMPO"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "ADMIN", "USO"]): return "TAXAS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA"]): return "DIÁRIAS"
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
    # Melhora nitidez para capturar centavos e evitar erros de leitura
    img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        if not ln: continue
        
        cat = categorizar_estrito(ln)
        if cat: # Só processa se for item de linha (não título)
            valor = extrair_valor_fiel(ln)
            if valor > 0:
                resumo[cat] += valor
            
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Pro", layout="wide")
st.title("🛡️ Auditar Fácil - Confronto Automático")

c1, c2 = st.columns(2)
with c1:
    f_suja = st.file_uploader("📂 Conta Hospitalar (SUJA)", key="suja")
with c2:
    f_limpa = st.file_uploader("📂 Relatório RAH (LIMPA)", key="limpa")

if f_suja and f_limpa:
    with st.spinner('Calculando valores e glosas...'):
        suja = processar_fatura(f_suja)
        limpa = processar_fatura(f_limpa)
    
    st.subheader("📊 Resultado do Batimento")
    
    tabela = []
    for cat in suja.keys():
        v_s, v_l = suja[cat], limpa[cat]
        glosa = v_s - v_l
        if v_s > 0 or v_l > 0:
            tabela.append({
                "Categoria": cat,
                "Conta Suja (R$)": f"{v_s:,.2f}",
                "Conta Limpa (R$)": f"{v_l:,.2f}",
                "Glosa (R$)": f"{glosa:,.2f}"
            })
    
    st.table(tabela)
    
    total_suja = sum(suja.values())
    total_limpa = sum(limpa.values())
    
    st.divider()
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("SOMA TOTAL SUJA", f"R$ {total_suja:,.2f}")
    col_b.metric("SOMA TOTAL LIMPA", f"R$ {total_limpa:,.2f}")
    col_c.metric("GLOSA TOTAL FINAL", f"R$ {(total_suja - total_limpa):,.2f}", delta_color="inverse")
    
