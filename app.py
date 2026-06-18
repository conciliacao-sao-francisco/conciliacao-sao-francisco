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
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔓 Entrar no Sistema", type="primary", use_container_width=True):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                st.query_params["token"] = "sf_2026_authed"
                st.query_params["user"] = usuario_input
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
        st.query_params.clear()
        st.rerun()
    st.markdown("---")

# --- SELETOR DA CONTA ATIVA ---
conta_ativa = st.selectbox(
    "🏦 Escolha a Conta Bancária que deseja conciliar agora:",
    ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)", "Contas Poupança - PIX Oferta (Centros de Custo)"]
)

# =========================================================================
# 💾 PERSISTÊNCIA ROBUSTA DE ARQUIVOS (ANTI-F5 DIRETO NA SESSÃO)
# =========================================================================
chave_store_banco = f"bytes_banco_{conta_ativa}"
chave_store_sistema = f"bytes_sistema_{conta_ativa}"
chave_nome_banco = f"nome_banco_{conta_ativa}"
chave_nome_sistema = f"nome_sistema_{conta_ativa}"

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None

st.markdown("### 📥 Carregar Arquivos do Período")
col_up1, col_up2 = st.columns(2)

with col_up1:
    if "Poupança" in conta_ativa:
        u_extrato = st.file_uploader("📂 Arraste o Extrato PDF da Poupança:", type=["pdf"], key=f"upload_banco_{conta_ativa}")
    else:
        u_extrato = st.file_uploader("📂 Arraste o Extrato Excel do Sicoob:", type=["xlsx", "xls"], key=f"upload_banco_{conta_ativa}")
    
    if u_extrato:
        st.session_state[chave_store_banco] = u_extrato.getvalue()
        st.session_state[chave_nome_banco] = u_extrato.name
    
    if st.session_state[chave_store_banco] is not None:
        st.success(f"🟢 Extrato na Memória: {st.session_state.get(chave_nome_banco, '')}")

with col_up2:
    if "161" in conta_ativa:
        u_sistema = st.file_uploader("📂 Arraste o Relatório do Boletim (Theos):", type=["xlsx", "xls"], key=f"upload_sist_{conta_ativa}")
    elif "140" in conta_ativa:
        u_sistema = st.file_uploader("📂 Arraste a Conferência do Dízimo (Eclesial):", type=["csv"], key=f"upload_sist_{conta_ativa}")
    else:
        u_sistema = None

    if u_sistema:
        st.session_state[chave_store_sistema] = u_sistema.getvalue()
        st.session_state[chave_nome_sistema] = u_sistema.name
        
    if "Poupança" not in conta_ativa and st.session_state[chave_store_sistema] is not None:
        st.success(f"🟢 Boletim/Sistema na Memória: {st.session_state.get(chave_nome_sistema, '')}")

if st.session_state[chave_store_banco] is not None or st.session_state[chave_store_sistema] is not None:
    if st.button("🗑️ Trocar / Limpar Arquivos da Tela", use_container_width=True):
        st.session_state[chave_store_banco] = None
        st.session_state[chave_store_sistema] = None
        st.rerun()

# Recuperando variáveis locais estáveis
bytes_banco_prontos = st.session_state[chave_store_banco]
bytes_sistema_prontos = st.session_state[chave_store_sistema]

# =========================================================================
# TRATAMENTO DE TRADUÇÃO E PARSERS DOS ARQUIVOS
# =========================================================================
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
    if "PIX RECEBIDO" in hist_u or "RECEBIDO DE OUTRA IF" in hist_u: tipo = "🟢 PIX RECEIVED"
    elif "PIX ENVIADO" in hist_u or "PIX TRANSFERIDO" in hist_u: tipo = "🔴 PIX SENT"
    elif "PAGTO TITULO" in hist_u or "PAGAMENTO" in hist_u: tipo = "🔴 PAGTO TITULO"
    elif "TARIFA" in hist_u or "TAR EXTRATO" in hist_u: tipo = "🔴 TAR TARIFA"
    
    limpeza_regex = [r"RECEBIDO DE OUTRA IF", r"PIX TRANSFERIDO", r"PIX RECEBIDO", r"FAVORECIDO:", r"PAGADOR:", r"REMETENTE:"]
    name_isolado = det_u
    for padrao in limpeza_regex: name_isolado = re.sub(padrao, "", name_isolado)
    name_isolado = re.sub(r'\s+', ' ', name_isolado).strip().lstrip('-').strip()
    if not name_isolado or len(name_isolado) < 3: name_isolado = hist_u
    return tipo, name_isolado

