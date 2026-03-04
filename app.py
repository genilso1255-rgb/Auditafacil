import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import pdf2image
import re

# Configuração da página
st.set_page_config(page_title="AuditaFácil - Auditoria Hospitalar", layout="wide")

# Funções de Login
def verificar_login(cpf, senha):
    return cpf == "123" and senha == "123"

if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🌐 AuditaFácil")
    cpf = st.text_input("👤 CPF (apenas números)")
    senha = st.text_input("🔑 Senha", type="password")
    if st.button("Acessar Sistema"):
        if verificar_login(cpf, senha):
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")
else:
    st.title("📄 Auditoria de Contas Hospitalares")
    
    if st.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    arquivos = st.file_uploader("Selecione as fotos ou PDFs das contas", 
                                type=['pdf', 'jpg', 'png', 'jpeg'], 
                                accept_multiple_files=True)

    if arquivos:
        dados_totais = []
        
        for arq in arquivos:
            st.info(f"Processando: {arq.name}...")
            paginas = []
            
            if arq.type == "application/pdf":
                paginas = pdf2image.convert_from_bytes(arq.read())
            else:
                paginas = [Image.open(arq)]

            for pg in paginas:
                # O motor Tesseract agora está instalado via packages.txt
                texto = pytesseract.image_to_string(pg, lang='por')
                
                # Regras de busca de valores (Regex)
                padrao_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
                valores = re.findall(padrao_valor, texto)
                
                for val in valores:
                    valor_limpo = float(val.replace('.', '').replace(',', '.'))
                    
                    # Classificação simples baseada em palavras-chave
                    categoria = "OUTROS"
                    if any(x in texto.upper() for x in ["HONORARIO", "MEDICO", "VISITA"]):
                        categoria = "HONORÁRIOS"
                    elif any(x in texto.upper() for x in ["MATERIA", "FIOS", "DESCARTAVEL"]):
                        categoria = "MATERIAL"
                    elif any(x in texto.upper() for x in ["DIARIA", "TAXA", "GASES"]):
                        categoria = "DIÁRIAS/TAXAS"

                    dados_totais.append({"Arquivo": arq.name, "Categoria": categoria, "Total": valor_limpo})

        if dados_totais:
            df = pd.DataFrame(dados_totais)
            # Agrupa por categoria para não travar a visualização
            df_resumo = df.groupby(['Arquivo', 'Categoria'])['Total'].sum().reset_index()
            
            st.subheader("📊 Resultado da Auditoria Consolidada")
            # Exibição segura que evita o ValueError:
            st.dataframe(df_resumo.style.format({"Total": "R$ {:.2f}"}))
            
            valor_final = df_resumo['Total'].sum()
            st.success(f"### Valor Total Identificado: R$ {valor_final:,.2f}")
        else:
            st.warning("Nenhum valor identificado. Verifique a nitidez da imagem.")
            
