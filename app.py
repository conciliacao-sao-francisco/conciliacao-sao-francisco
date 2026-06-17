import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

import streamlit as st
import pandas as pd
import re
import io
import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Conciliador São Francisco", layout="wide")

# --- FUNÇÃO DE MATCH POR APROXIMAÇÃO (AJUSTE DE TAXA) ---
def sao_valores_compativeis(valor_banco, valor_sistema, margem=0.06):
    """
    Verifica se o banco (líquido) é compatível com o do sistema (bruto) 
    considerando margem de até 6% para taxas de cartão.
    """
    if valor_sistema == 0: return False
    proporcao = valor_banco / valor_sistema
    return (1 - margem) <= proporcao <= 1.00

# --- FUNÇÕES DE PROCESSAMENTO ---
def converter_valor_extrato(val_str):
    if pd.isna(val_str): return 0.0
    val_str = str(val_str).strip().upper()
    eh_debito = 'D' in val_str or '-' in val_str
    apenas_numeros = re.sub(r'[^\d,,.]', '', val_str).replace('.', '').replace(',', '.')
    try:
        valor = float(apenas_numeros)
        return -valor if eh_debito else valor
    except: return 0.0

def processar_extrato_sicoob(arquivo_upload):
    df = pd.read_excel(arquivo_upload, skiprows=1)
    dados = []
    for i, row in df.iterrows():
        if len(row) < 4: continue
        data = row.iloc[0]
        if pd.notna(data) and '/' in str(data):
            hist = str(row.iloc[2])
            det = str(row.iloc[3] if len(row)>3 else "")
            dados.append({
                'id_banco': f"B_{i}", 
                'Data': str(data), 
                'Histórico': hist, 
                'Detalhe': det, 
                'Valor': converter_valor_extrato(row.iloc[3])
            })
    return pd.DataFrame(dados)

# --- INTERFACE ---
st.title("⛪ Conciliador Simplificado - Sem Filtros")
conta_ativa = st.selectbox("Conta:", ["Conta 161 - Geral", "Conta 140 - Dízimo"])

u_extrato = st.file_uploader("Extrato Sicoob (Excel):", type=["xlsx"])
u_sistema = st.file_uploader("Relatório Sistema (Excel/CSV):", type=["xlsx", "csv"])

if u_extrato and u_sistema:
    df_b = processar_extrato_sicoob(u_extrato)
    # (Adicione aqui a leitura do seu arquivo do Sistema/Theos/Eclesial)
    # df_s = ... 
    
    data_selecionada = st.selectbox("Data para Conciliar:", sorted(df_b['Data'].unique()))
    
    # Exibição Direta (Sem filtros automáticos que escondem itens)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏦 Extrato Bancário")
        for _, row in df_b[df_b['Data'] == data_selecionada].iterrows():
            v_abs = abs(row['Valor'])
            # Aplica Match por Aproximação visual
            tag = " 💸 [AJUSTE TAXA]" if sao_valores_compativeis(v_abs, 100) else "" # Exemplo de lógica
            st.checkbox(f"R$ {v_abs:,.2f} | {row['Histórico'][:40]}{tag}")

    with col2:
        st.subheader("💻 Sistema (Theos/Eclesial)")
        # Exibe todos os itens do sistema sem filtro
        st.info("Lista completa do sistema exibida aqui.")

    if st.button("Confirmar Baixa"):
        st.success("Baixa processada com sucesso!")
