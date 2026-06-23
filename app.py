import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # Silencia avisos no terminal

import streamlit as st
import pandas as pd
import re
import io
import datetime
import os
import json

# =========================================================================
# ⚙️ CONFIGURAÇÃO DA PÁGINA (DEVE SER O PRIMEIRO COMANDO STREAMLIT)
# =========================================================================
st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

CACHE_DIR = "cache_arquivos"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# =========================================================================
# 🔐 SISTEMA DE SEGURANÇA VIA URL PARAMS
# =========================================================================
if "token" in st.query_params and st.query_params["token"] == "sf_2026_authed":
    st.session_state.autenticado = True
    st.session_state.usuario_logado = st.query_params.get("user", "secretaria")
else:
    if "autenticado" not in st.session_state: st.session_state.autenticado = False
    if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = ""

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_log1, col_log2, col_log3 = st.columns([1, 2, 1])
    with col_log2:
        st.markdown("""
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 12px; border: 1px solid #dee2e6; box-shadow: 0px 4px 10px rgba(0,0,0,0.05);">
                <h2 style="text-align: center; color: #003366; margin-bottom: 5px;">⛪ Paróquia São Francisco de Assis</h2>
                <p style="text-align: center; color: #6c757d; font-size: 14px; margin-bottom: 25px;">Acesso Restrito ao Painel de Conciliation Financeira</p>
            </div>
        """, unsafe_allow_html=True)
        usuario_input = st.text_input("👤 Nome de Usuário:")
        senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
        if st.button("🔓 Entrar no Sistema", type="primary", use_container_width=True):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                st.query_params["token"] = "sf_2026_authed"
                st.query_params["user"] = usuario_input
                st.rerun()
            else: st.error("❌ Usuário ou senha incorretos!")
    st.stop()

