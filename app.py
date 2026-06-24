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

chave_modificacoes = f"modificacoes_ajustes_{conta_ativa}"
chave_dias_conciliados = f"dias_conciliados_{conta_ativa}"
chave_historico_ocultacoes = f"historico_ocultacoes_{conta_ativa}"
chave_data_atual_salva = f"data_salva_progresso_{conta_ativa}"

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_store_sipag not in st.session_state: st.session_state[chave_store_sipag] = None
if chave_store_campanha not in st.session_state: st.session_state[chave_store_campanha] = None
if chave_store_dizimo not in st.session_state: st.session_state[chave_store_dizimo] = None
if chave_modificacoes not in st.session_state: st.session_state[chave_modificacoes] = []
if chave_dias_conciliados not in st.session_state: st.session_state[chave_dias_conciliados] = []
if chave_historico_ocultacoes not in st.session_state: st.session_state[chave_historico_ocultacoes] = []

arq_cache_banco = os.path.join(CACHE_DIR, f"banco_{conta_ativa}.cache")
arq_cache_sistema = os.path.join(CACHE_DIR, f"sistema_{conta_ativa}.cache")
arq_cache_sipag = os.path.join(CACHE_DIR, f"sipag_{conta_ativa}.cache")
arq_cache_campanha = os.path.join(CACHE_DIR, f"campanha_{conta_ativa}.cache")
arq_cache_dizimo = os.path.join(CACHE_DIR, f"dizimo_{conta_ativa}.cache")

arq_cache_nome_banco = os.path.join(CACHE_DIR, f"nome_banco_{conta_ativa}.txt")
arq_cache_nome_sistema = os.path.join(CACHE_DIR, f"nome_sistema_{conta_ativa}.txt")
arq_cache_nome_sipag = os.path.join(CACHE_DIR, f"nome_sipag_{conta_ativa}.txt")
arq_cache_nome_campanha = os.path.join(CACHE_DIR, f"nome_campanha_{conta_ativa}.txt")
arq_cache_nome_dizimo = os.path.join(CACHE_DIR, f"nome_dizimo_{conta_ativa}.txt")

arq_cache_modificacoes = os.path.join(CACHE_DIR, f"ajustes_{conta_ativa}.json")
arq_cache_dias_conciliados = os.path.join(CACHE_DIR, f"dias_ok_{conta_ativa}.json")
arq_cache_historico_ocultacoes = os.path.join(CACHE_DIR, f"ocultados_{conta_ativa}.json")
arq_cache_data_ativa = os.path.join(CACHE_DIR, f"data_ativa_{conta_ativa}.txt")

# Recuperação de Cache do LocalStorage/Pasta
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

if st.session_state[chave_store_campanha] is None and os.path.exists(arq_cache_campanha):
    with open(arq_cache_campanha, "rb") as f: st.session_state[chave_store_campanha] = f.read()
    if os.path.exists(arq_cache_nome_campanha):
        with open(arq_cache_nome_campanha, "r", encoding="utf-8") as f: st.session_state[chave_nome_campanha] = f.read()

if st.session_state[chave_store_dizimo] is None and os.path.exists(arq_cache_dizimo):
    with open(arq_cache_dizimo, "rb") as f: st.session_state[chave_store_dizimo] = f.read()
    if os.path.exists(arq_cache_nome_dizimo):
        with open(arq_cache_nome_dizimo, "r", encoding="utf-8") as f: st.session_state[chave_nome_dizimo] = f.read()

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
# 📥 CARREGAMENTO DE ARQUIVOS INTERFACE DINÂMICA
# =========================================================================
st.markdown("### 📥 Carregar Arquivos do Período")