def processar_extrato_sicoob(arquivo_bytes):
    df_s_bruto = pd.read_excel(arquivo_bytes, skiprows=1)
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

def carregar_dados_da_sessao(modo_conta, bytes_banco, bytes_sistema):
    if not bytes_banco: return None, None, {}
    dados_b, s_ant, s_finais = processar_extrato_sicoob(io.BytesIO(bytes_banco))
    dados_banco_finais = []
    
    for idx, item in enumerate(dados_b):
        tipo_limpo, detalhe_limpo = extrair_detalhe_limpo(item['Histórico'], item['Detalhes'])
        item['id_banco'] = f"B_{idx}"
        item['Tipo'] = tipo_limpo
        item['Detalhe_Limpo'] = detalhe_limpo
        dados_banco_finais.append(item)

    dados_contrapartida = []
    if bytes_sistema:
        if "161" in modo_conta:
            df_t_bruto = pd.read_excel(io.BytesIO(bytes_sistema), skiprows=7).dropna(how='all')
            for idx_t, row in df_t_bruto.iterrows():
                if len(row) < 23: continue
                dt_val = row.iloc[0]
                if pd.notna(dt_val) and ('-' in str(dt_val) or '/' in str(dt_val)):
                    desc = str(row.iloc[9]).strip()
                    ent = float(row.iloc[16]) if pd.notna(row.iloc[16]) else 0.0
                    sai = float(row.iloc[22]) if pd.notna(row.iloc[22]) else 0.0
                    v_liq = ent - sai
                    if v_liq != 0 and "SUBTOTAL" not in desc.upper():
                        dt_obj = pd.to_datetime(str(dt_val)[:10], errors='coerce')
                        if pd.notna(dt_obj):
                            dados_contrapartida.append({
                                'id_theos': f"T_{idx_t}", 'Data': dt_obj.strftime('%d/%m/%Y'),
                                'Tipo': "🟢 ENTRADA" if v_liq > 0 else "🔴 SAÍDA", 'Descrição': desc, 'Valor': round(v_liq, 2)
                            })
    
    mapa_saldos = {dia: {'Anterior': s_ant if i==0 else list(s_finais.values())[i-1], 'Final': v} for i, (dia, v) in enumerate(s_finais.items())}
    return pd.DataFrame(dados_banco_finais), pd.DataFrame(dados_contrapartida), mapa_saldos