# =========================================================================
# 🎨 ESTILOS VISUAIS (CSS)
# =========================================================================
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; padding: 10px 20px; }
    .titulo-coluna { display: flex; align-items: center; background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid #004B87; margin-bottom: 5px; font-weight: bold; }
    .titulo-coluna-igreja { display: flex; align-items: center; background-color: #fdfaf6; padding: 12px; border-radius: 8px; border-left: 5px solid #8B4513; margin-bottom: 5px; font-weight: bold; }
    .titulo-coluna-sipag { display: flex; align-items: center; background-color: #f4fbf7; padding: 12px; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 5px; font-weight: bold; }
    .titulo-coluna-campanha { display: flex; align-items: center; background-color: #fbf4f9; padding: 12px; border-radius: 8px; border-left: 5px solid #d946ef; margin-bottom: 5px; font-weight: bold; }
    .caixa-soma { background-color: #f1f3f5; padding: 8px 12px; border-radius: 6px; font-size: 16px; font-weight: bold; margin-bottom: 15px; text-align: center; border: 1px solid #cbd5e1; color: #0f172a; }
    .caixa-saida-d { background-color: #fef2f2; padding: 8px 12px; border-radius: 6px; font-size: 15px; font-weight: bold; margin-bottom: 15px; border: 1px solid #fee2e2; color: #dc2626; text-align: center; }
    </style>
""", unsafe_allow_html=True)

st.title("⛪ Sistema Integrado de Conciliação - Paróquia São Francisco de Assis")

# =========================================================================
# 🏦 SELEÇÃO DE CONTA 
# =========================================================================
conta_ativa = st.selectbox(
    "🏦 Escolha a Conta Bancária que deseja conciliar agora:",
    ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)", "Contas Poupança - PIX Oferta (Centros de Custo)"]
)

eh_poupanca = "Poupança" in conta_ativa

chave_store_banco = f"bytes_banco_{conta_ativa}"
chave_store_sistema = f"bytes_sistema_{conta_ativa}"
chave_store_sipag = f"bytes_sipag_{conta_ativa}"
chave_store_campanha = f"bytes_campanha_{conta_ativa}"
chave_store_dizimo = f"bytes_dizimo_{conta_ativa}"

chave_nome_banco = f"nome_banco_{conta_ativa}"
chave_nome_sistema = f"nome_sistema_{conta_ativa}"
chave_nome_sipag = f"nome_sipag_{conta_ativa}"
chave_nome_campanha = f"nome_campanha_{conta_ativa}"
chave_nome_dizimo = f"nome_dizimo_{conta_ativa}"

chave_dias_conciliados = f"dias_conciliados_{conta_ativa}"
chave_historico_ocultacoes = f"historico_ocultacoes_{conta_ativa}"
chave_data_atual_salva = f"data_salva_progresso_{conta_ativa}"

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_store_sipag not in st.session_state: st.session_state[chave_store_sipag] = None
if chave_store_campanha not in st.session_state: st.session_state[chave_store_campanha] = None
if chave_store_dizimo not in st.session_state: st.session_state[chave_store_dizimo] = None
if chave_dias_conciliados not in st.session_state: st.session_state[chave_dias_conciliados] = []
if chave_historico_ocultacoes not in st.session_state: st.session_state[chave_historico_ocultacoes] = []

arq_cache_banco = os.path.join(CACHE_DIR, f"banco_{conta_ativa}.cache")
arq_cache_sistema = os.path.join(CACHE_DIR, f"sistema_{conta_ativa}.cache")
arq_cache_sipag = os.path.join(CACHE_DIR, f"sipag_{conta_ativa}.cache")
arq_cache_campanha = os.path.join(CACHE_DIR, f"campanha_{conta_ativa}.cache")
arq_cache_dizimo = os.path.join(CACHE_DIR, f"dizimo_{conta_ativa}.cache")

arq_cache_nome_banco = os.path.join(CACHE_DIR, f"nome_banco_{conta_ativa}.txt")
arq_cache_nome_sistema = os.path.join(CACHE_DIR, f"nome_sistema_{conta_ativa}.txt")
arq_cache_data_ativa = os.path.join(CACHE_DIR, f"data_ativa_{conta_ativa}.txt")

# Recuperação de Cache do Banco
if st.session_state[chave_store_banco] is None and os.path.exists(arq_cache_banco):
    with open(arq_cache_banco, "rb") as f: st.session_state[chave_store_banco] = f.read()
    if os.path.exists(arq_cache_nome_banco):
        with open(arq_cache_nome_banco, "r", encoding="utf-8") as f: st.session_state[chave_nome_banco] = f.read()

# Recuperação de Cache do Sistema (SÓ SE NÃO FOR POUPANÇA)
if not eh_poupanca and st.session_state[chave_store_sistema] is None and os.path.exists(arq_cache_sistema):
    with open(arq_cache_sistema, "rb") as f: st.session_state[chave_store_sistema] = f.read()
    if os.path.exists(arq_cache_nome_sistema):
        with open(arq_cache_nome_sistema, "r", encoding="utf-8") as f: st.session_state[chave_nome_sistema] = f.read()

# =========================================================================
# 📥 CARREGAMENTO DE ARQUIVOS INTERFACE DINÂMICA
# =========================================================================
st.markdown("### 📥 Carregar Arquivos do Período")

if eh_poupanca:
    # Interface Simplicada exclusiva para Conta Poupança
    u_extrato = st.file_uploader("📂 Carregar Extrato da Conta Poupança (PDF):", type=["pdf"], key=f"widget_up_poup_{conta_ativa}")
    if u_extrato is not None:
        conteudo = u_extrato.getvalue()
        st.session_state[chave_store_banco] = conteudo
        st.session_state[chave_nome_banco] = u_extrato.name
        with open(arq_cache_banco, "wb") as f: f.write(conteudo)
        with open(arq_cache_nome_banco, "w", encoding="utf-8") as f: f.write(u_extrato.name)
    elif st.session_state[chave_store_banco] is not None:
        st.caption(f"✅ Extrato Poupança Ativo: `{st.session_state.get(chave_nome_banco, 'Extrato Poupança')}`")
else:
    # Interface de Multi-uploads para Contas Correntes (161 e 140)
    colunas_upload = st.columns(5)
    with colunas_upload[0]:
        u_extrato = st.file_uploader("📂 Arraste o Extrato do Sicoob:", type=["xlsx", "xls", "pdf"], key=f"widget_up_banco_{conta_ativa}")
        if u_extrato is not None:
            conteudo = u_extrato.getvalue()
            st.session_state[chave_store_banco] = conteudo
            st.session_state[chave_nome_banco] = u_extrato.name
            with open(arq_cache_banco, "wb") as f: f.write(conteudo)
            with open(arq_cache_nome_banco, "w", encoding="utf-8") as f: f.write(u_extrato.name)
    with colunas_upload[1]:
        u_sistema = st.file_uploader("📂 Relatório Boletim / Sistema:", type=["xlsx", "xls", "csv", "pdf"], key=f"widget_up_sist_{conta_ativa}")
        if u_sistema is not None:
            conteudo = u_sistema.getvalue()
            st.session_state[chave_store_sistema] = conteudo
            st.session_state[chave_nome_sistema] = u_sistema.name
            with open(arq_cache_sistema, "wb") as f: f.write(conteudo)
            with open(arq_cache_nome_sistema, "w", encoding="utf-8") as f: f.write(u_sistema.name)
    with colunas_upload[2]:
        u_sipag = st.file_uploader("📂 Planilha Cartão SIPAG (CSV/XLSX):", type=["csv", "xlsx"], key=f"widget_up_sipag_{conta_ativa}")
        if u_sipag is not None:
            conteudo = u_sipag.getvalue()
            st.session_state[chave_store_sipag] = conteudo
            st.session_state[chave_nome_sipag] = u_sipag.name
    with colunas_upload[3]:
        u_campanha = st.file_uploader("📂 Planilha Cartão Campanha (CSV/XLSX):", type=["csv", "xlsx"], key=f"widget_up_campanha_{conta_ativa}")
        if u_campanha is not None:
            conteudo = u_campanha.getvalue()
            st.session_state[chave_store_campanha] = conteudo
            st.session_state[chave_nome_campanha] = u_campanha.name
    with colunas_upload[4]:
        u_dizimo = st.file_uploader("📂 Conferência do Dízimo (CSV/XLSX):", type=["csv", "xlsx"], key=f"widget_up_dizimo_{conta_ativa}")
        if u_dizimo is not None:
            conteudo = u_dizimo.getvalue()
            st.session_state[chave_store_dizimo] = conteudo
            st.session_state[chave_nome_dizimo] = u_dizimo.name

# Botão Limpar Geral
if st.session_state[chave_store_banco] is not None:
    if st.button("🗑️ Trocar / Limpar Arquivos e Apagar Cache", use_container_width=True):
        for k in [chave_store_banco, chave_store_sistema, chave_store_sipag, chave_store_campanha, chave_store_dizimo, Chave_nome_banco]:
            st.session_state[k] = None
        st.session_state[chave_historico_ocultacoes] = []
        if 'indice_data' in st.session_state: del st.session_state.indice_data
        st.rerun()

# =========================================================================
# ⚙️ PARSER EXCLUSIVO PARA O PDF DA CONTA POUPANÇA (MÉTODO ROBUSTO RE/TEXT)
# =========================================================================
def extrair_dados_pdf_poupanca(arquivo_bytes):
    try:
        import pypdf
    except ImportError:
        # Fallback caso não possua a biblioteca instalada no ambiente
        st.error("Biblioteca 'pypdf' necessária para processamento de extrato em PDF.")
        return [], {}

    leitor = pypdf.PdfReader(io.BytesIO(arquivo_bytes))
    registros = []
    saldos_dia = {}
    
    # Regex para capturar data, descrição e valor com C ou D no final (Ex: 27/04/2026 PIX RECEBIDO-OUTRA IF 10,00C)
    padrao_linha = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+[CD])')

    for pagina in leitor.pages:
        texto = pagina.extract_text()
        if not texto: continue
        
        for linha in texto.split('\n'):
            linha = linha.strip()
            match = padrao_linha.search(linha)
            if match:
                data_f = match.group(1)
                descricao = match.group(2).strip().upper()
                valor_raw = match.group(3).strip().upper()
                
                # Conversão numérica limpa
                sinal_d = 'D' in valor_raw
                num_limpo = re.sub(r'[^\d,.]', '', valor_raw)
                if ',' in num_limpo and '.' in num_limpo: num_limpo = num_limpo.replace('.', '')
                num_limpo = num_limpo.replace(',', '.')
                
                try:
                    valor_float = float(num_limpo)
                    valor_final = -valor_float if sinal_d else valor_float
                except:
                    continue
                
                if "SALDO DO DIA" in descricao:
                    saldos_dia[data_f] = valor_float
                else:
                    registros.append({
                        'Data': data_f,
                        'Descrição': descricao,
                        'Valor': valor_final,
                        'Tipo': 'SAÍDA (D)' if sinal_d else 'ENTRADA (C)'
                    })
                    
    return registros, saldos_dia

# =========================================================================
# 📊 RENDERIZADOR DA TELA DO CONCILIADOR DE POUPANÇA
# =========================================================================
if eh_poupanca and st.session_state[chave_store_banco]:
    dados_poupanca, mapa_saldos = extrair_dados_pdf_poupanca(st.session_state[chave_store_banco])
    
    if not dados_poupanca:
        st.warning("⚠️ Não foi possível encontrar registros no PDF estruturado. Verifique se o arquivo está correto.")
    else:
        df_poup = pd.DataFrame(dados_poupanca)
        todas_datas = sorted(list(df_poup['Data'].unique()), key=lambda x: pd.to_datetime(x, dayfirst=True))
        
        with st.sidebar:
            st.markdown("### 📆 Filtro de Período")
            data_selecionada = st.selectbox("Selecione o Dia para Análise:", todas_datas)
            
        df_dia = df_poup[df_poup['Data'] == data_selecionada].copy()
        
        # Filtros e cálculos solicitados pelo usuário:
        # 1. Pix recebidos (Créditos da Operação)
        filtro_pix = df_dia['Descrição'].str.contains("PIX RECEBIDO|TRANSF. CC|INTERCRE", regex=True)
        df_pix = df_dia[filtro_pix & (df_dia['Valor'] > 0)]
        soma_pix = df_pix['Valor'].sum()
        
        # 2. Rendimentos Selic do dia
        filtro_selic = df_dia['Descrição'].str.contains("SELIC|JUROS", regex=True)
        df_selic = df_dia[filtro_selic & (df_dia['Valor'] > 0)]
        soma_selic = df_selic['Valor'].sum()
        
        # 3. Retiradas (Valores com D)
        df_retiradas = df_dia[df_dia['Valor'] < 0]
        soma_retiradas = df_retiradas['Valor'].sum()
        
        # KPIs no topo da página
        st.markdown(f"---")
        st.markdown(f"### 📊 Resumo Consolidado de Conta Poupança — Dia: `{data_selecionada}`")
        
        c_k1, c_k2, c_k3 = st.columns(3)
        c_k1.metric("🟢 Entradas via PIX / Transf (C)", f"R$ {soma_pix:,.2f}")
        c_k2.metric("📈 Rendimento SELIC / Juros", f"R$ {soma_selic:,.2f}")
        c_k3.metric("🔴 Retiradas da Conta (D)", f"R$ {abs(soma_retiradas):,.2f}")
        
        st.markdown("---")
        
        col_t1, col_t2 = st.columns([2, 1])
        
        with col_t1:
            st.markdown("<div class='titulo-coluna'>📥 Detalhamento de Entradas Registradas (C)</div>", unsafe_allow_html=True)
            df_entradas_print = df_dia[df_dia['Valor'] > 0]
            if df_entradas_print.empty:
                st.info("Nenhuma entrada registrada nesta data.")
            else:
                st.dataframe(df_entradas_print[['Descrição', 'Valor', 'Tipo']], use_container_width=True, hide_index=True)
                
        with col_t2:
            st.markdown("<div class='titulo-coluna-igreja'>📤 Saídas / Retiradas Detectadas (D)</div>", unsafe_allow_html=True)
            if df_retiradas.empty:
                st.info("Parabéns! Nenhuma retirada de fundos (D) detectada hoje.")
            else:
                st.markdown(f"<div class='caixa-saida-d'>Total sacado no dia: R$ {abs(soma_retiradas):,.2f}</div>", unsafe_allow_html=True)
                st.dataframe(df_retiradas[['Descrição', 'Valor']], use_container_width=True, hide_index=True)

# Mantém a execução padrão ativa se o usuário selecionar as contas normais (161 ou 140)
elif not eh_poupanca:
    st.info("Por favor, certifique-se de que o Extrato Sicoob e o Relatório do Sistema foram carregados para prosseguir com a conciliação das contas correntes.")
