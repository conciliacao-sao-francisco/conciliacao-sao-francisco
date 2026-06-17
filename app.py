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
# ESTILIZAÇÕES E FUNÇÕES DE PROCESSAMENTO
# =========================================================================
st.markdown("""
    <style>
    .caixa-calculo { background-color: #e3f2fd; padding: 10px; border-radius: 6px; font-weight: bold; color: #0d47a1; }
    .caixa-calculo-igreja { background-color: #efebe9; padding: 10px; border-radius: 6px; font-weight: bold; color: #4e342e; }
    </style>
""", unsafe_allow_html=True)

def converter_valor_extrato(val_str):
    if pd.isna(val_str): return 0.0
    val_str = str(val_str).strip().upper()
    eh_debito = 'D' in val_str or '-' in val_str
    apenas_numeros = re.sub(r'[^\d,,.]', '', val_str).replace('.', '').replace(',', '.')
    try:
        valor = float(apenas_numeros)
        return -valor if eh_debito else valor
    except: return 0.0

def extrair_detalhe_limpo(historico, detalhes):
    hist_u = str(historico).upper().strip()
    tipo = "🔹 OUTROS"
    if "PIX" in hist_u: tipo = "🟢 PIX"
    elif "SIPAG" in hist_u or "COMPRAS" in hist_u: tipo = "💳 SIPAG / CARTÃO"
    elif "TARIFA" in hist_u: tipo = "🔴 TARIFA"
    return tipo, str(detalhes).upper().strip()

# [AQUI ENTRA O RESTANTE DAS SUAS FUNÇÕES ORIGINAIS: processar_extrato_sicoob, extrair_dados_pdf_poupanca, etc.]

# =========================================================================
# INTERFACE PRINCIPAL
# =========================================================================
st.title("⛪ Sistema de Conciliação")
conta_ativa = st.selectbox("🏦 Conta:", ["Conta 161 - Geral", "Conta 140 - Dízimo"])

# --- LÓGICA DE EXIBIÇÃO NA ABA DE CONCILIAÇÃO ---
# Dentro do seu loop de exibição:
# ...
# for _, row in df_banco_tela.iterrows():
#     v_abs = abs(row['Valor'])
#     
#     # VERIFICAÇÃO INTELIGENTE:
#     tem_match = False
#     for v_sist in valores_sistema_abs:
#         if sao_valores_compativeis(v_abs, v_sist):
#             tem_match = True
#             break
#
#     tag = " 💸 [AJUSTE TAXA]" if tem_match else ""
#     label = f"{row['Tipo']} | R$ {v_abs:,.2f} | {row['Histórico'][:30]}{tag}"
#     
#     if st.checkbox(label, key=f"b_{row['id_banco']}", value=tem_match):
#         # ... lógica de seleção ...
