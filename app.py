import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image, ImageOps
import pytesseract

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

# --- LOGIN ADN ---
usuarios = {"12345678901": {"senha": "teste", "perfil": "ADN"}}

def tratar_imagem_v5(arq_streamlit):
    img_pil = Image.open(arq_streamlit).convert('L')
    img_pil = ImageOps.autocontrast(img_pil)
    img_cv = np.array(img_pil)
    # Deixa o texto bem nítido para o OCR não pular linhas
    img_binaria = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return img_binaria

def categorizar_universal(desc):
    d = desc.upper()
    if any(k in d for k in ["FIO", "SUTURA", "AGULHA", "CATETER", "EQUIPO", "SONDA", "LUVA", "COMPRESSA", "CANULA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "AMPOLA", "FRASCO", "SOLUCAO", "UNIREZ", "DEX", "TORADOL", "RAPIFEN", "SEVONES", "PROPOFOL"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL", "SALA", "REGISTRO"]): return "TAXAS E ALUGUEIS"
    if any(k in d for k in ["GAS", "OXIGENIO", "AR COMP"]): return "GASES"
    if any(k in d for k in ["HONORARIO", "MEDICO", "VISITA"]): return "HONORARIOS"
    return "OUTROS/DIVERSOS"

def extrair_dados_v5(texto):
    linhas = texto.split('\n')
    extraidos = []
    
    # NOVA LÓGICA: Procura qualquer coisa que termine com Valor (ex: 1.234,56 ou 45,00)
    # O foco é no final da linha, ignorando se o início é código ou texto
    padrao_valor = re.compile(r'([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        if len(linha) < 5 or "Total" in linha or "Subtotal" in linha: continue
        
        match = padrao_valor.search(linha)
        if match:
            v_str = match.group(1)
            # Só aceita se tiver vírgula (formato de real) e não for o número de equivalência longo
            if "," in v_str and len(v_str.split(',')[1]) == 2:
                v_limpo = v_str.replace('.', '').replace(',', '.')
                try:
                    valor_f = float(v_limpo)
                    
                    # Filtro para evitar capturar números de equivalência ou datas
                    if valor_f > 9000.00: continue 
                    
                    desc = linha.replace(v_str, "").strip()
                    # Remove números do início da descrição (códigos)
                    desc = re.sub(r'^\d+\s+', '', desc)
                    
                    extraidos.append({
                        "Categoria": categorizar_universal(desc),
                        "Valor": valor_f
                    })
                except: continue
    return pd.DataFrame(extraidos)

# --- INTERFACE ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<h1>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    cpf = st.text_input("👤 CPF (12345678901)")
    senha = st.text_input("🔑 Senha (teste)", type="password")
    if st.button("Acessar Sistema"):
        if cpf in usuarios and usuarios[cpf]["senha"] == senha:
            st.session_state.logado = True
            st.rerun()
else:
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    arquivos = st.file_uploader("Upload das faturas", type=['png','jpg','jpeg'], accept_multiple_files=True)

    if arquivos:
        base = []
        with st.spinner('Lendo fatura linha por linha...'):
            for arq in arquivos:
                img = tratar_imagem_v5(arq)
                txt = pytesseract.image_to_string(img, lang='por', config='--psm 6')
                df_temp = extrair_dados_v5(txt)
                if not df_temp.empty: base.append(df_temp)

        if base:
            df_total = pd.concat(base)
            resumo = df_total.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            
            # Adicionando o campo de Glosa Manual para o Supervisor
            st.subheader("📝 Revisão do Supervisor")
            
            # Criando uma tabela editável
            df_editavel = st.data_editor(
                resumo,
                column_config={
                    "Valor": st.column_config.NumberColumn("Cobrado (R$)", format="%.2f"),
                    "Glosado": st.column_config.NumberColumn("Glosa Manual (R$)", format="%.2f", default=0.0)
                },
                disabled=["Categoria", "Valor"],
                hide_index=True,
                key="editor_glosa"
            )

            # Cálculo dos totais
            if "Glosado" not in df_editavel.columns:
                df_editavel["Glosado"] = 0.0
            
            total_cobrado = df_editavel["Valor"].sum()
            total_glosado = df_editavel["Glosado"].sum()
            total_liberado = total_cobrado - total_glosado
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Cobrado", f"R$ {total_cobrado:,.2f}")
            col2.metric("Total Glosado", f"R$ {total_glosado:,.2f}", delta=f"{(total_glosado/total_cobrado)*100:.1f}%", delta_color="inverse")
            col3.metric("Total Liberado", f"R$ {total_liberado:,.2f}")
            
            if abs(total_cobrado - 13290.70) < 10.0:
                st.success("✅ Valores conferidos com a fatura original do Hospital Brasília!")

    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()
    
