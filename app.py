import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

# Função Universal para capturar valores em qualquer lugar da linha
def capturar_valor_financeiro(texto):
    # Regex que ignora códigos de procedimento e foca no valor final (moeda)
    padrao = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    matches = re.findall(padrao, texto)
    if matches:
        # No 99% das contas, o valor total do item é o último da direita
        valor_limpo = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_limpo)
        except: return 0.0
    return 0.0

def classificar_categoria_universal(linha):
    ln = linha.upper()
    # Mapeamento por radicais (funciona para qualquer hospital/operadora)
    if any(x in ln for x in ["HONOR", "CIRURG", "MEDIC", "ASSIST", "SISTEMA", "PROCED"]): return "HONORÁRIOS"
    if any(x in ln for x in ["MATERIA", "DESCART", "FIOS", "AGULHA", "SERINGA", "LUVAS"]): return "MATERIAIS"
    if any(x in ln for x in ["MEDICAM", "SORO", "SOLUCAO", "DIETA", "AMPO"]): return "MEDICAMENTOS"
    if any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "APART", "ENFERM"]): return "DIÁRIAS"
    if any(x in ln for x in ["TAXA", "SALA", "EQUIP", "ALUGU", "USO"]): return "TAXAS"
    if any(x in ln for x in ["EXAME", "LABOR", "IMAGEM", "RAIO", "TOMO", "RESON"]): return "EXAMES"
    if any(x in ln for x in ["OPME", "ORTESE", "PROTESE", "ESPECIAL"]): return "OPME/MAT. ESPECIAL"
    if any(x in ln for x in ["GAS", "OXIG", "NITRO"]): return "GASES MEDICINAIS"
    if "PACOTE" in ln: return "PACOTES"
    return "OUTROS/DIVERSOS"

def processar_qualquer_conta(arquivo):
    resumo = {}
    img = np.array(Image.open(arquivo).convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Pré-processamento adaptativo para qualquer qualidade de foto
    img_final = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    texto = pytesseract.image_to_string(img_final, lang='por', config='--psm 6')

    for linha in texto.split('\n'):
        ln = linha.strip()
        if not ln or len(ln) < 5: continue # ignora ruídos pequenos
        
        valor = capturar_valor_financeiro(ln)
        if valor <= 0: continue
        
        categoria = classificar_categoria_universal(ln)
        resumo[categoria] = resumo.get(categoria, 0.0) + valor
            
    return resumo

# --- INTERFACE UNIVERSAL ---
st.set_page_config(page_title="Auditar Fácil - Sistema Aberto", layout="wide")
st.title("🛡️ Auditar Fácil - Motor de Auditoria Universal")
st.info("Suba qualquer conta hospitalar (Suja) e qualquer relatório (Limpo). O sistema identificará os padrões automaticamente.")

c1, c2 = st.columns(2)
with c1: f_suja = st.file_uploader("📂 Conta de Origem (SUJA)", key="u_suja")
with c2: f_limpa = st.file_uploader("📂 Resultado Auditoria (LIMPA)", key="u_limpa")

if f_suja and f_limpa:
    with st.spinner('Processando dados...'):
        suja = processar_qualquer_conta(f_suja)
        limpa = processar_qualquer_conta(f_limpa)
    
    # Criar lista única de todas as categorias encontradas nos dois documentos
    todas_categorias = sorted(list(set(list(suja.keys()) + list(limpa.keys()))))
    
    st.subheader("📊 Confronto de Valores")
    comparativo = []
    for cat in todas_categorias:
        v_s = suja.get(cat, 0.0)
        v_l = limpa.get(cat, 0.0)
        glosa = v_s - v_l
        if v_s > 0 or v_l > 0:
            comparativo.append({
                "Categoria": cat,
                "Cobrado (R$)": f"{v_s:,.2f}",
                "Liberado (R$)": f"{v_l:,.2f}",
                "Glosa (R$)": f"{max(0, glosa):,.2f}"
            })
    
    st.table(comparativo)
    
    total_suja, total_limpa = sum(suja.values()), sum(limpa.values())
    st.metric("GLOSA TOTAL", f"R$ {total_suja - total_limpa:,.2f}", delta=f"{total_suja - total_limpa:,.2f}", delta_color="inverse")
    
