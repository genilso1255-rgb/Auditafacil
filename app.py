import streamlit as st
import pandas as pd
import numpy as np
import cv2
import re
from PIL import Image
import pytesseract

# --- 1. CONFIGURAÇÕES TÉCNICAS E ESTILO ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

# CSS para manter o layout escuro e fiel às suas fotos
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2127; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    label { color: white !important; }
    .stTable { background-color: #1e2127; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DATOS DE TESTE (ADN) ---
usuarios = {
    "12345678901": {"senha": "teste", "perfil": "ADN"},
}

# --- 3. FUNÇÕES DE PROCESSAMENTO "GOOGLE LENS" (LÓGICA LIMPA) ---

def limpar_imagem(imagem_pil):
    """ Remove rabiscos de caneta e mantém apenas o texto impresso (preto) """
    img = cv2.cvtColor(np.array(imagem_pil), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Filtro para manter apenas tons muito escuros (texto impresso)
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 90])
    mask = cv2.inrange(hsv, lower_black, upper_black)
    return mask

def categorizar_por_texto(descricao):
    """ Regras de negócio para separar os itens nas gavetas certas """
    d = descricao.upper()
    if any(k in d for k in ["FIO", "SUTURA", "AGULHA", "CATETER", "EQUIPO", "SONDA", "CANETA"]): return "MATERIAL"
    if any(k in d for k in ["DIPIRONA", "DIETA", "ENTERAL", "AMPOLA", "FRASCO", "UNIREZ", "SOLUCAO"]): return "MEDICAMENTOS"
    if "DIARIA" in d: return "DIARIA DE ENFERMARIA"
    if any(k in d for k in ["TAXA", "ADMISSAC", "ALUGUEL"]): return "TAXAS E ALUGUEIS"
    if "GAS" in d or "OXIGENIO" in d: return "GASES"
    if "EXAME" in d: return "EXAMES"
    return "OUTROS/DIVERSOS"

def extrair_dados_fatura(texto):
    """ Busca códigos de 8 a 12 dígitos e valores no final da linha """
    linhas = texto.split('\n')
    extraidos = []
    # Regex flexível: Código (8-12) + Descrição + Valor (R$ 0.000,00)
    padrao = re.compile(r'(\d{8,12})\s+(.*?)\s+([\d\.,]+)$')

    for linha in linhas:
        linha = linha.strip()
        if not linha: continue
        
        match = padrao.search(linha)
        if match:
            codigo, desc, valor_str = match.groups()
            # Converte valor "1.234,56" para float 1234.56
            valor = float(valor_str.replace('.', '').replace(',', '.'))
            extraidos.append({
                "Código": codigo,
                "Descrição": desc,
                "Categoria": categorizar_por_texto(desc),
                "Valor": valor
            })
    return pd.DataFrame(extraidos)

# --- 4. CONTROLE DE ACESSO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    with st.container():
        cpf_input = st.text_input("👤 CPF (apenas números)")
        senha_input = st.text_input("🔑 Senha", type="password")
        if st.button("Acessar Sistema"):
            if cpf_input in usuarios and usuarios[cpf_input]["senha"] == senha_input:
                st.session_state.logado = True
                st.session_state.perfil = usuarios[cpf_input]["perfil"]
                st.rerun()
            else:
                st.error("CPF ou Senha inválidos.")
        st.markdown("<p style='text-align: center;'><a href='#'>Esqueceu a senha?</a></p>", unsafe_allow_html=True)

# --- TELA INTERNA (AUDITORIA) ---
else:
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    st.info("Selecione as fotos ou PDFs. O sistema irá ignorar rabiscos e capturar códigos de 8 a 12 dígitos.")

    arquivos = st.file_uploader("Arraste os arquivos aqui", type=['png','jpg','jpeg','pdf'], accept_multiple_files=True)

    if arquivos:
        todos_itens = []
        with st.spinner('Limpando imagem e processando OCR...'):
            for arq in arquivos:
                # Processamento de imagem
                img = Image.open(arq)
                img_processada = limpar_imagem(img)
                texto_puro = pytesseract.image_to_string(img_processada, lang='por')
                
                df_arq = extrair_dados_fatura(texto_puro)
                if not df_arq.empty:
                    todos_itens.append(df_arq)
        
        if todos_itens:
            df_final = pd.concat(todos_itens)
            
            # --- TABELA POR CATEGORIA (Modelo da sua Empresa) ---
            st.subheader("ITENS DA CONTA")
            resumo = df_final.groupby('Categoria').agg({'Valor': 'sum'}).reset_index()
            resumo['Glosado'] = 0.0  # Campo para o Auditor preencher
            resumo['Liberado'] = resumo['Valor'] - resumo['Glosado']
            
            st.table(resumo.style.format({'Valor': 'R$ {:.2f}', 'Glosado': 'R$ {:.2f}', 'Liberado': 'R$ {:.2f}'}))

            # --- RODAPÉ FINANCEIRO ---
            t_cobrado = resumo['Valor'].sum()
            t_glosado = resumo['Glosado'].sum()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Cobrado", f"R$ {t_cobrado:,.2f}")
            c2.metric("Total Glosado", f"R$ {t_glosado:,.2f}")
            c3.metric("% Glosa", f"{(t_glosado/t_cobrado)*100:.1f}%" if t_cobrado > 0 else "0%")
            c4.metric("Total Liberado", f"R$ {t_cobrado - t_glosado:,.2f}")
        else:
            st.warning("Nenhum código TUSS ou valor foi identificado. Verifique a nitidez da foto.")

    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()
        