if eh_poupanca:
    u_extrato = st.file_uploader("📂 Carregar Extrato de Poupança Sicoob (PDF):", type=["pdf"], key=f"widget_up_poup_{conta_ativa}")
    if u_extrato is not None:
        conteudo = u_extrato.getvalue()
        st.session_state[chave_store_banco] = conteudo
        st.session_state[chave_nome_banco] = u_extrato.name
        with open(arq_cache_banco, "wb") as f: f.write(conteudo)
        with open(arq_cache_nome_banco, "w", encoding="utf-8") as f: f.write(u_extrato.name)
        st.rerun()
    elif st.session_state[chave_store_banco] is not None:
        st.caption(f"✅ Extrato Ativo: `{st.session_state.get(chave_nome_banco, 'Extrato_Poupanca.pdf')}`")
else:
    mostrar_dizimo = "Conta 161" in conta_ativa or "Conta 140" in conta_ativa
    num_colunas_layout = 5 if mostrar_dizimo else 4
    colunas_upload = st.columns(num_colunas_layout)

    with colunas_upload[0]:
        u_extrato = st.file_uploader("📂 Arraste o Extrato do Sicoob:", type=["xlsx", "xls", "pdf"], key=f"widget_up_banco_{conta_ativa}")
        if u_extrato is not None:
            conteudo = u_extrato.getvalue()
            st.session_state[chave_store_banco] = conteudo
            st.session_state[chave_nome_banco] = u_extrato.name
            with open(arq_cache_banco, "wb") as f: f.write(conteudo)
            with open(arq_cache_nome_banco, "w", encoding="utf-8") as f: f.write(u_extrato.name)
        elif st.session_state[chave_store_banco] is not None:
            st.caption(f"✅ Extrato: `{st.session_state.get(chave_nome_banco, 'Arquivo Sicoob')}`")

    with colunas_upload[1]:
        u_sistema = st.file_uploader("📂 Relatório Boletim / Sistema:", type=["xlsx", "xls", "csv", "pdf"], key=f"widget_up_sist_{conta_ativa}")
        if u_sistema is not None:
            conteudo = u_sistema.getvalue()
            st.session_state[chave_store_sistema] = conteudo
            st.session_state[chave_nome_sistema] = u_sistema.name
            with open(arq_cache_sistema, "wb") as f: f.write(conteudo)
            with open(arq_cache_nome_sistema, "w", encoding="utf-8") as f: f.write(u_sistema.name)
        elif st.session_state[chave_store_sistema] is not None:
            st.caption(f"✅ Boletim: `{st.session_state.get(chave_nome_sistema, 'Arquivo Sistema')}`")

    with colunas_upload[2]:
        u_sipag = st.file_uploader("📂 Planilha Cartão SIPAG (CSV/XLSX):", type=["csv", "xlsx"], key=f"widget_up_sipag_{conta_ativa}")
        if u_sipag is not None:
            conteudo = u_sipag.getvalue()
            st.session_state[chave_store_sipag] = conteudo
            st.session_state[chave_nome_sipag] = u_sipag.name
            with open(arq_cache_sipag, "wb") as f: f.write(conteudo)
            with open(arq_cache_nome_sipag, "w", encoding="utf-8") as f: f.write(u_sipag.name)
        elif st.session_state[chave_store_sipag] is not None:
            st.caption(f"✅ SIPAG: `{st.session_state.get(chave_nome_sipag, 'Arquivo SIPAG')}`")

    with colunas_upload[3]:
        u_campanha = st.file_uploader("📂 Planilha Cartão Campanha (CSV/XLSX):", type=["csv", "xlsx"], key=f"widget_up_campanha_{conta_ativa}")
        if u_campanha is not None:
            conteudo = u_campanha.getvalue()
            st.session_state[chave_store_campanha] = conteudo
            st.session_state[chave_nome_campanha] = u_campanha.name
            with open(arq_cache_campanha, "wb") as f: f.write(conteudo)
            with open(arq_cache_nome_campanha, "w", encoding="utf-8") as f: f.write(u_campanha.name)
        elif st.session_state[chave_store_campanha] is not None:
            st.caption(f"✅ Campanha: `{st.session_state.get(chave_nome_campanha, 'Arquivo Campanha')}`")

    if mostrar_dizimo:
        with colunas_upload[4]:
            # 📄 AJUSTE CRUCIAL: Adicionado "xls" na lista de formatos aceitos para evitar o erro de recusa vermelho
            u_dizimo = st.file_uploader("📂 Conferência do Dízimo (CSV/XLSX/XLS):", type=["csv", "xlsx", "xls"], key=f"widget_up_dizimo_{conta_ativa}")
            if u_dizimo is not None:
                conteudo = u_dizimo.getvalue()
                st.session_state[chave_store_dizimo] = conteudo
                st.session_state[chave_nome_dizimo] = u_dizimo.name
                with open(arq_cache_dizimo, "wb") as f: f.write(conteudo)
                with open(arq_cache_nome_dizimo, "w", encoding="utf-8") as f: f.write(u_dizimo.name)
                st.rerun()
            elif st.session_state[chave_store_dizimo] is not None:
                st.caption(f"✅ Dízimo: `{st.session_state.get(chave_nome_dizimo, 'Arquivo Dízimo')}`")

