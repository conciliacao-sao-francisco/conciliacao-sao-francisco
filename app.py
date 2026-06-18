import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # Silencia avisos no terminal

import streamlit as st
import pandas as pd
import re
import io
import datetime

# Importa leitores de PDF
try:
    import pypdf
except ImportError:
    pypdf = None

# Configuração da página em modo AMPLO
st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

# =========================================================================
# 🔐 SISTEMA DE SEGURANÇA VIA URL PARAMS (BLINDADO CONTRA F5)
# =========================================================================
if "token" in st.query_params and st.query_params["token"] == "sf_2026_authed":
    st.session_state.autenticado = True
    st.session_state.usuario_logado = st.query_params.get("user", "secretaria")
else:
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    if "usuario_logado" not in st.session_state:
        st.session_state.usuario_logado = ""

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
# ESTILIZAÇÕES CUSTOMIZADAS (PADRÃO VISUAL IDENTICO)
# =========================================================================
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; padding: 10px 20px; }
    thead th { background-color: #f0f2f6 !important; color: #31333F !important; font-weight: bold !important; }
    .titulo-coluna { display: flex; align-items: center; background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid #004B87; margin-bottom: 5px; font-weight: bold; }
    .titulo-coluna-igreja { display: flex; align-items: center; background-color: #fdfaf6; padding: 12px; border-radius: 8px; border-left: 5px solid #8B4513; margin-bottom: 5px; font-weight: bold; }
    .titulo-coluna-sipag { display: flex; align-items: center; background-color: #f4fbf7; padding: 12px; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("⛪ Sistema Integrado de Conciliação - Paróquia São Francisco de Assis")

with st.sidebar:
    st.markdown("### 👤 Usuário Ativo")
    st.info(f"Conectado como: **{st.session_state.usuario_logado}**")
    if st.button("🔒 Sair do Sistema (Logoff)", use_container_width=True):
        st.session_state.autenticado = False
        st.query_params.clear()
        st.rerun()
    st.markdown("---")

conta_ativa = st.selectbox(
    "🏦 Escolha a Conta Bancária que deseja conciliar agora:",
    ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)", "Contas Poupança - PIX Oferta (Centros de Custo)"]
)

# =========================================================================
# 💾 PERSISTÊNCIA MULTI-ARQUIVOS (ANTI-F5)
# =========================================================================
chave_store_banco = f"bytes_banco_{conta_ativa}"
chave_store_sistema = f"bytes_sistema_{conta_ativa}"
chave_store_sipag = f"bytes_sipag_{conta_ativa}"
chave_nome_banco = f"nome_banco_{conta_ativa}"
chave_nome_sistema = f"nome_sistema_{conta_ativa}"
chave_nome_sipag = f"nome_sipag_{conta_ativa}"
chave_modificacoes = f"modificacoes_ajustes_{conta_ativa}"
chave_dias_conciliados = f"dias_conciliados_{conta_ativa}"

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_store_sipag not in st.session_state: st.session_state[chave_store_sipag] = None
if chave_modificacoes not in st.session_state: st.session_state[chave_modificacoes] = []
if chave_dias_conciliados not in st.session_state: st.session_state[chave_dias_conciliados] = {}

st.markdown("### 📥 Carregar Arquivos do Período")
col_up1, col_up2, col_up3 = st.columns(3)

with col_up1:
    u_extrato = st.file_uploader("📂 Arraste o Extrato do Sicoob:", type=["xlsx", "xls", "pdf"], key=f"up_banco_{conta_ativa}")
    if u_extrato:
        st.session_state[chave_store_banco] = u_extrato.getvalue()
        st.session_state[chave_nome_banco] = u_extrato.name
    if st.session_state[chave_store_banco]: st.success(f"🟢 {st.session_state[chave_nome_banco]}")

with col_up2:
    u_sistema = st.file_uploader("📂 Arraste o Relatório do Boletim / Sistema:", type=["xlsx", "xls", "csv"], key=f"up_sist_{conta_ativa}")
    if u_sistema:
        st.session_state[chave_store_sistema] = u_sistema.getvalue()
        st.session_state[chave_nome_sistema] = u_sistema.name
    if st.session_state[chave_store_sistema]: st.success(f"🟢 {st.session_state[chave_nome_sistema]}")

with col_up3:
    u_sipag = st.file_uploader("📂 Opcional: Arraste a Planilha do Cartão SIPAG:", type=["csv", "xlsx"], key=f"up_sipag_{conta_ativa}")
    if u_sipag:
        st.session_state[chave_store_sipag] = u_sipag.getvalue()
        st.session_state[chave_nome_sipag] = u_sipag.name
    if st.session_state[chave_store_sipag]: st.success(f"🟢 {st.session_state[chave_nome_sipag]}")

if st.session_state[chave_store_banco] or st.session_state[chave_store_sistema] or st.session_state[chave_store_sipag]:
    if st.button("🗑️ Trocar / Limpar Arquivos da Tela", use_container_width=True):
        st.session_state[chave_store_banco] = None
        st.session_state[chave_store_sistema] = None
        st.session_state[chave_store_sipag] = None
        st.session_state[chave_modificacoes] = []
        st.session_state[chave_dias_conciliados] = {}
        st.session_state.indice_data = 0
        st.rerun()

# =========================================================================
# PARSERS UNIVERSAIS DE DINHEIRO E TEXTO
# =========================================================================
def converter_valor_extrato(val_str):
    if pd.isna(val_str): return 0.0
    val_str = str(val_str).strip().upper()
    eh_debito = 'D' in val_str or '-' in val_str
    apenas_numeros = re.sub(r'[^\d,,.]', '', val_str)
    if not apenas_numeros: return 0.0
    if ',' in apenas_numeros and '.' in apenas_numeros: apenas_numeros = apenas_numeros.replace('.', '')
    apenas_numeros = apenas_numeros.replace(',', '.')
    try:
        valor_float = float(apenas_numeros)
        return -valor_float if eh_debito else valor_float
    except: return 0.0

def processar_extrato_sicoob(arquivo_bytes):
    df_s_bruto = pd.read_excel(io.BytesIO(arquivo_bytes), skiprows=1)
    saldo_anterior_inicial = 0.0
    saldos_finais_por_dia = {}
    
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        historico = str(row.iloc[2]).strip().upper()
        data_linha = row.iloc[0]
        if "SALDO ANTERIOR" in historico: saldo_anterior_inicial = abs(converter_valor_extrato(row.iloc[3]))
        if "SALDO DO DIA" in historico and pd.notna(data_linha):
            dt_formatada = pd.to_datetime(str(data_linha).strip(), dayfirst=True).strftime('%d/%m/%Y')
            saldos_finais_por_dia[dt_formatada] = abs(converter_valor_extrato(row.iloc[3]))

    dados_banco_brutos = []
    linha_mestre = None
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        data_orig = row.iloc[0]
        historico = str(row.iloc[2]).strip().upper()
        if "SALDO" in historico: continue
        
        if pd.notna(data_orig) and '/' in str(data_orig):
            if linha_mestre: dados_banco_brutos.append(linha_mestre)
            linha_mestre = {
                'Data': pd.to_datetime(str(data_orig).strip(), dayfirst=True).strftime('%d/%m/%Y'),
                'Histórico': historico, 'Valor': converter_valor_extrato(row.iloc[3]), 'Detalhes': ''
            }
        else:
            if linha_mestre:
                linha_mestre['Detalhes'] += " " + " ".join([str(v).strip() for v in row.values if pd.notna(v)])
                
    if linha_mestre: dados_banco_brutos.append(linha_mestre)
    return dados_banco_brutos, saldo_anterior_inicial, saldos_finais_por_dia

def processar_sipag_csv(arquivo_bytes):
    try:
        df_sipag = pd.read_csv(io.BytesIO(arquivo_bytes), sep=';', skiprows=2)
        dados_finais = []
        for idx, row in df_sipag.iterrows():
            if len(row) < 11 or pd.isna(row.iloc[1]): continue
            dt_str = str(row.iloc[1]).split()[0]
            try:
                dt_f = pd.to_datetime(dt_str, dayfirst=True).strftime('%d/%m/%Y')
                bandeira = str(row.iloc[3]).strip()
                forma = str(row.iloc[4]).strip()
                v_bruto = converter_valor_extrato(row.iloc[9])
                terminal = f"Term: {row.iloc[7]}" if pd.notna(row.iloc[7]) else ""
                
                dados_finais.append({
                    'id': f"SIPAG_{idx}", 'Data': dt_f, 'Tipo': f"💳 LOTE {bandeira.upper()}",
                    'Descrição': f"CARTÃO {forma.upper()} - {terminal}", 'Valor': v_bruto, 'Origem': 'Sipag'
                })
            except: continue
        return pd.DataFrame(dados_finais)
    except: return pd.DataFrame()

# =========================================================================
# FLUXO PRINCIPAL DE PROCESSAMENTO
# =========================================================================
if st.session_state[chave_store_banco] and st.session_state[chave_store_sistema]:
    dados_b, s_ant, s_finais = processar_extrato_sicoob(st.session_state[chave_store_banco])
    
    dados_banco_finais = []
    for idx, item in enumerate(dados_b):
        hist_u = item['Histórico'].upper()
        tipo = "🔹 OUTROS"
        if "PIX RECEBIDO" in hist_u or "RECEBIDO" in hist_u: tipo = "🟢 PIX RECEBIDO"
        elif "PIX ENVIADO" in hist_u or "TRANSFERIDO" in hist_u: tipo = "🔴 PIX ENVIADO"
        elif "PAGTO TITULO" in hist_u or "PAGAMENTO" in hist_u: tipo = "🔴 PAGTO TITULO"
        elif "SIPAG" in hist_u or "COMPRAS" in hist_u: tipo = "💳 SIPAG LOTE"
        
        dados_banco_finais.append({
            'id': f"B_{idx}", 'Data': item['Data'], 'Tipo': tipo,
            'Descrição': item['Histórico'] + " " + item['Detalhes'][:40], 'Valor': item['Valor'], 'Origem': 'Banco'
        })
    df_b_orig = pd.DataFrame(dados_banco_finais)
    
    dados_contrapartida = []
    df_t_bruto = pd.read_excel(io.BytesIO(st.session_state[chave_store_sistema]), skiprows=7).dropna(how='all')
    for idx_t, row in df_t_bruto.iterrows():
        if len(row
