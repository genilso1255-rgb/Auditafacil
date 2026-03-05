import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

# Habilita suporte a arquivos HEIC (fotos de iPhone)
register_heif_opener()

def processar_auditar_facil_final(arquivos):
    # GAVETAS DEFINIDAS PELO USUÁRIO (O DNA DO SISTEMA)
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0, # Inclui Materiais + Fios Cirúrgicos
        "MATERIAL ESPECIAL": 0.0,    # OPME
        "MEDICAMENTOS": 0.0,         # Inclui Remédios + Dietas/Nutrição
        "GASES": 0.0,                # Apenas Gases Medicinais
        "TAXAS": 0.0,                # Sala, Equipamentos e Administrativas
        "DIÁRIAS": 0.0,              # Estadia/Hospitalização
        "HONORÁRIOS": 0.0,           # Anatomia (Cabeça, Pescoço, Olhos, etc)
        "EXAMES": 0.0,               # Diagnósticos, Imagem e Laboratório
        "PACOTES ESPECIAIS": 0.0     # Itens de Pacote Fechado
    }

    # Títulos de setores que devem ser IGNORADOS (para não duplicar a soma)
    setores_ignorar = [
        "CENTRO CIRURGICO", "APARTAMENTO", "CTI ADULTO", "RAIO X", 
        "UNID 02", "UNID 04B", "RESUMO DA CONTA", "TOTAL DO SETOR"
    ]

    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        
        # Pré-processamento para limpar carimbos e focar no texto impresso
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, img_bin = cv2.threshold(gray, 125, 255, cv2.THRESH_BINARY)
        
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            
            # 1. VERIFICAÇÃO DE TÍTULOS: Se a linha for um setor em negrito, pula
            if any(setor in ln for setor in setores_ignorar):
                continue
            
            # 2. EXTRAÇÃO DE VALOR: Pega o último valor monetário da linha
            matches = re.findall(r'(\d+[\.,]\d{2})', ln)
            if not matches:
                continue
                
            try:
                valor = float(matches[-1].replace('.', '').replace(',', '.'))
            except:
                continue

            # 3. CLASSIFICAÇÃO NAS GAVETAS (REGRAS PRÁTICAS)
            
            # GASES (Isolado)
            if any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPRIMIDO"]):
                resumo["GASES"] += valor
            
            # HONORÁRIOS (Termos anatômicos e sistemas)
            elif any(x in ln for x in ["CABECA", "PESCOCO", "SISTEMA", "NARIZ", "OLHOS", "MUSCULAR", "NERVOSO", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor

            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS CIR", "MATERIAIS HOSPITALARES", "DESCARTAVEL", "AGULHA", "LUVAS"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "OPME", "ESPECIAL"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # MEDICAMENTOS (Medicamentos + Dietas)
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "NUTRICAO", "SORO", "AMPOLA"]):
                resumo["MEDICAMENTOS"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO"]):
                resumo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA"]):
                resumo["DIÁRIAS"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORATORIO", "TOMOGRAFIA"]):
                resumo["EXAMES"] += valor

            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Auditar Fácil", layout="wide")
st.title("🛡️ Auditar Fácil - Versão Final 2026")
st.markdown("---")

uploads = st.file_uploader("Arraste as fotos da conta (HEIC, JPG, PNG) aqui", accept_multiple_files=True)

if uploads:
    with st.spinner('Processando... ignorando títulos e somando categorias puras.'):
        resultado = processar_auditar_facil_final(uploads)
    
    st.subheader("📊 Resumo da Conta Suja Consolidade")
    
    # Exibe apenas categorias que possuem valor acumulado
    col1, col2 = st.columns([2, 1])
    
    with col1:
        for cat, total in resultado.items():
            if total > 0:
                st.write(f"✅ **{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("Total Bruto da Conta", f"R$ {total_geral:,.2f}")
        st.success("Títulos de setores (Centro Cirúrgico, etc.) foram filtrados com sucesso.")

    st.divider()
    st.info("Este resumo está pronto para ser confrontado com o Relatório de Auditoria (RAH).")
    