if st.session_state[chave_store_banco] or st.session_state[chave_store_sistema] or st.session_state[chave_store_sipag] or st.session_state[chave_store_campanha] or st.session_state[chave_store_dizimo]:
    if st.button("🗑️ Trocar / Limpar Arquivos e Apagar Cache Completamente", use_container_width=True):
        st.session_state[chave_store_banco] = None
        st.session_state[chave_store_sistema] = None
        st.session_state[chave_store_sipag] = None
        st.session_state[chave_store_campanha] = None
        st.session_state[chave_store_dizimo] = None
        st.session_state[chave_nome_banco] = None
        st.session_state[chave_nome_sistema] = None
        st.session_state[chave_nome_sipag] = None
        st.session_state[chave_nome_campanha] = None
        st.session_state[chave_nome_dizimo] = None
        st.session_state[chave_modificacoes] = []
        st.session_state[chave_dias_conciliados] = []
        st.session_state[chave_historico_ocultacoes] = []
        if 'indice_data' in st.session_state: del st.session_state.indice_data
        
        arquivos_para_deletar = [
            arq_cache_banco, arq_cache_sistema, arq_cache_sipag, arq_cache_campanha, arq_cache_dizimo,
            arq_cache_nome_banco, arq_cache_nome_sistema, arq_cache_nome_sipag, arq_cache_nome_campanha, arq_cache_nome_dizimo,
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
            
    return dados_contrapartida, saldos_sistema_por_dia

# =========================================================================
# ⚙️ ENGINE DE TRATAMENTO ISOLADO (MAPEAMENTO DE COLUNAS ADAPTÁVEL)
# =========================================================================
def mapear_e_limpar_colunas(df):
    df.columns = [str(c).strip() for c in df.columns]
    dict_renomear = {}
    for col in df.columns:
        c_upper = col.upper()
        if any(x in c_upper for x in ["DATA", "DT.PGTO", "LIQUIDA", "DT_VENDA", "MOVIMENTO"]):
            dict_renomear[col] = "Data"
        elif any(x in c_upper for x in ["BRUTO", "VALOR_BRUTO", "VLR BRUTO"]):
            dict_renomear[col] = "Valor Bruto"
        elif any(x in c_upper for x in ["DESCONTO", "TAXA", "DESC"]):
            dict_renomear[col] = "Desconto"
        elif any(x in c_upper for x in ["LIQUIDO", "VALOR LIQ", "VLR LIQ", "VALOR_LIQ"]):
            dict_renomear[col] = "Valor Líquido"
        elif any(x in c_upper for x in ["CENTRO", "CUSTO", "CC", "DESTINO", "CONTA"]):
            dict_renomear[col] = "Centro de Custo"
            
    return df.rename(columns=dict_renomear)

def processar_planilha_isolada(arquivo_bytes, nome_arquivo):
    if arquivo_bytes is None: return pd.DataFrame()
    try:
        if str(nome_arquivo).lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(arquivo_bytes), sep=None, engine='python')
        else:
            # Mecanismo que aceita tanto arquivos novos .xlsx quanto os antigos .xls
            df = pd.read_excel(io.BytesIO(arquivo_bytes))
            
        df = mapear_e_limpar_colunas(df)
        
        colunas_obrigatorias = ["Data", "Valor Bruto", "Desconto", "Valor Líquido"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                if col == "Desconto": df["Desconto"] = 0.0
                elif col == "Valor Líquido" and "Valor Bruto" in df.columns: df["Valor Líquido"] = df["Valor Bruto"]
                else: df[col] = 0.0
                
        if "Centro de Custo" not in df.columns:
            df["Centro de Custo"] = "NÃO ESPECIFICADO"
            
        dados_processados = []
        for idx, row in df.iterrows():
            if pd.isna(row["Data"]): continue
            try:
                dt_str = str(row["Data"]).strip().split()[0]
                dt_f = pd.to_datetime(dt_str, dayfirst=True, errors='coerce').strftime('%d/%m/%Y')
                if not dt_f: continue
                
                v_bruto = abs(converter_valor_extrato(row["Valor Bruto"]))
                v_desc = abs(converter_valor_extrato(row["Desconto"]))
                v_liq = abs(converter_valor_extrato(row["Valor Líquido"]))
                
                if v_liq == 0 and v_bruto != 0: v_liq = v_bruto - v_desc
                
                dados_processados.append({
                    "Data": dt_f, "Valor Bruto": v_bruto, "Desconto": v_desc, "Valor Líquido": v_liq,
                    "Centro de Custo": str(row["Centro de Custo"]).strip().upper()
                })
            except: pass
        return pd.DataFrame(dados_processados)
    except:
        return pd.DataFrame()

# =========================================================================
# 📊 FLUXO DE EXECUÇÃO - PROCESSAMENTO PRINCIPAL DAS CONTAS CORRENTES
# =========================================================================
if not eh_poupanca and st.session_state[chave_store_banco] and st.session_state[chave_store_sistema]:
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

    # Processamento Isolado das Tabelas de Suporte (Sem travar a conciliação principal)
    df_sipag_isolado = processar_planilha_isolada(st.session_state[chave_store_sipag], st.session_state.get(chave_nome_sipag, ''))
    df_campanha_isolado = processar_planilha_isolada(st.session_state[chave_store_campanha], st.session_state.get(chave_nome_campanha, ''))
    df_dizimo_isolado = processar_planilha_isolada(st.session_state[chave_store_dizimo], st.session_state.get(chave_nome_dizimo, ''))

    for mod in st.session_state[chave_modificacoes]:
        if mod['acao'] == 'excluir':
            df_b_orig = df_b_orig[df_b_orig['id'] != mod['id']]
            if not df_s_orig.empty: df_s_orig = df_s_orig[df_s_orig['id'] != mod['id']]
        elif mod['acao'] == 'editar' or mod['acao'] == 'edit':
            df_b_orig.loc[df_b_orig['id'] == mod['id'], ['Descrição', 'Valor', 'Data']] = [mod['desc'], mod['valor'], mod['data']]
            if not df_s_orig.empty: df_s_orig.loc[df_s_orig['id'] == mod['id'], ['Descrição', 'Valor', 'Data']] = [mod['desc'], mod['valor'], mod['data']]
        elif mod['acao'] == 'inserir':
            nova_linha = pd.DataFrame([{'id': mod['id'], 'Data': mod['data'], 'Tipo': '🔹 AJUSTE', 'Descrição': mod['desc'], 'Valor': mod['valor'], 'Origem': mod['origem']}])
            if mod['origem'] == 'Banco': df_b_orig = pd.concat([df_b_orig, nova_linha], ignore_index=True)
            elif mod['origem'] == 'Sistema': df_s_orig = pd.concat([df_s_orig, nova_linha], ignore_index=True)

    todas_datas_totais = sorted(list(set(df_b_orig['Data'].unique()).union(set(df_s_orig['Data'].unique()))), key=lambda x: pd.to_datetime(x, dayfirst=True))
    datas_pendentes = [d for d in todas_datas_totais if d not in st.session_state[chave_dias_conciliados]]

    if not datas_pendentes:
        data_selecionada = todas_datas_totais[0] if todas_datas_totais else None
    else:
        if 'indice_data' not in st.session_state:
            data_inicial_recuperada = datas_pendentes[0]
            if os.path.exists(arq_cache_data_ativa):
                with open(arq_cache_data_ativa, "r", encoding="utf-8") as f:
                    saved_dt = f.read().strip()
                    if saved_dt in datas_pendentes: data_inicial_recuperada = saved_dt
            st.session_state.indice_data = datas_pendentes.index(data_inicial_recuperada)
            
        if st.session_state.indice_data >= len(datas_pendentes): st.session_state.indice_data = 0
        data_selecionada = datas_pendentes[st.session_state.indice_data]

    with st.sidebar:
        st.markdown("### 🎛️ Controle de Datas")
        if datas_pendentes:
            data_selecionada = st.selectbox("📆 Dias Pendentes de Baixa:", datas_pendentes, index=st.session_state.indice_data)
            st.session_state.indice_data = datas_pendentes.index(data_selecionada)
            with open(arq_cache_data_ativa, "w", encoding="utf-8") as f: f.write(data_selecionada)
        else:
            st.success("🎉 Nenhum dia pendente!")

    df_banco_dia = df_b_orig[df_b_orig['Data'] == data_selecionada].copy() if data_selecionada else pd.DataFrame()
    df_sistema_dia = df_s_orig[df_s_orig['Data'] == data_selecionada].copy() if (not df_s_orig.empty and data_selecionada) else pd.DataFrame()

    todos_ocultados = set()
    for lista_ids in st.session_state[chave_historico_ocultacoes]: todos_ocultados.update(lista_ids)

    if not df_banco_dia.empty: df_banco_dia = df_banco_dia[~df_banco_dia['id'].isin(todos_ocultados)]
    if not df_sistema_dia.empty: df_sistema_dia = df_sistema_dia[~df_sistema_dia['id'].isin(todos_ocultados)]

    saldo_banco_declarado = round(mapa_saldos_banco.get(data_selecionada, 0.0), 2) if data_selecionada else 0.0
    saldo_oficial_boletim = round(mapa_saldos_theos.get(data_selecionada, 0.0), 2) if data_selecionada else 0.0
    diferenca_visual = round(saldo_banco_declarado - saldo_oficial_boletim, 2)

    st.markdown("---")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("📅 Dia em Execução", data_selecionada if data_selecionada else "--/--/----")
    col_s2.metric("🏦 Saldo Extrato Sicoob", f"R$ {saldo_banco_declarado:,.2f}")
    col_s3.metric("⛪ Saldo Boletim Theos", f"R$ {saldo_oficial_boletim:,.2f}")
    
    if abs(diferenca_visual) < 0.05:
        col_s4.metric("🎯 Alinhamento de Saldos", "✅ 100% FECHADO", delta="Pronto")
    else:
        col_s4.metric("🎯 Alinhamento de Saldos", "⚠️ CONFERIR AJUSTES", delta=f"Dif: R$ {diferenca_visual:,.2f}", delta_color="inverse")

    aba_conciliacao, aba_cartoes = st.tabs(["🔄 Esteira de Conciliação Diária", "📊 Visualizador Isolado de Planilhas (Suporte)"])

    with aba_conciliacao:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='titulo-coluna'>📊 Extrato Sicoob ({data_selecionada})</div>", unsafe_allow_html=True)
            if df_banco_dia.empty: st.info("Nenhum registro para esta data.")
            else:
                for idx, r in df_banco_dia.iterrows():
                    st.checkbox(f"{r['Tipo']} | {r['Descrição']} | **R$ {r['Valor']:,.2f}**", key=f"chk_{r['id']}")
        with col2:
            st.markdown(f"<div class='titulo-coluna-igreja'>⛪ Sistema Eclesial ({data_selecionada})</div>", unsafe_allow_html=True)
            if df_sistema_dia.empty: st.info("Nenhum registro para esta data.")
            else:
                for idx, r in df_sistema_dia.iterrows():
                    st.checkbox(f"{r['Tipo']} | {r['Descrição']} | **R$ {r['Valor']:,.2f}**", key=f"chk_{r['id']}")

    # =========================================================================
    # 📊 CONSULTA DAS ABAS AUXILIARES POR DATA COMPLETAMENTE ISOLADO
    # =========================================================================
    with aba_cartoes:
        st.markdown(f"### 📋 Lançamentos Relativos das Planilhas - Data Base: `{data_selecionada}`")
        c_v1, c_v2, c_v3 = st.columns(3)
        
        with c_v1:
            st.markdown("<div class='titulo-coluna-sipag'>💳 Movimentação Cartão SIPAG</div>", unsafe_allow_html=True)
            if df_sipag_isolado.empty: st.info("Nenhum dado carregado.")
            else:
                df_sipag_dia = df_sipag_isolado[df_sipag_isolado["Data"] == data_selecionada]
                if df_sipag_dia.empty: st.warning(f"Sem lançamentos para {data_selecionada}.")
                else:
                    st.markdown(f"<div class='caixa-soma'>Soma Líquida do Dia: R$ {df_sipag_dia['Valor Líquido'].sum():,.2f}</div>", unsafe_allow_html=True)
                    st.dataframe(df_sipag_dia[["Valor Bruto", "Desconto", "Valor Líquido", "Centro de Custo"]], hide_index=True, use_container_width=True)
                    
        with c_v2:
            st.markdown("<div class='titulo-coluna-campanha'>🎁 Lançamentos Cartão Campanha</div>", unsafe_allow_html=True)
            if df_campanha_isolado.empty: st.info("Nenhum dado carregado.")
            else:
                df_campanha_dia = df_campanha_isolado[df_campanha_isolado["Data"] == data_selecionada]
                if df_campanha_dia.empty: st.warning(f"Sem lançamentos para {data_selecionada}.")
                else:
                    st.markdown(f"<div class='caixa-soma'>Soma Líquida do Dia: R$ {df_campanha_dia['Valor Líquido'].sum():,.2f}</div>", unsafe_allow_html=True)
                    st.dataframe(df_campanha_dia[["Valor Bruto", "Desconto", "Valor Líquido", "Centro de Custo"]], hide_index=True, use_container_width=True)

        with c_v3:
            st.markdown("<div class='titulo-coluna'>⛪ Conferência de Dízimo Auxiliar</div>", unsafe_allow_html=True)
            if df_dizimo_isolado.empty: st.info("Nenhum arquivo anexado no topo.")
            else:
                df_dizimo_dia = df_dizimo_isolado[df_dizimo_isolado["Data"] == data_selecionada]
                if df_dizimo_dia.empty: st.warning(f"Sem dados para {data_selecionada}.")
                else:
                    st.markdown(f"<div class='caixa-soma'>Total Dízimo Coletado: R$ {df_dizimo_dia['Valor Líquido'].sum():,.2f}</div>", unsafe_allow_html=True)
                    st.dataframe(df_dizimo_dia[["Valor Bruto", "Desconto", "Valor Líquido", "Centro de Custo"]], hide_index=True, use_container_width=True)

# =========================================================================
# ⚙️ PARSER EXCLUSIVO E ESTRUTURA PARA EXTRATO PDF DE POUPANÇA
# =========================================================================
def extrair_dados_pdf_poupanca(arquivo_bytes):
    try: import pypdf
    except ImportError: return []
    leitor = pypdf.PdfReader(io.BytesIO(arquivo_bytes))
    registros = []
    padrao_linha = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.,]+[CD])')
    for pagina in leitor.pages:
        texto = pagina.extract_text()
        if not texto: continue
        for linha in texto.replace('\n ', ' ').replace(' \n', ' ').split('\n'):
            linha = linha.strip()
            match = padrao_linha.search(linha)
            if match:
                data_f = match.group(1)
                descricao = match.group(2).strip().upper()
                valor_raw = match.group(3).strip().upper()
                tipo_sinal = 'C' if 'C' in valor_raw else 'D'
                num_limpo = re.sub(r'[^\d,.]', '', valor_raw).replace('.', '').replace(',', '.')
                try: registros.append({'Data': data_f, 'Descrição': descricao, 'Valor': float(num_limpo), 'Sinal': tipo_sinal})
                except: pass
    return registros

