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
# LÓGICA DE MATCH POR APROXIMAÇÃO (AJUSTE DE TAXAS)
# =========================================================================
def sao_valores_compativeis(valor_banco, valor_sistema, margem=0.06):
    """
    Verifica se o valor do banco (líquido) é compatível com o do sistema (bruto),
    considerando a perda de taxa de cartão (padrão 6% para ser abrangente).
    """
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
        st.markdown("<h2 style='text-align:center;'>⛪ Paróquia São Francisco</h2>", unsafe_allow_html=True)
        usuario_input = st.text_input("👤 Usuário:")
        senha_input = st.text_input("🔑 Senha:", type="password")
        if st.button("🔓 Entrar"):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# =========================================================================
#
