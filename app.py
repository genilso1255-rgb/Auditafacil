import streamlit as st
import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
from pillow_heif import register_heif_opener

# Habilita suporte para fotos de iPhone (HEIC)
register_heif_opener()

def extrair_valor_cheio(texto_linha):
    """
    Captura valores no formato brasileiro (ex: 22.831,31 ou 450,00).
    Remove pontos de milhar e converte para float decimal.
    """
    # Procura o último padrão numérico da linha que tenha vírgula (centavos)
    # Ex: 22.831,31 ou 575,81
    matches = re.findall(r'(\d[\d\.]*,\d{2})', texto_linha)
    if matches:
        valor_str = matches[-1] # Pega o último valor (coluna Total)
        # Limpeza: remove ponto de milhar e troca vírgula por ponto
        valor_limpo = valor_str.replace('.', '').replace(',', '.')
        try:
            return float(valor_limpo)
        except:
            return 0.0
    return 0.0

def processar_auditar_facil_v4(arquivos):
    # GAVETAS PURAS E ACUMULATIVAS
    resumo = {
        "MATERIAL DESCARTÁVEL": 0.0, # Materiais + Fios
        "MATERIAL ESPECIAL": 0.0,    # OPME / Órteses e Próteses
        "MEDICAMENTOS": 0.0,         # Medicamentos + Dietas
        "GASES": 0.0,                # Apenas Gases Medicinais
        "TAXAS": 0.0,                # Sala, Equipamentos e Adm
        "DIÁRIAS": 0.0,              # Estadia no Hospital/UTI
        "HONORÁRIOS": 0.0,           # Anatomia (Cabeça, Olhos, Sistemas, etc)
        "EXAMES": 0.0,               # Imagem e Laboratório
        "PACOTES ESPECIAIS": 0.0     # Itens fechados
    }

    # Títulos que devem ser ignorados para NÃO DUPLICAR a soma
    setores_ignorar = [
        "CENTRO CIRURGICO", "APARTAMENTO", "CTI ADULTO", "RAIO X", 
        "UNID 02", "UNID 04B", "RESUMO DA CONTA", "TOTAL DO SETOR",
        "VALOR TOTAL DA GUIA"
    ]

    for arq in arquivos:
        img_pil = Image.open(arq).convert('RGB')
        img_np = np.array(img_pil)
        
        # MELHORIA NA IMAGEM: Contraste para destacar números pequenos
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        img_bin = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        texto = pytesseract.image_to_string(img_bin, lang='por', config='--psm 6')

        for linha in texto.split('\n'):
            ln = linha.upper().strip()
            
            # 1. Pula se for título de setor (evita duplicidade)
            if any(setor in ln for setor in setores_ignorar):
                continue
            
            # 2. Extrai o valor corrigido (capturando os milhares)
            valor = extrair_valor_cheio(ln)
            if valor <= 0:
                continue

            # 3. Classificação por Nomes (Acúmulo Inteligente)
            
            # GASES
            if any(x in ln for x in ["GASES", "OXIGENIO", "AR COMPRIMIDO"]):
                resumo["GASES"] += valor
            
            # HONORÁRIOS (Anatomia)
            elif any(x in ln for x in ["CABECA", "PESCOCO", "SISTEMA", "NARIZ", "OLHOS", "MUSCULAR", "NERVOSO", "HONORARIO"]):
                resumo["HONORÁRIOS"] += valor

            # MATERIAL DESCARTÁVEL (Materiais + Fios)
            elif any(x in ln for x in ["FIOS CIR", "MATERIAIS HOSPITALARES", "DESCARTAVEL", "AGULHA", "LUVAS", "CATETER"]):
                resumo["MATERIAL DESCARTÁVEL"] += valor
                
            # MATERIAL ESPECIAL (OPME)
            elif any(x in ln for x in ["ORTESE", "PROTESE", "SINTESE", "MATERIAL ESPECIAL", "OPME"]):
                resumo["MATERIAL ESPECIAL"] += valor
                
            # MEDICAMENTOS (Remédios + Dietas)
            elif any(x in ln for x in ["MEDICAM", "DIETA", "SOLUCAO", "NUTRICAO", "SORO", "AMPOLA"]):
                resumo["MEDICAMENTOS"] += valor
                
            # TAXAS
            elif any(x in ln for x in ["TAXA", "ALUGUEL", "SALA", "EQUIPAMENTO"]):
                resumo["TAXAS"] += valor
                
            # DIÁRIAS
            elif any(x in ln for x in ["DIARIA", "PERNOITE", "ESTADIA", "ENFERMARIA"]):
                resumo["DIÁRIAS"] += valor
                
            # EXAMES
            elif any(x in ln for x in ["DIAGNOSTICO", "IMAGEM", "RAIO X", "LABORATORIO", "TOMOGRAFIA"]):
                resumo["EXAMES"] += valor

            # PACOTES
            elif "PACOTE" in ln:
                resumo["PACOTES ESPECIAIS"] += valor
                
    return resumo

# --- INTERFACE ---
st.set_page_config(page_title="Auditar Fácil Pro", layout="wide")
st.title("🛡️ Auditar Fácil - Versão Corrigida (Milhares)")

uploads = st.file_uploader("Suba as imagens da conta", accept_multiple_files=True)

if uploads:
    with st.spinner('Lendo valores cheios e ignorando títulos...'):
        resultado = processar_auditar_facil_v4(uploads)
    
    st.markdown("### 📊 Resultado da Auditoria (Conta Suja)")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        for cat, total in resultado.items():
            if total > 0:
                st.write(f"💵 **{cat}:** R$ {total:,.2f}")
    
    with col2:
        total_geral = sum(resultado.values())
        st.metric("Total Acumulado", f"R$ {total_geral:,.2f}")
        st.warning("Verifique se o valor acima bate com o rodapé da conta.")
        