if eh_poupanca and st.session_state[chave_store_banco]:
    dados_poupanca = extrair_dados_pdf_poupanca(st.session_state[chave_store_banco])
    if dados_poupanca:
        df_poup = pd.DataFrame(dados_poupanca)
        lista_datas = sorted(list(df_poup['Data'].unique()), key=lambda x: pd.to_datetime(x, dayfirst=True))
        with st.sidebar: data_selecionada = st.selectbox("Selecione o dia para conferência:", lista_datas)
        df_dia = df_poup[df_poup['Data'] == data_selecionada]
        
        soma_pix = df_dia[(df_dia['Descrição'].isin(["PIX RECEBIDO-OUTRA IF", "CRÉDITO TRANSF. CC", "CRED TRF CC INTERCRE"])) & (df_dia['Sinal'] == 'C')]['Valor'].sum()
        soma_selic = df_dia[(df_dia['Descrição'].isin(["CORREÇÃO MONETÁRIA - SELIC", "JUROS - SELIC", "JUROS SELIC"])) & (df_dia['Sinal'] == 'C')]['Valor'].sum()
        df_retiradas = df_dia[df_dia['Sinal'] == 'D']
        
        st.markdown(f"---")
        st.markdown(f"### 📊 Relatório Poupança — Período: `{data_selecionada}`")
        c_k1, c_k2, c_k3 = st.columns(3)
        c_k1.metric("🟢 PIX & Transferências Recebidas (C)", f"R$ {soma_pix:,.2f}")
        c_k2.metric("📈 Correção & Juros SELIC", f"R$ {soma_selic:,.2f}")
        c_k3.metric("🔴 Retiradas Identificadas (D)", f"R$ {df_retiradas['Valor'].sum():,.2f}")
        
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.markdown("<div class='titulo-coluna'>📥 Extrato de Entradas Detalhado (C)</div>", unsafe_allow_html=True)
            st.dataframe(df_dia[df_dia['Sinal'] == 'C'][['Descrição', 'Valor']], use_container_width=True, hide_index=True)
        with col_t2:
            st.markdown("<div class='titulo-coluna-igreja'>📤 Alerta de Retiradas de Conta (D)</div>", unsafe_allow_html=True)
            if df_retiradas.empty: st.info("Tudo certo! Nenhuma movimentação de saída (D) nesta data.")
            else: st.dataframe(df_retiradas[['Descrição', 'Valor']], use_container_width=True, hide_index=True)

elif not st.session_state[chave_store_banco] and not eh_poupanca:
    st.info("Por favor, certifique-se de carregar os arquivos base acima para iniciar os trabalhos de conciliação.")
