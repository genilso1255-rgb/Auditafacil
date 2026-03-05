import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="AuditaFácil", layout="centered")

# --- ESTILO CSS (Para manter o visual das fotos) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1 { color: white; font-family: 'sans-serif'; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS TESTE (Simulado) ---
# Aqui criamos o seu usuário ADN para testes
usuarios_db = {
    "12345678901": {"senha": "teste123", "perfil": "ADN"}, # CPF Teste
    "00000000000": {"senha": "admin", "perfil": "Supervisor"}
}

# --- FUNÇÕES DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

def autenticar(cpf, senha):
    if cpf in usuarios_db and usuarios_db[cpf]["senha"] == senha:
        st.session_state.logado = True
        st.session_state.perfil = usuarios_db[cpf]["perfil"]
        st.rerun()
    else:
        st.error("CPF ou Senha incorretos.")

# --- TELA DE LOGIN (Igual à foto 1000648938) ---
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center;'>🌐 AuditaFácil</h1>", unsafe_allow_html=True)
    
    with st.container():
        cpf_input = st.text_input("👤 CPF (apenas números)")
        senha_input = st.text_input("🔑 Senha", type="password")
        
        if st.button("Acessar Sistema"):
            autenticar(cpf_input, senha_input)
        
        st.markdown("[Esqueceu a senha? Clique aqui para recuperar](#)")

# --- INTERFACE INTERNA (Igual à foto 1000648940) ---
else:
    st.markdown("### 📑 Auditoria de Contas Hospitalares")
    
    # Mensagem de instrução do sistema
    st.info("Agora você pode selecionar vários arquivos (PDF ou Imagem) segurando a tecla Ctrl ou pressionando cada um no celular.")

    # Upload de arquivos
    arquivos = st.file_uploader("Selecione as fotos ou PDFs das contas", 
                               accept_multiple_files=True, 
                               type=['png', 'jpg', 'jpeg', 'pdf'])
    
    # Seção Administrativa (Visível apenas para ADN/Supervisor)
    if st.session_state.perfil in ["ADN", "Supervisor"]:
        with st.sidebar:
            st.write(f"**Nível de Acesso:** {st.session_state.perfil}")
            st.write("---")
            if st.button("Painel de Gestão (ADN)"):
                st.write("Aqui você poderá gerenciar códigos TUSS e usuários.")
    
    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- ESPAÇO PARA O RESULTADO (Referência da foto 1000648794) ---
    if arquivos:
        st.success(f"{len(arquivos)} arquivo(s) carregado(s). Iniciando leitura...")
        # A lógica de OCR e a tabela de resumo (Cobrado/Glosado/Liberado) 
        # entrarão aqui após os cálculos baterem.
        
