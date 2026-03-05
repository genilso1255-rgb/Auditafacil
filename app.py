import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

def extrair_valor(linha):
    """Extrai o último valor monetário de uma linha (Conta Suja)."""
    matches = re.findall(r'(\d+[\.,]\d{2})', linha)
    if matches:
        try:
            return float(matches[-1].replace('.', '').replace(',', '.'))
        except:
            return 0.0
    return 0.0

def processar_auditar_facil(arquivos):
    # Dicionário de soma acumulada (As gavetas que combinamos)
    resumo_sujo = {
        "MATERIAL DESCARTÁVEL": 0.0,
        "MATERIAL ESPECIAL (OPME)": 0.0,
        "MEDICAMENTOS E DIETAS": 0.0,
        "DIÁRIAS": 0.0,
        "TAXAS E GASES": 0.0,
        "EXAMES": 0.0,
        "PACOTES ESPECIAIS": 0.0,
        "OUTROS": 0.0
    }
    
    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        
        # LIMPEZA: Ignorar canetas coloridas e focar no texto impresso
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, img_bin = cv2.threshold(gray, 125, 255, cv2.THRESH_BINARY)
        
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            linha_upper = linha.upper().strip()
            valor = extrair_valor(linha_upper)
            
            if valor <= 0: continue
            
            # REGRAS DE CATEGORIZAÇÃO (As gavetas do Auditar Fácil)
            if any(x in linha_upper for x in ["FIOS", "FIO CIR", "MATER", "DESC", "AGUL", "LUV", "SERIN"]):
                resumo_sujo["MATERIAL DESCARTÁVEL"] += valor
                
            elif any(x in linha_upper for x in ["OPME", "ORTE", "PROT", "ESPEC", "SINTESE"]):
                resumo_sujo["MATERIAL ESPECIAL (OPME)"] += valor
                
            elif any(x in linha_upper for x in ["DIETA", "MEDIC", "SOLU", "AMP", "SORO", "FARMA"]):
                resumo_sujo["MEDICAMENTOS E DIETAS"] += valor
                
            elif any(x in linha_upper for x in ["DIARIA", "APART", "ENFERM", "UTI", "PERNOITE"]):
                resumo_sujo["DIÁRIAS"] += valor
                
            elif any(x in linha_upper for x in ["TAXA", "SALA", "ALUG", "GAS", "OXIG", "AR COMP"]):
                resumo_sujo["TAXAS E GASES"] += valor
                
            elif any(x in linha_upper for x in ["IMAGEM", "LABOR", "DIAGNOSTICO", "RAIO", "TOMO", "EXAME"]):
                resumo_sujo["EXAMES"] += valor
                
            elif "PACOTE" in linha_upper:
                resumo_sujo["PACOTES ESPECIAIS"] += valor
            else:
                resumo_sujo["OUTROS"] += valor
                
    return resumo_sujo

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Auditar Fácil", layout="wide")
st.title("🛡️ Auditar Fácil - 2026")
st.write("Processamento inteligente de contas hospitalares e RAH.")

uploads = st.file_uploader("Arraste as fotos da conta ou RAH aqui", accept_multiple_files=True)

if uploads:
    with st.spinner('Limpando imagem e somando categorias...'):
        dados = processar_auditar_facil(uploads)
        
    st.divider()
    
    # Exibição do Resumo
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Resumo da Conta Suja (Por Categoria)")
        # Remove categorias zeradas para não poluir
        dados_filtrados = {k: v for k, v in dados.items() if v > 0}
        st.table([{"Categoria": k, "Total Acumulado": f"R$ {v:,.2f}"} for k, v in dados_filtrados.items()])
        
    with col2:
        total_geral = sum(dados.values())
        st.metric("Total Bruto Identificado", f"R$ {total_geral:,.2f}")
        st.info("O sistema somou itens repetidos automaticamente com base na descrição.")

    # Simulação da Conta Limpa (A ser integrada com a leitura do RAH)
    st.subheader("📝 Próximo passo: Conciliação com RAH")
    st.write("O sistema detectou os grupos acima. Deseja comparar com as glosas do relatório de auditoria?")
    
