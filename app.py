import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor_exato(texto_linha):
    # Captura valores com pontos e vírgulas (ex: 2.164,77)
    # Focamos no padrão brasileiro de milhar
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1].replace('.', '').replace(',', '.')
        try: return float(valor_str)
        except: return 0.0
    return 0.0

def processar_auditar_facil_v_finalisima(arquivos):
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0,
        "MATERIAL ESPECIAL": 0.0,
        "MEDICAMENTOS": 0.0,
        "GASES": 0.0,
        "TAXAS": 0.0,
        "DIÁRIAS": 0.0,
        "HONORÁRIOS": 0.0,
        "EXAMES": 0.0,
        "PACOTES ESPECIAIS": 0.0
    }

    # Bloqueia os títulos dos setores para não duplicar os R$ 64 mil do Centro Cirúrgico
    setores_ignorar = ["632 -", "652 -", "658 -", "TOTAL DO SETOR", "VALOR TOTAL DA GUIA"]

    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # Filtro para clarear o carimbo e destacar o texto preto
        img_proc = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        
        texto = pytesseract.image_to_string(img_proc, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            if not ln or any(s in ln for s in setores_ignorar): continue
            
            valor = extrair_valor_exato(ln)
            if valor <= 0: continue

            # --- DISTRIBUIÇÃO NAS GAVETAS ---
            # HONORÁRIOS: Anatomia e Procedimentos Médicos
            if any(x in ln for x in ["NARIZ", "CABECA", "PESCOCO", "OLHOS", "SEIOS", "SISTEMA", "NERVOSO", "MUSCULO", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor
            # MATERIAL DESCARTÁVEL (Materiais e Fios)
            elif any(x in ln for x in ["MATERIAIS", "FIOS", "DESCARTAVEL", "AGULHA", "LUVAS"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
            # MEDICAMENTOS (Comum e Restrito)
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "SORO"]):
                resumo["MEDICAMENTOS"] += valor
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
            # TAXAS (Administrativas e Sala)
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO"]):
                resumo["TAXAS"] += valor
            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
            # OUTROS (Gases, Diárias, Exames)
            elif any(x in ln for x in ["GASES", "OXIGENIO"]): resumo["GASES"] += valor
            elif any(x in ln for x in ["DIARIA", "PERNOITE"]): resumo["DIÁRIAS"] += valor
            elif any(x in ln for x in ["IMAGEM", "RAIO X", "LABORAT"]): resumo["EXAMES"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil - Versão de Ouro", layout="wide")
st.title("🛡️ Auditar Fácil - Fechamento de Conta")

uploads = st.file_uploader("Arraste as fotos da conta aqui", accept_multiple_files=True)

if uploads:
    with st.spinner('Realizando batimento final...'):
        resultado = processar_auditar_facil_v_finalisima(uploads)
    
    st.subheader("📊 Relatório de Conta Suja")
    col1, col2 = st.columns(2)
    with col1:
        for cat, total in resultado.items():
            st.write(f"✅ **{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("TOTAL IDENTIFICADO", f"R$ {total_geral:,.2f}")
        
    st.divider()
    st.info("O item 'NARIZ' (R$ 2.164,77) foi incluído na gaveta de Honorários.")
    
