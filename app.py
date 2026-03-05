import pandas as pd
import streamlit as st

def categorizar_item(descricao):
    """
    Classifica o item com base nas regras de negócio da empresa.
    """
    desc = descricao.upper()
    
    # Regra: Dieta entra em Medicamentos
    if "DIETA" in desc or "ENTERAL" in desc:
        return "MEDICAMENTOS"
    
    # Regra: Fios cirúrgicos entram em Materiais
    if "FIO" in desc and "CIRURGICO" in desc:
        return "MATERIAL"
    
    # Regra: Órtese e Prótese (OPME) em Material Especial
    if "ORTESE" in desc or "PROTESE" in desc or "OPME" in desc:
        return "MATERIAL ESPECIAL"
    
    # Mapeamento padrão
    if "MEDIC" in desc or "SOLUCAO" in desc:
        return "MEDICAMENTOS"
    if "MATER" in desc or "DESCARTAVEL" in desc:
        return "MATERIAL"
    if "OXIG" in desc or "GAS" in desc:
        return "GASES"
    if "TAXA" in desc or "ALUG" in desc:
        return "TAXAS E ALUGUEIS"
    if "DIARIA" in desc:
        return "DIARIA DE ENFERMARIA"
    if "HONOR" in desc:
        return "HONORARIOS"
    
    return "OUTROS"

def gerar_relatorio_final(df_itens):
    """
    Soma os valores por categoria e calcula a glosa.
    O DF de entrada deve ter: 'Descricao', 'Cobrado', 'Glosado'
    """
    # Aplica a categorização
    df_itens['Categoria'] = df_itens['Descricao'].apply(categorizar_item)
    
    # Agrupa por categoria
    resumo = df_itens.groupby('Categoria').agg({
        'Cobrado': 'sum',
        'Glosado': 'sum'
    }).reset_index()
    
    # Calcula o Liberado (Cobrado - Glosado)
    resumo['Liberado'] = resumo['Cobrado'] - resumo['Glosado']
    
    return resumo

# --- INTERFACE STREAMLIT ---
st.title("AuditaFacil - Processamento de Contas")

# Exemplo de uso com dados manuais para teste
data = {
    'Descricao': ['FIO CIRURGICO NYLON', 'DIETA ENTERAL 1000ML', 'TAXA DE SALA', 'DIPIRONA AMPOLA'],
    'Cobrado': [150.00, 250.00, 500.00, 20.00],
    'Glosado': [0.00, 50.00, 100.00, 0.00]
}

df_teste = pd.DataFrame(data)
relatorio = gerar_relatorio_final(df_teste)

st.subheader("Itens Categorizados (Espelho da Conta)")
st.table(relatorio)

# Totais Finais
total_cobrado = relatorio['Cobrado'].sum()
total_glosado = relatorio['Glosado'].sum()
percentual_glosa = (total_glosado / total_cobrado) * 100 if total_cobrado > 0 else 0

st.markdown(f"**Total Cobrado:** R$ {total_cobrado:,.2f}")
st.markdown(f"**Total Glosado:** R$ {total_glosado:,.2f} ({percentual_glosa:.1f}%)")
st.markdown(f"**Total Liberado:** R$ {total_cobrado - total_glosado:,.2f}")
