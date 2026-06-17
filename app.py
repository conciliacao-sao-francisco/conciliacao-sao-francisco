import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # Silencia avisos no terminal

import streamlit as st
import pandas as pd
import re
import io
import datetime

# Importa leitores de PDF e gerenciador de Cookies Seguros
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from streamlit_cookies_controller import CookieController
    controller = CookieController()
except:
    controller = None

# Configuração da página em modo AMPLO
st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

# =========================================================================
# 🔐 SISTEMA DE SEGURANÇA AVANÇADO (PERSISTÊNCIA POR COOKIES - 30 DIAS)
# =========================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = ""

# Tenta recuperar o login salvo no navegador da máquina
if not st.session_state.autenticado and controller:
    try:
        cookie_login = controller.get("paroquia_sf_auth")
        cookie_user = controller.get("paroquia_sf_user")
        if cookie_login == "token_seguro_sf_2026" and cookie_user:
            st.session_state.autenticado = True
            st.session_state.usuario_logado = cookie_user
    except:
        pass

# Tela de Bloqueio se não estiver autenticado
if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_log1, col_log2, col_log3 = st.columns([1, 2, 1])
    
    with col_log2:
        st.markdown("""
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);">
                <h2 style="text-align: center; color: #003366; margin-bottom: 5px;">⛪ Paróquia São Francisco de Assis</h2>
                <p style="text-align: center; color: #6c757d; font-size: 14px; margin-bottom: 25px;">Acesso Restrito ao Painel de Conciliação Financeira</p>
            </div>
        """, unsafe_allow_html=True)
        
        usuario_input = st.text_input("👤 Nome de Usuário:")
        senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
        lembrar_acesso = st.checkbox("📌 Manter-me conectado nesta máquina (Não pede senha por 30 dias)", value=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔓 Entrar no Sistema", type="primary", use_container_width=True):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                
                # Se o usuário marcou para lembrar, grava o Cookie no navegador
                if lembrar_acesso and controller:
                    validade = datetime.datetime.now() + datetime.timedelta(days=30)
                    controller.set("paroquia_sf_auth", "token_seguro_sf_2026", expires=validade)
                    controller.set("paroquia_sf_user", usuario_input, expires=validade)
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos! Tente novamente.")
                
    st.stop()

# =========================================================================
# ESTILIZAÇÕES CUSTOMIZADAS (CSS)
# =========================================================================
st.markdown("""
    <style>
    .block-container { padding-top:
