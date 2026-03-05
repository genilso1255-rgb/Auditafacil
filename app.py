import streamlit as st
import pandas as pd

# 1. Configuração que resolve o erro de upload e define o Layout
st.set_page_config(page_title="AuditaFácil", layout="centered")

# --- BANCO DE DADOS TESTE ---
# CPF: 12345678901 | Senha: teste
usuarios = {
    "12345678901": {"senha": "teste", "perfil": "ADN"},
}

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- ESTILO CSS (Fundo escuro e fontes) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    label { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- TELA DE LOGIN (Baseada na foto 1000648938) ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    
    with st.container():
        cpf = st.text_input("👤 CPF (apenas números)")
        senha = st.text_input("🔑 Senha", type="password")
        
        if st.button("Acessar Sistema"):
            if cpf in usuarios and usuarios[cpf]["senha"] == senha:
                st.session_state.logado = True
                st.session_state.user = cpf
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
        
        st.markdown("<p style='text-align: center;'><a href='#'>Esqueceu a senha?</a></p>", unsafe_allow_html=True)

# --- TELA INTERNA (Baseada nas fotos 1000648940/941) ---
else:
    st.markdown("# 📑 Auditoria de Contas Hospitalares")
    
    # Box informativo azul
    st.info("Agora você pode selecionar vários arquivos (PDF ou Imagem) segurando a tecla Ctrl ou pressionando cada um no celular.")

    # Uploader corrigido (accept_multiple_files=True é o que permite várias fotos/folhas)
    arquivos = st.file_uploader(
        "Selecione as fotos ou PDFs das contas", 
        type=["pdf", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    if arquivos:
        st.success(f"{len(arquivos)} arquivo(s) carregado(s). Iniciando leitura...")
        # Aqui entra a lógica de somar a "conta suja" com a "conta limpa"
        # que vamos construir assim que você validar este acesso.

    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # Rodapé de Administrador
    if usuarios[st.session_state.user]["perfil"] == "ADN":
        st.sidebar.warning("Modo Administrador Ativo")
        
