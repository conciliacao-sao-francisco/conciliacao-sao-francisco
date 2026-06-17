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
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; padding: 10px 20px; }
    thead th { background-color: #f0f2f6 !important; color: #31333F !important; font-weight: bold !important; }
    .titulo-coluna { display: flex; align-items: center; background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid #004B87; margin-bottom: 5px; }
    .titulo-coluna-igreja { display: flex; align-items: center; background-color: #fdfaf6; padding: 12px; border-radius: 8px; border-left: 5px solid #8B4513; margin-bottom: 5px; }
    .caixa-calculo { background-color: #e3f2fd; padding: 6px 12px; border-radius: 6px; font-weight: bold; color: #0d47a1; margin-bottom: 15px; font-size: 14px; display: inline-block; width: 100%; }
    .caixa-calculo-igreja { background-color: #efebe9; padding: 6px 12px; border-radius: 6px; font-weight: bold; color: #4e342e; margin-bottom: 15px; font-size: 14px; display: inline-block; width: 100%; }
    .texto-header-col { margin-left: 10px; font-size: 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("⛪ Sistema Integrado de Conciliação - Paróquia São Francisco de Assis")

with st.sidebar:
    st.markdown("### 👤 Usuário Ativo")
    st.info(f"Conectado como: **{st.session_state.usuario_logado}**")
    if st.button("🔒 Sair do Sistema (Logoff)", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = ""
        if controller:
            controller.remove("paroquia_sf_auth")
            controller.remove("paroquia_sf_user")
        st.rerun()
    st.markdown("---")

# --- SELETOR DA CONTA ATIVA NO TOPO DO APP ---
conta_ativa = st.selectbox(
    "🏦 Escolha a Conta Bancária que deseja conciliar agora:",
    ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)", "Contas Poupança - PIX Oferta (Centros de Custo)"]
)

# --- TRATAMENTO MONETÁRIO UNIVERSAL ---
def converter_valor_extrato(val_str):
    if pd.isna(val_str): return 0.0
    val_str = str(val_str).strip().upper()
    eh_debito = 'D' in val_str or '-' in val_str
    apenas_numeros = re.sub(r'[^\d,,.]', '', val_str)
    if not apenas_numeros: return 0.0
    if ',' in apenas_numeros and '.' in apenas_numeros:
        apenas_numeros = apenas_numeros.replace('.', '')
    apenas_numeros = apenas_numeros.replace(',', '.')
    try:
        valor_float = float(apenas_numeros)
        return -valor_float if eh_debito else valor_float
    except: return 0.0

def extrair_detalhe_limpo(historico, detalhes):
    hist_u = str(historico).upper().strip()
    det_u = str(detalhes).upper().strip()
    
    tipo = "🔹 OUTROS"
    if "PIX RECEBIDO" in hist_u or "RECEBIDO DE OUTRA IF" in hist_u: 
        tipo = "🟢 PIX RECEBIDO"
    elif "PIX ENVIADO" in hist_u or "PIX TRANSFERIDO" in hist_u: 
        tipo = "🔴 PIX ENVIADO"
    elif "PAGTO TITULO" in hist_u or "PAGAMENTO" in hist_u: 
        tipo = "🔴 PAGTO TITULO"
    elif "TARIFA" in hist_u or "TAR EXTRATO" in hist_u: 
        tipo = "🔴 TAR TARIFA"
    elif "JUROS" in hist_u or "REND" in hist_u or "SELIC" in hist_u or "CRED.REND" in hist_u: 
        tipo = "📈 RENDIMENTO POUPANÇA"
    elif "ESTORNO" in hist_u: 
        tipo = "🟢 ESTORNO"
    elif "TRANSF" in hist_u and "RECEB" in hist_u: 
        tipo = "🟢 TRANSF RECEBIDA"
    elif "TRANSF" in hist_u: 
        tipo = "🔴 TRANSF ENVIADA"

    limpeza_regex = [
        r"RECEBIDO DE OUTRA IF", r"PIX TRANSFERIDO", r"PIX RECEBIDO", r"PAGTO TITULO INTERNET",
        r"COMPLEMENTO:", r"VALOR DO COMPROMISSO", r"COBRANCA SICOOB", r"FAVORECIDO:", r"PAGADOR:",
        r"REMETENTE:", r"AGENCIA:", r"CONTA:", r"CPF:", r"CNPJ:", r"-\s*$"
    ]
    nome_isolado = det_u
    for padrao in limpeza_regex:
        nome_isolado = re.sub(padrao, "", nome_isolado)
        
    nome_isolado = re.sub(r'\s+', ' ', nome_isolado).strip().lstrip('-').strip()
    
    if not nome_isolado or len(nome_isolado) < 3:
        nome_isolado = hist_u
    return tipo, nome_isolado

# --- PARSER DE EXTRATO DO SICOOB (EXCEL) ---
def processar_extrato_sicoob(arquivo_upload):
    df_s_bruto = pd.read_excel(arquivo_upload, skiprows=1)
    saldo_anterior_inicial = 0.0
    saldos_finais_por_dia = {}
    
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        historico = str(row.iloc[2]).strip().upper()
        data_linha = row.iloc[0]
        if "SALDO ANTERIOR" in historico:
            saldo_anterior_inicial = abs(converter_valor_extrato(row.iloc[3]))
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
                'Documento': str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else '',
                'Histórico': historico, 'Valor': converter_valor_extrato(row.iloc[3]), 'Detalhes': ''
            }
        else:
            if linha_mestre:
                texto_detalhe = " ".join([str(v).strip() for v in row.values if pd.notna(v)])
                linha_mestre['Detalhes'] += " " + texto_detalhe
                
    if linha_mestre: dados_banco_brutos.append(linha_mestre)
    return dados_banco_brutos, saldo_anterior_inicial, saldos_finais_por_dia

# --- PARSER DE EXTRATO DE POUPANÇA (PDF) ---
def extrair_dados_pdf_poupanca(arquivo_pdf):
    if pypdf is None:
        st.error("Erro crítico: Biblioteca 'pypdf' em falta no sistema.")
        return []
    leitor = pypdf.PdfReader(arquivo_pdf)
    linhas_finais = []
    regex_data = re.compile(r'(\d{2}/\d{2}/\d{4})')
    
    for pagina in leitor.pages:
        texto = pagina.extract_text()
        if not texto: continue
        for linha in texto.split('\n'):
            linha_u = rename_u = linha.upper().strip()
            match_data = regex_data.search(linha_u)
            if match_data and "SALDO" not in inline_u:
                dt_enc = match_data.group(1)
                tipo = "📈 RENDIMENTO POUPANÇA" if any(x in rename_u for x in ["JUROS", "REND", "SELIC", "CRED.REND"]) else "🔹 OFERTA / PIX"
                partes = linha_u.split()
                if len(partes) >= 3:
                    v_num = converter_valor_extrato(partes[-1])
                    if v_num == 0.0 and len(partes) > 1:
                        v_num = converter_valor_extrato(partes[-2])
                    if v_num != 0.0:
                        desc = linha_u.replace(dt_enc, "").replace(partes[-1], "").strip()
                        linhas_finais.append({'Data': dt_enc, 'Tipo': tipo, 'Descrição': desc, 'Valor': v_num})
    return linhas_finais

# --- PROCESSADOR CENTRAL DE UPLOAD CONTAS CORRENTES ---
def carregar_dados_upload(modo_conta, file_banco, file_sistema):
    if not file_banco: return None, None, {}
    dados_b, s_ant, s_finais = processar_extrato_sicoob(file_banco)
    dados_banco_finais = []
    sipag_por_dia = {}
    idx_b = 0
    
    for item in dados_b:
        hist_c = (item['Histórico'] + " " + item['Detalhes']).upper()
        tipo_limpo, detalhe_
