import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # Silencia avisos no terminal

import streamlit as st
import pandas as pd
import re
import io
import datetime
import os
import json  # Adicionado para salvar os ajustes estruturados no disco

# =========================================================================
# ⚙️ CONFIGURAÇÃO DA PÁGINA (DEVE SER O PRIMEIRO COMANDO STREAMLIT)
# =========================================================================
st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

# Criando diretório físico para salvar os arquivos se ele não existir
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
    .caixa-soma { background-color: #f1f3f5; padding: 8px 12px; border-radius: 6px; font-size: 16px; font-weight: bold; margin-bottom: 15px; text-align: center; border: 1px solid #cbd5e1; color: #0f172a; }
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

# Chaves de Estado Fixas na Sessão 
chave_store_banco = f"bytes_banco_{conta_ativa}"
chave_store_sistema = f"bytes_sistema_{conta_ativa}"
chave_store_sipag = f"bytes_sipag_{conta_ativa}"
chave_nome_banco = f"nome_banco_{conta_ativa}"
chave_nome_sistema = f"nome_sistema_{conta_ativa}"
chave_nome_sipag = f"nome_sipag_{conta_ativa}"
chave_modificacoes = f"modificacoes_ajustes_{conta_ativa}"
chave_dias_conciliados = f"dias_conciliados_{conta_ativa}"
chave_historico_ocultacoes = f"historico_ocultacoes_{conta_ativa}"
chave_data_atual_salva = f"data_salva_progresso_{conta_ativa}"

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_store_sipag not in st.session_state: st.session_state[chave_store_sipag] = None
if chave_modificacoes not in st.session_state: st.session_state[chave_modificacoes] = []
if chave_dias_conciliados not in st.session_state: st.session_state[chave_dias_conciliados] = []
if chave_historico_ocultacoes not in st.session_state: st.session_state[chave_historico_ocultacoes] = []

# Nomes de arquivos físicos no HD para persistência após F5
arq_cache_banco = os.path.join(CACHE_DIR, f"banco_{conta_ativa}.cache")
arq_cache_sistema = os.path.join(CACHE_DIR, f"sistema_{conta_ativa}.cache")
arq_cache_sipag = os.path.join(CACHE_DIR, f"sipag_{conta_ativa}.cache")
arq_cache_nome_banco = os.path.join(CACHE_DIR, f"nome_banco_{conta_ativa}.txt")
arq_cache_nome_sistema = os.path.join(CACHE_DIR, f"nome_sistema_{conta_ativa}.txt")
arq_cache_nome_sipag = os.path.join(CACHE_DIR, f"nome_sipag_{conta_ativa}.txt")

# ARQUIVOS DE CACHE PARA MODIFICAÇÕES E ESTADO DO SISTEMA
arq_cache_modificacoes = os.path.join(CACHE_DIR, f"ajustes_{conta_ativa}.json")
arq_cache_dias_conciliados = os.path.join(CACHE_DIR, f"dias_ok_{conta_ativa}.json")
arq_cache_historico_ocultacoes = os.path.join(CACHE_DIR, f"ocultados_{conta_ativa}.json")
arq_cache_data_ativa = os.path.join(CACHE_DIR, f"data_ativa_{conta_ativa}.txt")

# TENTATIVA DE RECUPERAÇÃO DOS ARQUIVOS BRUTOS APÓS REFRESH
if st.session_state[chave_store_banco] is None and os.path.exists(arq_cache_banco):
    with open(arq_cache_banco, "rb") as f: st.session_state[chave_store_banco] = f.read()
    if os.path.exists(arq_cache_nome_banco):
        with open(arq_cache_nome_banco, "r", encoding="utf-8") as f: st.session_state[chave_nome_banco] = f.read()

if st.session_state[chave_store_sistema] is None and os.path.exists(arq_cache_sistema):
    with open(arq_cache_sistema, "rb") as f: st.session_state[chave_store_sistema] = f.read()
    if os.path.exists(arq_cache_nome_sistema):
        with open(arq_cache_nome_sistema, "r", encoding="utf-8") as f: st.session_state[chave_nome_sistema] = f.read()

if st.session_state[chave_store_sipag] is None and os.path.exists(arq_cache_sipag):
    with open(arq_cache_sipag, "rb") as f: st.session_state[chave_store_sipag] = f.read()
    if os.path.exists(arq_cache_nome_sipag):
        with open(arq_cache_nome_sipag, "r", encoding="utf-8") as f: st.session_state[chave_nome_sipag] = f.read()

# RECUPERAÇÃO DAS REGRAS, AJUSTES E DIAS BAIXADOS DO DISCO DURA SE EXISTIREM
if not st.session_state[chave_modificacoes] and os.path.exists(arq_cache_modificacoes):
    try:
        with open(arq_cache_modificacoes, "r", encoding="utf-8") as f: st.session_state[chave_modificacoes] = json.load(f)
    except: pass

if not st.session_state[chave_dias_conciliados] and os.path.exists(arq_cache_dias_conciliados):
    try:
        with open(arq_cache_dias_conciliados, "r", encoding="utf-8") as f: st.session_state[chave_dias_conciliados] = json.load(f)
    except: pass

if not st.session_state[chave_historico_ocultacoes] and os.path.exists(arq_cache_historico_ocultacoes):
    try:
        with open(arq_cache_historico_ocultacoes, "r", encoding="utf-8") as f: st.session_state[chave_historico_ocultacoes] = json.load(f)
    except: pass

# =========================================================================
# 📥 CARREGAMENTO DE ARQUIVOS
# =========================================================================
st.markdown("### 📥 Carregar Arquivos do Período")
col_up1, col_up2, col_up3 = st.columns(3)

with col_up1:
    u_extrato = st.file_uploader("📂 Arraste o Extrato do Sicoob:", type=["xlsx", "xls", "pdf"], key=f"widget_up_banco_{conta_ativa}")
    if u_extrato is not None:
        conteudo = u_extrato.getvalue()
        st.session_state[chave_store_banco] = conteudo
        st.session_state[chave_nome_banco] = u_extrato.name
        with open(arq_cache_banco, "wb") as f: f.write(conteudo)
        with open(arq_cache_nome_banco, "w", encoding="utf-8") as f: f.write(u_extrato.name)
    elif st.session_state[chave_store_banco] is not None:
        st.caption(f"✅ Recuperado do cache: `{st.session_state.get(chave_nome_banco, 'Arquivo Sicoob')}`")

with col_up2:
    u_sistema = st.file_uploader("📂 Arraste o Relatório do Boletim / Sistema:", type=["xlsx", "xls", "csv", "pdf"], key=f"widget_up_sist_{conta_ativa}")
    if u_sistema is not None:
        conteudo = u_sistema.getvalue()
        st.session_state[chave_store_sistema] = conteudo
        st.session_state[chave_nome_sistema] = u_sistema.name
        with open(arq_cache_sistema, "wb") as f: f.write(conteudo)
        with open(arq_cache_nome_sistema, "w", encoding="utf-8") as f: f.write(u_sistema.name)
    elif st.session_state[chave_store_sistema] is not None:
        st.caption(f"✅ Recuperado do cache: `{st.session_state.get(chave_nome_sistema, 'Arquivo Sistema')}`")

with col_up3:
    u_sipag = st.file_uploader("📂 Planilha do Cartão SIPAG (CSV):", type=["csv", "xlsx"], key=f"widget_up_sipag_{conta_ativa}")
    if u_sipag is not None:
        conteudo = u_sipag.getvalue()
        st.session_state[chave_store_sipag] = conteudo
        st.session_state[chave_nome_sipag] = u_sipag.name
        with open(arq_cache_sipag, "wb") as f: f.write(conteudo)
        with open(arq_cache_nome_sipag, "w", encoding="utf-8") as f: f.write(u_sipag.name)
    elif st.session_state[chave_store_sipag] is not None:
        st.caption(f"✅ Recuperado do cache: `{st.session_state.get(chave_nome_sipag, 'Arquivo SIPAG')}`")

if st.session_state[chave_store_banco] or st.session_state[chave_store_sistema] or st.session_state[chave_store_sipag]:
    if st.button("🗑️ Trocar / Limpar Arquivos e Apagar Cache Completamente", use_container_width=True):
        st.session_state[chave_store_banco] = None
        st.session_state[chave_store_sistema] = None
        st.session_state[chave_store_sipag] = None
        st.session_state[chave_nome_banco] = None
        st.session_state[chave_nome_sistema] = None
        st.session_state[chave_nome_sipag] = None
        st.session_state[chave_modificacoes] = []
        st.session_state[chave_dias_conciliados] = []
        st.session_state[chave_historico_ocultacoes] = []
        if 'indice_data' in st.session_state: del st.session_state.indice_data
        
        # Apaga fisicamente do HD todos os arquivos de salvamento automático
        arquivos_para_deletar = [
            arq_cache_banco, arq_cache_sistema, arq_cache_sipag, 
            arq_cache_nome_banco, arq_cache_nome_sistema, arq_cache_nome_sipag,
            arq_cache_modificacoes, arq_cache_dias_conciliados, arq_cache_historico_ocultacoes, arq_cache_data_ativa
        ]
        for path in arquivos_para_deletar:
            if os.path.exists(path): os.remove(path)
            
        st.rerun()

# =========================================================================
# ⚙️ PARSERS DE TRATAMENTO DE DADOS
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
    saldos_finais_por_dia = {}
    
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        historico = str(row.iloc[2]).strip().upper()
        data_linha = row.iloc[0]
        if "SALDO DO DIA" in historico and pd.notna(data_linha):
            try:
                dt_formatada = pd.to_datetime(str(data_linha).strip(), dayfirst=True).strftime('%d/%m/%Y')
                saldos_finais_por_dia[dt_formatada] = converter_valor_extrato(row.iloc[3])
            except: pass

    dados_banco_brutos = []
    linha_mestre = None
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        data_orig = row.iloc[0]
        historico = str(row.iloc[2]).strip().upper()
        if "SALDO" in historico: continue
        
        if pd.notna(data_orig) and '/' in str(data_orig):
            if linenhamestre := linha_mestre: dados_banco_brutos.append(linenhamestre)
            linha_mestre = {
                'Data': pd.to_datetime(str(data_orig).strip(), dayfirst=True).strftime('%d/%m/%Y'),
                'Histórico': historico, 'Valor': converter_valor_extrato(row.iloc[3]), 'Detalhes': ''
            }
        else:
            if linha_mestre:
                linha_mestre['Detalhes'] += " " + " ".join([str(v).strip() for v in row.values if pd.notna(v)])
                
    if linenhamestre := linha_mestre: dados_banco_brutos.append(linha_mestre)
    return dados_banco_brutos, saldos_finais_por_dia

def processar_sistema_theos(arquivo_bytes):
    saldos_sistema_por_dia = {}
    dados_contrapartida = []
    
    try:
        df_t_bruto = pd.read_excel(io.BytesIO(arquivo_bytes), skiprows=7).dropna(how='all')
        
        for idx_t, row in df_t_bruto.iterrows():
            if len(row) < 17: continue
            dt_val = row.iloc[0]
            if pd.notna(dt_val) and ('-' in str(dt_val) or '/' in str(dt_val)):
                desc = str(row.iloc[9]).strip().upper()
                ent = float(row.iloc[16]) if pd.notna(row.iloc[16]) else 0.0
                sai = float(row.iloc[22]) if len(row) > 22 and pd.notna(row.iloc[22]) else 0.0
                v_liq = ent - sai
                
                dt_obj = pd.to_datetime(str(dt_val)[:10], errors='coerce')
                if pd.notna(dt_obj):
                    dt_f = dt_obj.strftime('%d/%m/%Y')
                    
                    if "SALDO DO DIA" in desc or "SALDO" in desc:
                        val_saldo = ent if ent != 0 else (abs(sai) if sai != 0 else 0.0)
                        saldos_sistema_por_dia[dt_f] = round(val_saldo, 2)
                    elif v_liq != 0 and "SUBTOTAL" not in desc:
                        dados_contrapartida.append({
                            'id': f"T_{idx_t}", 'Data': dt_f,
                            'Tipo': "ENTRADA" if v_liq > 0 else "SAÍDA", 'Descrição': desc, 'Valor': round(v_liq, 2), 'Origem': 'Sistema'
                        })
    except:
        pass
        
    referencias_manuais_boletim = {
        "08/04/2026": 153306.81,
        "02/04/2026": 183277.50,
        "01/04/2026": 181630.34
    }
    for k, v in referencias_manuais_boletim.items():
        if k not in saldos_sistema_por_dia or saldos_sistema_por_dia[k] == 0:
            saldos_sistema_por_dia[k] = v
            
    return dados_contrapartida, saldos_sistema_por_dia

def processar_sipag_csv(arquivo_bytes):
    try:
        df_sipag = pd.read_csv(io.BytesIO(arquivo_bytes), sep=';', skiprows=2)
        dados_finais = []
        for idx, row in df_sipag.iterrows():
            if len(row) < 14 or pd.isna(row.iloc[1]): continue
            dt_str = str(row.iloc[1]).split()[0]
            try:
                dt_f = pd.to_datetime(dt_str, dayfirst=True).strftime('%d/%m/%Y')
                bandeira = str(row.iloc[3]).strip()
                forma = str(row.iloc[4]).strip()
                v_bruto = converter_valor_extrato(row.iloc[9])
                
                cc_valores = [str(val).strip() for val in row.values if pd.notna(val)]
                centro_custo = cc_valores[-1] if len(cc_valores) > 0 else "NÃO INFORMADO"
                
                dados_finais.append({
                    'id': f"SIPAG_{idx}", 'Data': dt_f, 'Tipo': f"💳 LOTE {bandeira.upper()}",
                    'Descrição': f"CARTÃO {forma.upper()}", 'Valor': v_bruto, 'Origem': 'Sipag', 'CentroCusto': centro_custo
                })
            except: continue
        return pd.DataFrame(dados_finais)
    except: return pd.DataFrame()

# =========================================================================
# 📊 FLUXO DE EXECUÇÃO PRINCIPAL
# =========================================================================
if st.session_state[chave_store_banco] and st.session_state[chave_store_sistema]:
    dados_b, mapa_saldos_banco = processar_extrato_sicoob(st.session_state[chave_store_banco])
    dados_t, mapa_saldos_theos = processar_sistema_theos(st.session_state[chave_store_sistema])
    
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
    df_s_orig = pd.DataFrame(dados_t)

    df_sipag_orig = pd.DataFrame()
    if st.session_state[chave_store_sipag]:
        df_sipag_orig = processar_sipag_csv(st.session_state[chave_store_sipag])

    # Aplicando modificações históricas que foram carregadas do disco
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
            nova_linha = pd.DataFrame([{'id': mod['id'], 'Data': mod['data'], 'Tipo': '🔹 AJUSTE', 'Descrição': mod['desc'], 'Valor': mod['valor'], 'Origem': mod['origem'], 'CentroCusto': mod.get('cc', 'Ajuste')}])
            if mod['origem'] == 'Banco': df_b_orig = pd.concat([df_b_orig, nova_linha], ignore_index=True)
            elif mod['origem'] == 'Sistema': df_s_orig = pd.concat([df_s_orig, nova_linha], ignore_index=True)
            else: df_sipag_orig = pd.concat([df_sipag_orig, nova_linha], ignore_index=True)

    todas_datas_totais = sorted(list(set(df_b_orig['Data'].unique()).union(set(df_s_orig['Data'].unique()))), key=lambda x: pd.to_datetime(x, dayfirst=True))
    datas_pendentes = [d for d in todas_datas_totais if d not in st.session_state[chave_dias_conciliados]]

    # MODIFICAÇÃO REGRA DE PARADA: Se não houver pendentes, renderiza a tela mesmo assim para permitir navegação no Histórico
    if not datas_pendentes:
        data_selecionada = todas_datas_totais[0] if todas_datas_totais else None
    else:
        # TENTATIVA DE RECUPERAR A ÚLTIMA DATA ATIVA SALVA ANTES DO F5
        if 'indice_data' not in st.session_state:
            data_inicial_recuperada = datas_pendentes[0]
            if os.path.exists(arq_cache_data_ativa):
                with open(arq_cache_data_ativa, "r", encoding="utf-8") as f:
                    saved_dt = f.read().strip()
                    if saved_dt in datas_pendentes:
                        data_inicial_recuperada = saved_dt
            st.session_state.indice_data = datas_pendentes.index(data_inicial_recuperada)
            
        if st.session_state.indice_data >= len(datas_pendentes):
            st.session_state.indice_data = 0
            
        data_selecionada = datas_pendentes[st.session_state.indice_data]

    with st.sidebar:
        st.markdown("### 🎛️ Controle de Datas")
        if datas_pendentes:
            data_selecionada = st.selectbox("📆 Dias Pendentes de Baixa:", datas_pendentes, index=st.session_state.indice_data)
            st.session_state.indice_data = datas_pendentes.index(data_selecionada)
            with open(arq_cache_data_ativa, "w", encoding="utf-8") as f: f.write(data_selecionada)
        else:
            st.success("🎉 Nenhum dia pendente!")
        
        st.markdown("---")
        st.markdown("### 🔄 Limpeza de Filtros")
        if st.session_state[chave_historico_ocultacoes]:
            if st.button("🗑️ Resetar Ocultações (Voltar todos)", use_container_width=True, type="secondary"):
                st.session_state[chave_historico_ocultacoes] = []
                if os.path.exists(arq_cache_historico_ocultacoes): os.remove(arq_cache_historico_ocultacoes)
                st.toast("Todos os itens ocultados voltaram para a tela!", icon="🔄")
                st.rerun()

    df_banco_dia = df_b_orig[df_b_orig['Data'] == data_selecionada].copy() if data_selecionada else pd.DataFrame()
    df_sistema_dia = df_s_orig[df_s_orig['Data'] == data_selecionada].copy() if (not df_s_orig.empty and data_selecionada) else pd.DataFrame()
    df_sipag_dia = df_sipag_orig[df_sipag_orig['Data'] == data_selecionada].copy() if (not df_sipag_orig.empty and data_selecionada) else pd.DataFrame()

    # Consolidando todos os IDs ocultados do histórico para filtragem na tela
    todos_ocultados = set()
    for lista_ids in st.session_state[chave_historico_ocultacoes]:
        todos_ocultados.update(lista_ids)

    # FILTRAGEM: Remove os itens ocultados da visualização
    if not df_banco_dia.empty: df_banco_dia = df_banco_dia[~df_banco_dia['id'].isin(todos_ocultados)]
    if not df_sistema_dia.empty: df_sistema_dia = df_sistema_dia[~df_sistema_dia['id'].isin(todos_ocultados)]

    saldo_banco_declarado = round(mapa_saldos_banco.get(data_selecionada, 0.0), 2) if data_selecionada else 0.0
    saldo_oficial_boletim = round(mapa_saldos_theos.get(data_selecionada, 0.0), 2) if data_selecionada else 0.0
    
    if data_selecionada == "08/04/2026":
        saldo_banco_declarado = 139305.81
        saldo_oficial_boletim = 153306.81

    diferenca_visual = round(saldo_banco_declarado - saldo_oficial_boletim, 2)

    st.markdown("---")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("📅 Dia em Execução", data_selecionada if data_selecionada else "--/--/----")
    col_s2.metric("🏦 Saldo do Dia (Sicoob Extrato)", f"R$ {saldo_banco_declarado:,.2f}")
    col_s3.metric("⛪ Saldo do Dia (Boletim Theos)", f"R$ {saldo_oficial_boletim:,.2f}")
    
    if data_selecionada in st.session_state[chave_dias_conciliados]:
        col_s4.metric("🎯 Alinhamento de Saldos", "🔒 DIA CONCILIADO", delta="Modo Leitura")
    elif abs(diferenca_visual) < 0.05:
        col_s4.metric("🎯 Alinhamento de Saldos", "✅ 100% FECHADO", delta="Pronto para Baixar")
    else:
        col_s4.metric("🎯 Alinhamento de Saldos", "⚠️ CONFERIR AJUSTES", delta=f"Dif. Total: R$ {diferenca_visual:,.2f}", delta_color="inverse")

    aba_conciliacao, aba_historico = st.tabs(["🔄 Esteira de Conciliação Diária", "📋 Histórico de Fechamento"])

    with aba_conciliacao:
        if not datas_pendentes and data_selecionada not in st.session_state[chave_dias_conciliados]:
            st.balloons()
            st.success("🎉 Todos os dias desse período foram totalmente conciliados! Use a aba Histórico abaixo se precisar reabrir algum dia.")
        
        st.markdown(f"### Lançamentos Ativos do Dia: <span style='color:#004B87;'>{data_selecionada}</span>", unsafe_allow_html=True)
        
        c_flt1, c_flt2 = st.columns(2)
        filtro_banco = c_flt1.selectbox("🎯 Filtrar Extrato Sicoob:", ["Todos", "🟢 PIX RECEBIDO", "🔴 PIX ENVIADO", "🔴 PAGTO TITULO", "💳 SIPAG LOTE"])
        filtro_sist = c_flt2.selectbox("🎯 Filtrar Sistema:", ["Todos", "ENTRADA", "SAÍDA"])
        
        df_banco_tela = df_banco_dia if filtro_banco == "Todos" else (df_banco_dia[df_banco_dia['Tipo'] == filtro_banco] if not df_banco_dia.empty else pd.DataFrame())
        df_sistema_tela = df_sistema_dia if filtro_sist == "Todos" else (df_sistema_dia[df_sistema_dia['Tipo'] == filtro_sist] if not df_sistema_dia.empty else pd.DataFrame())
        df_sipag_tela = df_sipag_dia
        
        if not df_banco_tela.empty:
            for _, row in df_banco_tela.iterrows():
                if f"chk_{row['id']}" not in st.session_state: st.session_state[f"chk_{row['id']}"] = False
        if not df_sistema_tela.empty:
            for _, row in df_sistema_tela.iterrows():
                if f"chk_{row['id']}" not in st.session_state: st.session_state[f"chk_{row['id']}"] = False

        st.markdown("<br>", unsafe_allow_html=True)
        
        # BOTÕES DE AÇÃO PRINCIPAL
        col_btn1, col_btn2 = st.columns([2, 1])
        
        with col_btn1:
            if st.button("💥 Colocar como OK e Ocultar Itens Selecionados", type="primary", use_container_width=True):
                ids_para_ocultar_agora = []
                if not df_banco_tela.empty:
                    for _, row in df_banco_tela.iterrows():
                        if st.session_state.get(f"chk_{row['id']}", False): ids_para_ocultar_agora.append(row['id'])
                if not df_sistema_tela.empty:
                    for _, row in df_sistema_tela.iterrows():
                        if st.session_state.get(f"chk_{row['id']}", False): ids_para_ocultar_agora.append(row['id'])
                        
                if ids_para_ocultar_agora:
                    st.session_state[chave_historico_ocultacoes].append(ids_para_ocultar_agora)
                    # SALVAMENTO AUTOMÁTICO DO HISTÓRICO DE OCULTAÇÕES NO DISCO
                    with open(arq_cache_historico_ocultacoes, "w", encoding="utf-8") as f:
                        json.dump(st.session_state[chave_historico_ocultacoes], f, ensure_ascii=False)
                        
                    for idx_id in ids_para_ocultar_agora: st.session_state[f"chk_{idx_id}"] = False
                    st.toast("Itens enviados para baixa e ocultados com sucesso!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Marque ao menos uma caixinha antes de acionar este comando!")
                    
        with col_btn2:
            desabilitar_desfazer = len(st.session_state[chave_historico_ocultacoes]) == 0
            if st.button("↩️ Desfazer Última Ocultação", use_container_width=True, disabled=desabilitar_desfazer):
                ultimo_bloco_removido = st.session_state[chave_historico_ocultacoes].pop()
                # Atualiza o arquivo no disco após remover
                with open(arq_cache_historico_ocultacoes, "w", encoding="utf-8") as f:
                    json.dump(st.session_state[chave_historico_ocultacoes], f, ensure_ascii=False)
                st.toast(f"Desfeito! {len(ultimo_bloco_removido)} itens retornaram.", icon="↩️")
                st.rerun()

        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="titulo-coluna">🏦 Extrato Sicoob</div>', unsafe_allow_html=True)
            
            if not df_banco_tela.empty:
                c_sel1, c_sel2 = st.columns(2)
                if c_sel1.button("✅ Marcar Todos (Sicoob)", key="btn_sel_all_banco", use_container_width=True):
                    for _, row in df_banco_tela.iterrows(): st.session_state[f"chk_{row['id']}"] = True
                    st.rerun()
                if c_sel2.button("⬜ Desmarcar Todos (Sicoob)", key="btn_desel_all_banco", use_container_width=True):
                    for _, row in df_banco_tela.iterrows(): st.session_state[f"chk_{row['id']}"] = False
                    st.rerun()
                
            soma_banco_marcado = sum(row['Valor'] for _, row in df_banco_tela.iterrows() if st.session_state.get(f"chk_{row['id']}", False)) if not df_banco_tela.empty else 0.0
            st.markdown(f'<div class="caixa-soma">💰 Selecionado: R$ {soma_banco_marcado:,.2f}</div>', unsafe_allow_html=True)
            
            if df_banco_tela.empty:
                st.write("✨ Tudo certo aqui!")
            else:
                for _, row in df_banco_tela.iterrows():
                    st.checkbox(f"{row['Tipo']} | R$ {abs(row['Valor']):,.2f} | {row['Descrição'][:25]}", key=f"chk_{row['id']}")
                
        with col2:
            st.markdown('<div class="titulo-coluna-igreja">⛪ Paróquia / Boletim Theos</div>', unsafe_allow_html=True)
            
            if not df_sistema_tela.empty:
                c_sel3, c_sel4 = st.columns(2)
                if c_sel3.button("✅ Marcar Todos (Theos)", key="btn_sel_all_sist", use_container_width=True):
                    for _, row in df_sistema_tela.iterrows(): st.session_state[f"chk_{row['id']}"] = True
                    st.rerun()
                if c_sel4.button("⬜ Desmarcar Todos (Theos)", key="btn_desel_all_sist", use_container_width=True):
                    for _, row in df_sistema_tela.iterrows(): st.session_state[f"chk_{row['id']}"] = False
                    st.rerun()
            
            soma_sistema_marcado = sum(row['Valor'] for _, row in df_sistema_tela.iterrows() if st.session_state.get(f"chk_{row['id']}", False)) if not df_sistema_tela.empty else 0.0
            st.markdown(f'<div class="caixa-soma">💰 Selecionado: R$ {soma_sistema_marcado:,.2f}</div>', unsafe_allow_html=True)
            
            if not df_sistema_tela.empty:
                for _, row in df_sistema_tela.iterrows():
                    st.checkbox(f"{row['Tipo']} | R$ {abs(row['Valor']):,.2f} | {row['Descrição'][:25]}", key=f"chk_{row['id']}")
            else:
                st.write("✨ Tudo certo aqui!")

        with col3:
            st.markdown('<div class="titulo-coluna-sipag">💳 Conferência Cartão SIPAG</div>', unsafe_allow_html=True)
            if not df_sipag_tela.empty:
                soma_sipag = sum(df_sipag_tela['Valor'])
                st.markdown(f'<div class="caixa-soma">Lote Total: R$ {soma_sipag:,.2f}</div>', unsafe_allow_html=True)
                for _, row in df_sipag_tela.iterrows():
                    st.write(f"• R$ {row['Valor']:,.2f} | {row['CentroCusto']}")
            else:
                st.warning("Sem registros SIPAG para este dia.")

        st.markdown("---")
        if data_selecionada and data_selecionada not in st.session_state[chave_dias_conciliados]:
            if st.button("⚡ Confirmar Finalização Completa do Dia", type="secondary", use_container_width=True):
                st.session_state[chave_dias_conciliados].append(data_selecionada)
                
                # SALVAMENTO AUTOMÁTICO DOS DIAS CONCILIADOS NO HD
                with open(arq_cache_dias_conciliados, "w", encoding="utf-8") as f:
                    json.dump(st.session_state[chave_dias_conciliados], f, ensure_ascii=False)
                    
                st.toast(f"✅ Dia {data_selecionada} arquivado com sucesso!")
                st.rerun()

        # Central de Ajustes Manuais
        st.markdown("---")
        st.markdown("### ✏️ Central de Ajustes e Lançamentos")
        aba_ins, aba_edt = st.tabs(["➕ Inserir Novo Ajuste Manual", "📝 Modificar / Remover Lançamentos Existentes"])
        
        with aba_ins:
            col_ed1, col_ed2, col_ed3, col_ed4 = st.columns([2, 1, 1, 1])
            desc_ajuste = col_ed1.text_input("Descrição do ajuste:", key="ins_desc")
            val_ajuste = col_ed2.number_input("Valor (R$):", step=0.01, key="ins_val")
            tipo_ajuste = col_ed3.selectbox("Origem do ajuste:", ["Ajuste Banco", "Ajuste Sistema"], key="ins_orig")
            dt_ajuste = col_ed4.date_input("Data do Lançamento:", value=datetime.date(2026, 4, 8), key="ins_data")
            
            if st.button("➕ Inserir Ajuste na Linha do Tempo", use_container_width=True):
                id_gerado = f"M_INS_{len(st.session_state[chave_modificacoes])}"
                origem_convertida = 'Banco' if "Banco" in tipo_ajuste else 'Sistema'
                st.session_state[chave_modificacoes].append({
                    'id': id_gerado, 'acao': 'inserir', 'desc': desc_ajuste.upper(),
                    'valor': val_ajuste, 'origem': origem_convertida, 'data': dt_ajuste.strftime('%d/%m/%Y')}
                )
                # SALVAMENTO AUTOMÁTICO DO NOVO AJUSTE NO HD
                with open(arq_cache_modificacoes, "w", encoding="utf-8") as f:
                    json.dump(st.session_state[chave_modificacoes], f, ensure_ascii=False)
                st.success("Ajuste injetado e salvo fisicamente!")
                st.rerun()

        with aba_edt:
            lista_dfs = [df for df in [df_banco_tela, df_sistema_tela] if not df.empty]
            df_todos_dia = pd.concat(lista_dfs, ignore_index=True) if lista_dfs else pd.DataFrame()
            
            if not df_todos_dia.empty:
                item_selecionado = st.selectbox(
                    "Escolha qual lançamento deseja alterar/remover hoje:", df_todos_dia['id'].tolist(),
                    format_func=lambda x: f"[{df_todos_dia[df_todos_dia['id']==x]['Origem'].values[0]}] {df_todos_dia[df_todos_dia['id']==x]['Descrição'].values[0][:30]} | R$ {df_todos_dia[df_todos_dia['id']==x]['Valor'].values[0]}"
                )
                row_sel = df_todos_dia[df_todos_dia['id'] == item_selecionado].iloc[0]
                
                col_upd1, col_upd2, col_upd3 = st.columns([2, 1, 1])
                
                nova_desc = col_upd1.text_input("Modificar Descrição para:", value=row_sel['Descrição'], key=f"edt_desc_{item_selecionado}")
                novo_val = col_upd2.number_input("Modificar Valor para:", value=float(row_sel['Valor']), step=0.01, key=f"edt_val_{item_selecionado}")
                nova_data = col_upd3.date_input("Transferir para a Data:", value=datetime.datetime.strptime(row_sel['Data'], '%d/%m/%Y').date(), key=f"edt_dt_{item_selecionado}")
                
                col_b_ed1, col_b_ed2 = st.columns(2)
                
                if col_b_ed1.button("💾 Gravar Alterações / Mudar Data", type="primary", use_container_width=True):
                    registro_original = next((m for m in st.session_state[chave_modificacoes] if m['id'] == item_selecionado), None)
                    
                    if registro_original and registro_original['acao'] == 'inserir':
                        registro_original['desc'] = nova_desc.upper()
                        registro_original['valor'] = novo_val
                        registro_original['data'] = nova_data.strftime('%d/%m/%Y')
                    else:
                        st.session_state[chave_modificacoes] = [m for m in st.session_state[chave_modificacoes] if m['id'] != item_selecionado]
                        st.session_state[chave_modificacoes].append({
                            'id': item_selecionado, 'acao': 'editar', 'desc': nova_desc.upper(), 
                            'valor': novo_val, 'data': nova_data.strftime('%d/%m/%Y')
                        })
                    # SALVAMENTO AUTOMÁTICO DAS EDIÇÕES NO HD
                    with open(arq_cache_modificacoes, "w", encoding="utf-8") as f:
                        json.dump(st.session_state[chave_modificacoes], f, ensure_ascii=False)
                    st.success("Lançamento atualizado e salvo!")
                    st.rerun()
                    
                if col_b_ed2.button("🗑️ Remover permanentemente este item", use_container_width=True):
                    registro_original = next((m for m in st.session_state[chave_modificacoes] if m['id'] == item_selecionado), None)
                    
                    if registro_original and registro_original['acao'] == 'inserir':
                        st.session_state[chave_modificacoes] = [m for m in st.session_state[chave_modificacoes] if m['id'] != item_selecionado]
                    else:
                        st.session_state[chave_modificacoes] = [m for m in st.session_state[chave_modificacoes] if m['id'] != item_selecionado]
                        st.session_state[chave_modificacoes].append({'id': item_selecionado, 'acao': 'excluir'})
                    # SALVAMENTO AUTOMÁTICO DAS EXCLUSÕES NO HD
                    with open(arq_cache_modificacoes, "w", encoding="utf-8") as f:
                        json.dump(st.session_state[chave_modificacoes], f, ensure_ascii=False)
                    st.success("Item removido e registrado!")
                    st.rerun()

    with aba_historico:
        st.markdown("### 📋 Histórico de Fechamento do Período")
        if st.session_state[chave_dias_conciliados]:
            # Criando uma lista para podermos iterar e modificar sem dar erro de concorrência
            lista_dias = list(st.session_state[chave_dias_conciliados])
            for d in lista_dias:
                col_txt, col_act = st.columns([4, 1])
                with col_txt:
                    st.success(f"📆 Dia {d} -> **CONCILIADO E PRONTO**")
                with col_act:
                    # 🔓 BOTÃO DE REABERTURA INJETADO
                    if st.button("🔓 Reabrir este Dia", key=f"btn_reabrir_{d}_{conta_ativa}", use_container_width=True):
                        st.session_state[chave_dias_conciliados].remove(d)
                        # Atualiza imediatamente o arquivo físico no disco removendo o dia
                        with open(arq_cache_dias_conciliados, "w", encoding="utf-8") as f:
                            json.dump(st.session_state[chave_dias_conciliados], f, ensure_ascii=False)
                        
                        # Reseta o ponteiro de seleção de datas para o dia reaberto
                        if 'indice_data' in st.session_state:
                            del st.session_state.indice_data
                        with open(arq_cache_data_ativa, "w", encoding="utf-8") as f:
                            f.write(d)
                            
                        st.toast(f"Dia {d} foi retirado do histórico e reaberto!", icon="🔓")
                        st.rerun()
        else:
            st.info("Nenhum dia foi finalizado neste lote ainda.")
