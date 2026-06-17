import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

import streamlit as st
import pandas as pd
import re
import io
import datetime

# --- IMPORTAÇÕES ---
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from streamlit_cookies_controller import CookieController
    controller = CookieController()
except:
    controller = None

st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

# =========================================================================
# LÓGICA DE MATCH POR APROXIMAÇÃO E EXATO
# =========================================================================
def sao_valores_compativeis(valor_banco, valor_sistema, margem=0.06):
    """Verifica se o banco (líquido) é compatível com sistema (bruto) - até 6% de taxa."""
    if valor_sistema == 0: return False
    proporcao = valor_banco / valor_sistema
    return (1 - margem) <= proporcao <= 1.00

# =========================================================================
# SISTEMA DE SEGURANÇA E AUTH
# =========================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = ""

if not st.session_state.autenticado and controller:
    try:
        cookie_login = controller.get("paroquia_sf_auth")
        if cookie_login == "token_seguro_sf_2026":
            st.session_state.autenticado = True
            st.session_state.usuario_logado = controller.get("paroquia_sf_user")
    except: pass

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<h2 style='text-align:center; color:#003366;'>⛪ Paróquia São Francisco</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#666;'>Acesso Restrito - Secretaria</p>", unsafe_allow_html=True)
        usuario_input = st.text_input("👤 Usuário:")
        senha_input = st.text_input("🔑 Senha:", type="password")
        lembrar = st.checkbox("Manter conectado", value=True)
        if st.button("🔓 Entrar", use_container_width=True, type="primary"):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                if lembrar and controller:
                    validade = datetime.datetime.now() + datetime.timedelta(days=30)
                    controller.set("paroquia_sf_auth", "token_seguro_sf_2026", expires=validade)
                    controller.set("paroquia_sf_user", usuario_input, expires=validade)
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# =========================================================================
# ESTILIZAÇÕES (CSS)
# =========================================================================
st.markdown("""
    <style>
    .caixa-calculo { background-color: #e3f2fd; padding: 10px; border-radius: 6px; font-weight: bold; color: #0d47a1; text-align: center; }
    .caixa-calculo-igreja { background-color: #efebe9; padding: 10px; border-radius: 6px; font-weight: bold; color: #4e342e; text-align: center; }
    .painel-diferenca { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 2px solid #dee2e6; text-align: center; margin-top: 20px; }
    .titulo-coluna { display: flex; align-items: center; background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid #004B87; margin-bottom: 10px; }
    .titulo-coluna-igreja { display: flex; align-items: center; background-color: #fdfaf6; padding: 12px; border-radius: 8px; border-left: 5px solid #8B4513; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================================
# FUNÇÕES DE PROCESSAMENTO DE ARQUIVOS
# =========================================================================
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
    df_s_bruto = pd.read_excel(arquivo_upload, skiprows=1)
    saldo_anterior = 0.0
    saldos_finais = {}
    dados_banco = []
    
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        historico = str(row.iloc[2]).strip().upper()
        data = row.iloc[0]
        if "SALDO ANTERIOR" in historico:
            saldo_anterior = abs(converter_valor_extrato(row.iloc[3]))
        if "SALDO DO DIA" in historico and pd.notna(data):
            dt_fmt = pd.to_datetime(str(data).strip(), dayfirst=True).strftime('%d/%m/%Y')
            saldos_finais[dt_fmt] = abs(converter_valor_extrato(row.iloc[3]))

    linha_mestre = None
    for i, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        data_orig = row.iloc[0]
        historico = str(row.iloc[2]).strip().upper()
        if "SALDO" in historico: continue
        
        if pd.notna(data_orig) and '/' in str(data_orig):
            if linha_mestre
