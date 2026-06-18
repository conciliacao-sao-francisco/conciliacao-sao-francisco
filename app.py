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

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_store_sipag not in st.session_state: st.session_state[chave_store_sipag] = None
if chave_modificacoes not in st.session_state: st.session_state[chave_modificacoes] = []

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
    # Processador customizado para ler o layout SIPAG recebido com delimitador ';'
    try:
        df_sipag = pd.read_csv(io.BytesIO(arquivo_bytes), sep=';', skiprows=2)
        dados_finais = []
        for idx, row in df_sipag.iterrows():
            if len(row) < 11 or pd.isna(row.iloc[1]): continue
            dt_str = str(row.iloc[1]).split()[0] # Pega apenas a data da transação
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
    # Carregamento primário
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
    
    # Contrapartida do Sistema (Theos)
    dados_contrapartida = []
    df_t_bruto = pd.read_excel(io.BytesIO(st.session_state[chave_store_sistema]), skiprows=7).dropna(how='all')
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
                        'id': f"T_{idx_t}", 'Data': dt_obj.strftime('%d/%m/%Y'),
                        'Tipo': "ENTRADA" if v_liq > 0 else "SAÍDA", 'Descrição': desc, 'Valor': round(v_liq, 2), 'Origem': 'Sistema'
                    })
    df_s_orig = pd.DataFrame(dados_contrapartida)

    # SIPAG condicional
    df_sipag_orig = pd.DataFrame()
    if st.session_state[chave_store_sipag]:
        df_sipag_orig = processar_sipag_csv(st.session_state[chave_store_sipag])

    # ⚙️ Aplicar histórico de modificações salvas na sessão (Edições, inclusões e Troca de Data)
    for mod in st.session_state[chave_modificacoes]:
        if mod['acao'] == 'excluir':
            df_b_orig = df_b_orig[df_b_orig['id'] != mod['id']]
            if not df_s_orig.empty: df_s_orig = df_s_orig[df_s_orig['id'] != mod['id']]
            if not df_sipag_orig.empty: df_sipag_orig = df_sipag_orig[df_sipag_orig['id'] != mod['id']]
        elif mod['acao'] == 'editar':
            df_b_orig.loc[df_b_orig['id'] == mod['id'], ['Descrição', 'Valor', 'Data']] = [mod['desc'], mod['valor'], mod['data']]
            if not df_s_orig.empty: df_s_orig.loc[df_s_orig['id'] == mod['id'], ['Descrição', 'Valor', 'Data']] = [mod['desc'], mod['valor'], mod['data']]
            if not df_sipag_orig.empty: df_sipag_orig.loc[df_sipag_orig['id'] == mod['id'], ['Descrição', 'Valor', 'Data']] = [mod['desc'], mod['valor'], mod['data']]
        elif mod['acao'] == 'inserir':
            nova_linha = pd.DataFrame([{'id': mod['id'], 'Data': mod['data'], 'Tipo': '🔹 AJUSTE', 'Descrição': mod['desc'], 'Valor': mod['valor'], 'Origem': mod['origem']}])
            if mod['origem'] == 'Banco': df_b_orig = pd.concat([df_b_orig, nova_linha], ignore_index=True)
            elif mod['origem'] == 'Sistema': df_s_orig = pd.concat([df_s_orig, nova_linha], ignore_index=True)
            else: df_sipag_orig = pd.concat([df_sipag_orig, nova_linha], ignore_index=True)

    todas_datas = sorted(list(set(df_b_orig['Data'].unique()).union(set(df_s_orig['Data'].unique()))), key=lambda x: pd.to_datetime(x, dayfirst=True))
    
    if 'indice_data' not in st.session_state: st.session_state.indice_data = 0
    with st.sidebar:
        st.markdown(f"### 🎛️ Painel - {conta_ativa.split('-')[0]}")
        data_selecionada = st.selectbox("📆 Selecione o Dia:", todas_datas, index=min(st.session_state.indice_data, len(todas_datas)-1))
        st.session_state.indice_data = todas_datas.index(data_selecionada)

    # Dados do Dia
    mapa_saldos = {dia: {'Anterior': s_ant if i==0 else list(s_finais.values())[i-1], 'Final': v} for i, (dia, v) in enumerate(s_finais.items())}
    info_saldo = mapa_saldos.get(data_selecionada, {'Anterior': 0.0, 'Final': 0.0})
    df_banco_dia = df_b_orig[df_b_orig['Data'] == data_selecionada]
    
    st.markdown("---")
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("💰 Saldo Anterior Real", f"R$ {info_saldo['Anterior']:,.2f}")
    col_s2.metric("🔄 Movimentação Líquida", f"R$ {df_banco_dia['Valor'].sum():,.2f}")
    col_s3.metric("🏦 Saldo Final Sicoob", f"R$ {info_saldo['Final']:,.2f}")

    aba_conciliacao, aba_historico = st.tabs(["🔄 Esteira de Conciliação Diária", "📋 Histórico de Fechamento"])

    with aba_conciliacao:
        st.markdown(f"### Lançamentos em: <span style='color:#1e7e34;'>{data_selecionada}</span>", unsafe_allow_html=True)
        
        # --- FILTROS INDEPENDENTES (LAYOUT IGUAL AO PRINT) ---
        c_flt1, c_flt2, c_flt3 = st.columns(3)
        filtro_banco = c_flt1.selectbox("🎯 Filtrar Extrato Sicoob:", ["Todos", "🟢 PIX RECEBIDO", "🔴 PIX ENVIADO", "🔴 PAGTO TITULO", "💳 SIPAG LOTE"], key="flt_b")
        filtro_sist = c_flt2.selectbox("🎯 Filtrar Sistema:", ["Todos", "ENTRADA", "SAÍDA"], key="flt_s")
        filtro_sip = c_flt3.selectbox("🎯 Filtrar SIPAG Cartão:", ["Todos", "💳 LOTE VISA", "💳 LOTE MASTER", "💳 LOTE ELO"], key="flt_sip")

        df_banco_tela = df_banco_dia if filtro_banco == "Todos" else df_banco_dia[df_banco_dia['Tipo'] == filtro_banco]
        df_sistema_tela = df_s_orig[df_s_orig['Data'] == data_selecionada]
        if filtro_sist != "Todos": df_sistema_tela = df_sistema_tela[df_sistema_tela['Tipo'] == filtro_sist]
        
        df_sipag_tela = df_sipag_orig[df_sipag_orig['Data'] == data_selecionada] if not df_sipag_orig.empty else pd.DataFrame()
        if filtro_sip != "Todos" and not df_sipag_tela.empty: df_sipag_tela = df_sipag_tela[df_sipag_tela['Tipo'] == filtro_sip]

        # --- RECURSO SOLICITADO: CONCILIAÇÃO POR SELEÇÃO DINÂMICA VIA CHECKBOX ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="titulo-coluna">🏦 Extrato Sicoob</div>', unsafe_allow_html=True)
            st.info(f"📊 Saldo do Extrato Filtrado: R$ {df_banco_tela['Valor'].sum():,.2f}")
            
            selecionados_banco = []
            for _, row in df_banco_tela.iterrows():
                if st.checkbox(f"{row['Tipo']} | R$ {abs(row['Valor']):,.2f} | {row['Descrição'][:25]}", key=f"chk_{row['id']}"):
                    selecionados_banco.append(row['Valor'])
            
            soma_banco = sum(selecionados_banco)
            st.markdown(f'<div style="background-color:#e3f2fd; padding:8px; border-radius:5px; font-weight:bold; color:#0d47a1;">🔹 Selecionados: {len(selecionados_banco)} itens | Soma Atual: R$ {soma_banco:,.2f}</div>', unsafe_allow_html=True)
                
        with col2:
            st.markdown('<div class="titulo-coluna-igreja">⛪ Paróquia / Boletim Theos</div>', unsafe_allow_html=True)
            st.info(f"📊 Saldo do Boletim Filtrado: R$ {df_sistema_tela['Valor'].sum():,.2f}")
            
            selecionados_sist = []
            for _, row in df_sistema_tela.iterrows():
                if st.checkbox(f"{row['Tipo']} | R$ {abs(row['Valor']):,.2f} | {row['Descrição'][:25]}", key=f"chk_{row['id']}"):
                    selecionados_sist.append(row['Valor'])
            
            soma_sist = sum(selecionados_sist)
            st.markdown(f'<div style="background-color:#fbe9e7; padding:8px; border-radius:5px; font-weight:bold; color:#d84315;">🔹 Selecionados: {len(selecionados_sist)} itens | Soma Atual: R$ {soma_sist:,.2f}</div>', unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="titulo-coluna-sipag">💳 Conferência Cartão SIPAG</div>', unsafe_allow_html=True)
            if not df_sipag_tela.empty:
                st.info(f"📊 Total SIPAG do Dia: R$ {df_sipag_tela['Valor'].sum():,.2f}")
                selecionados_sip = []
                for _, row in df_sipag_tela.iterrows():
                    if st.checkbox(f"{row['Tipo']} | R$ {row['Valor']:,.2f} | {row['Descrição'][:25]}", key=f"chk_{row['id']}"):
                        selecionados_sip.append(row['Valor'])
                soma_sip = sum(selecionados_sip)
                st.markdown(f'<div style="background-color:#e8f5e9; padding:8px; border-radius:5px; font-weight:bold; color:#1b5e20;">🔹 Selecionados: {len(selecionados_sip)} itens | Soma Atual: R$ {soma_sip:,.2f}</div>', unsafe_allow_html=True)
            else:
                st.warning("Nenhum lote SIPAG ou planilha inserida para este dia.")

        # --- CENTRAL DE AJUSTES INTEGRADA ---
        st.markdown("---")
        st.markdown("### ✏️ Central de Ajustes, Edição e Alteração de Data")
        aba_ins, aba_edt = st.tabs(["➕ Inserir Novo Ajuste", "📝 Editar / Excluir / Mudar Data de Existentes"])
        
        with aba_ins:
            col_ed1, col_ed2, col_ed3, col_ed4 = st.columns([2, 1, 1, 1])
            desc_ajuste = col_ed1.text_input("Descrição do ajuste:", key="ins_desc")
            val_ajuste = col_ed2.number_input("Valor (R$):", step=0.01, key="ins_val")
            tipo_ajuste = col_ed3.selectbox("Origem do ajuste:", ["Ajuste Banco", "Ajuste Sistema", "Ajuste Sipag"], key="ins_orig")
            dt_ajuste = col_ed4.date_input("Data do Lançamento:", value=datetime.date(2026, 4, 2), key="ins_data")
            
            if st.button("➕ Inserir Ajuste na Esteira", use_container_width=True):
                id_gerado = f"M_INS_{len(st.session_state[chave_modificacoes])}"
                origem_convertida = 'Banco' if "Banco" in tipo_ajuste else ('Sistema' if "Sistema" in tipo_ajuste else 'Sipag')
                st.session_state[chave_modificacoes].append({
                    'id': id_gerado, 'acao': 'inserir', 'desc': desc_ajuste.upper(),
                    'valor': val_ajuste, 'origem': origem_convertida, 'data': dt_ajuste.strftime('%d/%m/%Y')
                })
                st.success("Ajuste inserido!")
                st.rerun()

        with aba_edt:
            lista_dfs = [df for df in [df_banco_tela, df_sistema_tela, df_sipag_tela] if not df.empty]
            df_todos_dia = pd.concat(lista_dfs, ignore_index=True) if lista_dfs else pd.DataFrame()
            
            if not df_todos_dia.empty:
                item_selecionado = st.selectbox(
                    "Escolha qual lançamento deseja alterar/remover:", df_todos_dia['id'].tolist(),
                    format_func=lambda x: f"[{df_todos_dia[df_todos_dia['id']==x]['Origem'].values[0]}] {df_todos_dia[df_todos_dia['id']==x]['Descrição'].values[0][:30]} | R$ {df_todos_dia[df_todos_dia['id']==x]['Valor'].values[0]}"
                )
                row_sel = df_todos_dia[df_todos_dia['id'] == item_selecionado].iloc[0]
                
                col_upd1, col_upd2, col_upd3 = st.columns([2, 1, 1])
                nova_desc = col_upd1.text_input("Alterar Descrição para:", value=row_sel['Descrição'])
                novo_val = col_upd2.number_input("Alterar Valor para:", value=float(row_sel['Valor']), step=0.01)
                nova_data = col_upd3.date_input("Mudar Data para:", value=datetime.datetime.strptime(row_sel['Data'], '%d/%m/%Y').date())
                
                col_b_ed1, col_b_ed2 = st.columns(2)
                if col_b_ed1.button("💾 Gravar Modificações / Mudar Data", type="primary", use_container_width=True):
                    st.session_state[chave_modificacoes] = [m for m in st.session_state[chave_modificacoes] if m['id'] != item_selecionado]
                    st.session_state[chave_modificacoes].append({'id': item_selecionado, 'acao': 'editar', 'desc': nova_desc.upper(), 'valor': novo_val, 'data': nova_data.strftime('%d/%m/%Y')})
                    st.success("Alterado com sucesso!")
                    st.rerun()
                if col_b_ed2.button("🗑️ Excluir este lançamento", use_container_width=True):
                    st.session_state[chave_modificacoes] = [m for m in st.session_state[chave_modificacoes] if m['id'] != item_selecionado]
                    st.session_state[chave_modificacoes].append({'id': item_selecionado, 'acao': 'excluir'})
                    st.rerun()
            else: st.info("Nenhum lançamento para alteração hoje.")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📌 Confirmar Baixa dos Itens Selecionados", type="primary", use_container_width=True):
            st.success(f"Baixa efetuada com sucesso para o dia {data_selecionada}!")
else:
    st.info("💡 Insira ao menos o Extrato do Sicoob e o Relatório do Boletim (Theos) para liberar as telas de conciliação.")
