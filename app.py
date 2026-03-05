import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_fiel(linha):
    # Busca o último valor financeiro à direita da linha (padrão de faturas e RAH)
    matches = re.findall(r'(\d[\d\.]*,\d{2})', linha)
    if matches:
        v_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(v_str)
        except: return 0.0
    return 0.0

def categorizar_conforme_usuario(linha):
    ln = linha.upper()
    
    # 🛑 TRAVA DE SEGURANÇA: Ignorar títulos de setores e subtotais (Negritos)
    # Essas linhas NÃO devem entrar na soma para não duplicar os itens
    bloqueios = [
        "CENTRO CIRURGICO", "CTI ADULTO", "APARTAMENTO", 
        "UNID", "SUB-TOTAL", "TOTAL DO SETOR", "TOTAL GERAL", 
        "VALOR TOTAL", "TOTAL DA CONTA"
    ]
    if any(b in ln for b in bloqueios):
        return None

    # 📋 AS 9 CATEGORIAS EXATAS QUE VOCÊ PASSOU:
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

def processar_auditoria(arquivo):
    # Inicializa o resumo apenas com as suas 9 categorias
    resumo = {k: 0.0 for k in [
        "HONORÁRIOS", "MATERIAL DESCARTÁVEL", "MEDICAMENTOS", 
        "TAXAS", "DIÁRIAS", "MATERIAL ESPECIAL", 
        "GASES", "EXAMES", "PACOTES ESPECIAIS"
    ]}
    
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Binarização para limpar ruídos de carimbo e fundo
    img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        if not ln: continue
        
        # Primeiro verificamos a categoria (e se a linha deve ser bloqueada)
        cat = categorizar_conforme_usuario(ln)
        
        if cat: # Só entra aqui se for uma categoria válida e NÃO for título/negrito
            valor = extrair_valor_fiel(ln)
            if valor > 0:
                resumo[cat] += valor
            
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Sistema de Confronto", layout="wide")
st.title("🛡️ Auditar Fácil - Batimento Suja vs. Limpa")

col1, col2 = st.columns(2)
with col1:
    f_suja = st.file_uploader("📂 Subir Conta Hospitalar (SUJA)", key="u_suja")
with col2:
    f_limpa = st.file_uploader("📂 Subir Relatório RAH (LIMPA)", key="u_limpa")

if f_suja and f_limpa:
    with st.spinner('Processando auditoria...'):
        dados_suja = processar_auditoria(f_suja)
        dados_limpa = processar_auditoria(f_limpa)
    
    st.subheader("📊 Batimento por Categoria")
    
    tabela_confronto = []
    for cat in dados_suja.keys():
        v_suja = dados_suja[cat]
        v_limpa = dados_limpa[cat]
        if v_suja > 0 or v_limpa > 0:
            tabela_confronto.append({
                "Categoria": cat,
                "Conta Suja (R$)": f"{v_suja:,.2f}",
                "Conta Limpa (R$)": f"{v_limpa:,.2f}",
                "Glosa (R$)": f"{(v_suja - v_limpa):,.2f}"
            })
    
    st.table(tabela_confronto)
    
    # Totais Finais
    ts = sum(dados_suja.values())
    tl = sum(dados_limpa.values())
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL CONTA SUJA", f"R$ {ts:,.2f}")
    m2.metric("TOTAL CONTA LIMPA", f"R$ {tl:,.2f}")
    m3.metric("GLOSA TOTAL IDENTIFICADA", f"R$ {(ts - tl):,.2f}")
    
