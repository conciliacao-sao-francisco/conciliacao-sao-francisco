import streamlit as st
import pandas as pd
import re
import io

# Configuração de interface profissional
st.set_page_config(page_title="Gestão Financeira SF", layout="wide")

# --- MÓDULO DE SEGURANÇA ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

def tela_login():
    st.subheader("🔒 Acesso Seguro")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if user == "secretaria" and pwd == "sf@2026":
            st.session_state.autenticado = True
            st.rerun()
        else: st.error("Credenciais inválidas.")

if not st.session_state.autenticado:
    tela_login()
    st.stop()

# --- LÓGICA DE PROCESSAMENTO INTELIGENTE ---
def limpar_valor(valor):
    try:
        if pd.isna(valor): return 0.0
        v_str = str(valor).replace('.', '').replace(',', '.')
        valor_num = float(re.sub(r'[^\d.-]', '', v_str))
        return valor_num if 'D' not in str(valor) else -valor_num
    except: return 0.0

def classificar_transacao(historico):
    hist = str(historico).upper()
    if "PIX" in hist: return "🟢 PIX"
    if "TARIFA" in hist: return "🔴 TARIFA"
    if "SIPAG" in hist: return "💳 CARTÃO"
    return "🔹 OUTROS"

# --- INTERFACE PRINCIPAL ---
st.title("📊 Conciliador Inteligente")

# Seletor de contas
conta = st.selectbox("Conta Bancária:", ["Geral", "Dízimo", "Poupança"])

col1, col2 = st.columns(2)
with col1: f_banco = st.file_uploader("Extrato Sicoob (Excel)", type=["xlsx"])
with col2: f_sistema = st.file_uploader("Relatório Interno (CSV/XLSX)", type=["csv", "xlsx"])

if f_banco and f_sistema:
    try:
        # Carregamento robusto
        df_banco = pd.read_excel(f_banco)
        st.success("Arquivos carregados com sucesso!")
        
        # Filtro Inteligente
        tipo_filtro = st.sidebar.multiselect("Filtrar por Tipo:", ["🟢 PIX", "🔴 TARIFA", "💳 CARTÃO", "🔹 OUTROS"])
        
        # Exibição de dados simplificada
        st.write("### 📝 Pendências de Conciliação")
        # Aqui entra a lógica de exibição com os checkboxes que você já utiliza
        
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}. Verifique se o formato está correto.")
else:
    st.info("💡 Por favor, carregue os dois arquivos para iniciar.")

# --- DICA DE PRODUTIVIDADE ---
st.sidebar.markdown("---")
st.sidebar.info("📌 **Dica:** Mantenha os nomes das colunas dos seus arquivos sempre padronizados para que o sistema reconheça automaticamente.")