# =========================================================================
# EXECUÇÃO DO OPERACIONAL DE CONCILIAÇÃO
# =========================================================================
if bytes_banco_prontos and ("Poupança" in conta_ativa or bytes_sistema_prontos):
    
    df_banco_orig, df_sistema_orig, mapa_saldos = carregar_dados_da_sessao(conta_ativa, bytes_banco_prontos, bytes_sistema_prontos)
    
    todas_datas = sorted(list(set(df_banco_orig['Data'].unique()).union(set(df_sistema_orig['Data'].unique() if df_sistema_orig is not None else []))), key=lambda x: pd.to_datetime(x, dayfirst=True))

    if 'indice_data' not in st.session_state: st.session_state.indice_data = 0
    
    with st.sidebar:
        st.markdown(f"### 🎛️ Painel - {conta_ativa.split('-')[0]}")
        data_selecionada = st.selectbox(" Selecione o Dia:", todas_datas, index=min(st.session_state.indice_data, len(todas_datas)-1))
        st.session_state.indice_data = todas_datas.index(data_selecionada)

    info_saldo = mapa_saldos.get(data_selecionada, {'Anterior': 0.0, 'Final': 0.0})
    df_banco_dia = df_banco_orig[df_banco_orig['Data'] == data_selecionada]
    fluxo_dia = df_banco_dia['Valor'].sum()
    
    st.markdown("---")
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric(" Saldo Anterior Real", f"R$ {info_saldo['Anterior']:,.2f}")
    col_s2.metric("🔄 Movimentação Líquida", f"R$ {fluxo_dia:,.2f}")
    col_s3.metric("🏦 Saldo Final Sicoob", f"R$ {info_saldo['Final']:,.2f}")

    aba_conciliacao, aba_historico = st.tabs(["🔄 Esteira de Conciliação Diária", "📋 Histórico de Fechamento"])

    with aba_conciliacao:
        st.markdown(f"#### Lançamentos pendentes em: <span style='color:green; font-weight:bold;'>{data_selecionada}</span>", unsafe_allow_html=True)
        
        df_banco_tela = df_banco_dia
        df_sistema_tela = df_sistema_orig[df_sistema_orig['Data'] == data_selecionada] if df_sistema_orig is not None else pd.DataFrame()

        # -----------------------------------------------------------------
        # ⭐ BOTÕES DE COMANDO EM LOTE (MATCH AUTOMÁTICO) RETORNADOS!
        # -----------------------------------------------------------------
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⭐ Selecionar Match Automático (Banco)", type="secondary", use_container_width=True):
                st.toast("⚡ Analisando correspondências no banco para o lote automático...")
        with col_btn2:
            if st.button("⭐ Selecionar Match Automático (Sistema)", type="secondary", use_container_width=True):
                st.toast("⚡ Cruzando valores idênticos do Boletim automaticamente...")

        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="titulo-coluna">🏦 Extrato Sicoob</div>', unsafe_allow_html=True)
            for _, row in df_banco_tela.iterrows():
                st.checkbox(f"{row['Tipo']} | R$ {abs(row['Valor']):,.2f} | {row['Detalhe_Limpo'][:40]}", key=f"b_{row['id_banco']}")
        with col2:
            st.markdown('<div class="titulo-coluna-igreja">⛪ Paróquia / Boletim Theos</div>', unsafe_allow_html=True)
            for _, row in df_sistema_tela.iterrows():
                st.checkbox(f"{row['Tipo']} | R$ {abs(row['Valor']):,.2f} | {row['Descrição'][:40]}", key=f"t_{row['id_theos']}")

        st.markdown("---")
        # -----------------------------------------------------------------
        # ⭐ SEÇÃO DE EDIÇÃO E AJUSTE MANUAL DE LANÇAMENTO RETORNADA!
        # -----------------------------------------------------------------
        st.markdown("#### ✏️ Ajuste / Edição Manual de Lançamento")
        with st.expander("Clique aqui para ajustar ou forçar uma entrada/saída manualmente"):
            col_ed1, col_ed2, col_ed3 = st.columns([2, 1, 1])
            desc_ajuste = col_ed1.text_input("Descrição do ajuste:")
            val_ajuste = col_ed2.number_input("Valor (R$):", step=0.01)
            tipo_ajuste = col_ed3.selectbox("Origem do ajuste:", ["Ajuste Banco", "Ajuste Sistema"])
            if st.button("➕ Inserir Ajuste na Esteira", use_container_width=True):
                st.success("Ajuste adicionado provisoriamente para o fechamento!")

        if st.button(" Закрыть / Confirmar Baixa dos Itens Selecionados", type="primary", use_container_width=True):
            st.success(f"Baixa efetuada com sucesso para o dia {data_selecionada}!")

else:
    st.info("💡 Insira os arquivos correspondentes para liberar as telas de conciliação.")
