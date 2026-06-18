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
    # Inicializa o controlador de cookies de forma persistente no estado da sessão
    if "cookies_controller" not in st.session_state:
        st.session_state.cookies_controller = CookieController()
    controller = st.session_state.cookies_controller
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

# Tenta recuperar o login salvo se a sessão sumir no F5
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

# --- SELETOR DA CONTA ATIVA ---
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
    if "PIX RECEBIDO" in hist_u or "RECEBIDO DE OUTRA IF" in hist_u: tipo = "🟢 PIX RECEBIDO"
    elif "PIX ENVIADO" in hist_u or "PIX TRANSFERIDO" in hist_u: tipo = "🔴 PIX ENVIADO"
    elif "PAGTO TITULO" in hist_u or "PAGAMENTO" in hist_u: tipo = "🔴 PAGTO TITULO"
    elif "TARIFA" in hist_u or "TAR EXTRATO" in hist_u: tipo = "🔴 TAR TARIFA"
    elif "JUROS" in hist_u or "REND" in hist_u or "SELIC" in hist_u or "CRED.REND" in hist_u: tipo = "📈 RENDIMENTO POUPANÇA"
    elif "ESTORNO" in hist_u: tipo = "🟢 ESTORNO"
    elif "TRANSF" in hist_u and "RECEB" in hist_u: tipo = "🟢 TRANSF RECEBIDA"
    elif "TRANSF" in hist_u: tipo = "🔴 TRANSF ENVIADA"

    limpeza_regex = [
        r"RECEBIDO DE OUTRA IF", r"PIX TRANSFERIDO", r"PIX RECEBIDO", r"PAGTO TITULO INTERNET",
        r"COMPLEMENTO:", r"VALOR DO COMPROMISSO", r"COBRANCA SICOOB", r"FAVORECIDO:", r"PAGADOR:",
        r"REMETENTE:", r"AGENCIA:", r"CONTA:", r"CPF:", r"CNPJ:", r"-\s*$"
    ]
    name_isolado = det_u
    for padrao in limpeza_regex:
        name_isolado = re.sub(padrao, "", name_isolado)
    name_isolado = re.sub(r'\s+', ' ', name_isolado).strip().lstrip('-').strip()
    if not name_isolado or len(name_isolado) < 3:
        name_isolado = hist_u
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

def extrair_dados_pdf_poupanca(arquivo_bytes):
    if pypdf is None: return []
    leitor = pypdf.PdfReader(arquivo_bytes)
    linhas_finais = []
    regex_data = re.compile(r'(\d{2}/\d{2}/\d{4})')
    
    for pagina in leitor.pages:
        texto = pagina.extract_text()
        if not texto: continue
        for linha in texto.split('\n'):
            linha_u = linha.upper().strip()
            match_data = regex_data.search(linha_u)
            if match_data and "SALDO" not in linha_u:
                dt_enc = match_data.group(1)
                tipo = "📈 RENDIMENTO POUPANÇA" if any(x in linha_u for x in ["JUROS", "REND", "SELIC", "CRED.REND"]) else "🔹 OFERTA / PIX"
                partes = linha_u.split()
                if len(partes) >= 3:
                    v_num = converter_valor_extrato(partes[-1])
                    if v_num == 0.0 and len(partes) > 1:
                        v_num = converter_valor_extrato(partes[-2])
                    if v_num != 0.0:
                        desc = linha_u.replace(dt_enc, "").replace(partes[-1], "").strip()
                        linhas_finais.append({'Data': dt_enc, 'Tipo': tipo, 'Descrição': desc, 'Valor': v_num})
    return linhas_finais

def carregar_dados_da_sessao(modo_conta, bytes_banco, bytes_sistema):
    if not bytes_banco: return None, None, {}
    dados_b, s_ant, s_finais = processar_extrato_sicoob(io.BytesIO(bytes_banco))
    dados_banco_finais = []
    sipag_por_dia = {}
    idx_b = 0
    
    for item in dados_b:
        hist_c = (item['Histórico'] + " " + item['Detalhes']).upper()
        tipo_limpo, detalhe_limpo = extrair_detalhe_limpo(item['Histórico'], item['Detalhes'])
        if "SIPAG" in hist_c or "COMPRAS" in item['Histórico'].upper() or "MAESTRO" in hist_c:
            sipag_por_dia[item['Data']] = sipag_por_dia.get(item['Data'], 0.0) + item['Valor']
        else:
            item['id_banco'] = f"B_{idx_b}"
            item['Tipo'] = tipo_limpo
            item['Detalhe_Limpo'] = detalhe_limpo
            dados_banco_finais.append(item)
            idx_b += 1
            
    for dia, v_tot in sipag_por_dia.items():
        dados_banco_finais.append({
            'id_banco': f"B_{idx_b}", 'Data': dia, 'Documento': 'SIPAG_LOTE',
            'Tipo': '💳 SIPAG LOTE', 'Detalhe_Limpo': "VENDAS CARTÕES (Agrupado)",
            'Valor': round(v_tot, 2), 'Histórico': 'SIPAG', 'Detalhes': ''
        })
        idx_b += 1

    dados_contrapartida = []
    idx_t = 0
    if bytes_sistema:
        if "161" in modo_conta:
            df_t_bruto = pd.read_excel(io.BytesIO(bytes_sistema), skiprows=7).dropna(how='all')
            for _, row in df_t_bruto.iterrows():
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
                                'Tipo': "🟢 PIX RECEBIDO" if v_liq > 0 else "🔴 SAÍDA", 'Descrição': desc, 'Valor': round(v_liq, 2)
                            })
                            idx_t += 1
        elif "140" in modo_conta:
            try:
                conteudo = bytes_sistema.decode('utf-8', errors='ignore')
                df_e = pd.read_csv(io.StringIO(conteudo), skiprows=9, on_bad_lines='skip')
                df_e = df_e[df_e['Dt.Oferta'].str.contains('/', na=False)]
                for _, row in df_e.iterrows():
                    v_ecl = float(str(row['Valor (R$)']).strip().replace(',', '.'))
                    dt_obj = pd.to_datetime(row['Dt.Oferta'].strip(), dayfirst=True, errors='coerce')
                    if pd.notna(dt_obj) and v_ecl > 0:
                        dados_contrapartida.append({
                            'id_theos': f"T_{idx_t}", 'Data': dt_obj.strftime('%d/%m/%Y'),
                            'Tipo': "🟢 PIX RECEBIDO", 'Descrição': str(row['Nome']).strip(), 'Valor': round(v_ecl, 2)
                        })
                        idx_t += 1
            except: pass

    mapa_saldos = {dia: {'Anterior': s_ant if i==0 else list(s_finais.values())[i-1], 'Final': v} for i, (dia, v) in enumerate(s_finais.items())}
    return pd.DataFrame(dados_banco_finais), pd.DataFrame(dados_contrapartida), mapa_saldos

# =========================================================================
# 💾 INTERCEPTADOR E PERSISTIDOR DE UPLOADS (CATCH DE F5)
# =========================================================================
st.markdown("### 📥 Carregar Arquivos do Período")
col_up1, col_up2 = st.columns(2)

# Chaves de armazenamento na sessão
chave_store_banco = f"store_bytes_banco_{conta_ativa}"
chave_store_sistema = f"store_bytes_sistema_{conta_ativa}"
chave_name_banco = f"store_name_banco_{conta_ativa}"
chave_name_sistema = f"store_name_sistema_{conta_ativa}"

if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_name_banco not in st.session_state: st.session_state[chave_name_banco] = ""
if chave_name_sistema not in st.session_state: st.session_state[chave_name_sistema] = ""

with col_up1:
    if "Poupança" in conta_ativa:
        u_extrato = st.file_uploader("📂 Arraste o Extrato PDF da Poupança:", type=["pdf"], key=f"f_banco_{conta_ativa}")
    else:
        u_extrato = st.file_uploader("📂 Arraste o Extrato Excel do Sicoob:", type=["xlsx", "xls"], key=f"f_banco_{conta_ativa}")
    
    if u_extrato:
        st.session_state[chave_store_banco] = u_extrato.getvalue()
        st.session_state[chave_name_banco] = u_extrato.name
    
    if st.session_state[chave_store_banco]:
        st.caption(f"📦 **Arquivo ativo em memória:** {st.session_state[chave_name_banco]}")

with col_up2:
    if "161" in conta_ativa:
        u_sistema = st.file_uploader("📂 Arraste o Relatório do Boletim (Theos):", type=["xlsx", "xls"], key=f"f_sist_{conta_ativa}")
    elif "140" in conta_ativa:
        u_sistema = st.file_uploader("📂 Arraste a Conferência do Dízimo (Eclesial):", type=["csv"], key=f"f_sist_{conta_ativa}")
    else:
        u_sistema = None

    if u_sistema:
        st.session_state[chave_store_sistema] = u_sistema.getvalue()
        st.session_state[chave_name_sistema] = u_sistema.name
        
    if "Poupança" not in conta_ativa and st.session_state[chave_store_sistema]:
        st.caption(f"📦 **Arquivo ativo em memória:** {st.session_state[chave_name_sistema]}")
    elif "Poupança" in conta_ativa:
        st.info("💡 Contas Poupança necessitam apenas do extrato bancário em formato PDF.")

# Botão para limpar arquivos e resetar a memória se necessário
if st.session_state[chave_store_banco] or st.session_state[chave_store_sistema]:
    if st.button("🗑️ Limpar Arquivos da Memória", use_container_width=True):
        st.session_state[chave_store_banco] = None
        st.session_state[chave_store_sistema] = None
        st.session_state[chave_name_banco] = ""
        st.session_state[chave_name_sistema] = ""
        st.rerun()

# =========================================================================
# FLUXO POUPANÇA (PDF)
# =========================================================================
if "Poupança" in conta_ativa and st.session_state[chave_store_banco]:
    with st.spinner("Processando PDF da poupança..."):
        dados_pdf = extrair_dados_pdf_poupanca(io.BytesIO(st.session_state[chave_store_banco]))
        
    if dados_pdf:
        df_p = pd.DataFrame(dados_pdf)
        st.success("✅ Dados carregados com sucesso do histórico em cache!")
        st.markdown("---")
        st.subheader("📊 Relatório de Repasse Curial (Filtro de Rendimentos)")
        
        todas_datas_p = sorted(df_p['Data'].unique(), key=lambda x: pd.to_datetime(x, dayfirst=True))
        data_p = st.selectbox("📆 Escolha o Dia do Repasse:", todas_datas_p)
        
        df_dia = df_p[df_p['Data'] == data_p]
        df_ofertas = df_dia[df_dia['Tipo'] == "🔹 OFERTA / PIX"]
        df_rendimentos = df_dia[df_dia['Tipo'] == "📈 RENDIMENTO POUPANÇA"]
        
        tot_ofertas = df_ofertas[df_ofertas['Valor'] > 0]['Valor'].sum()
        tot_rendimentos = df_rendimentos['Valor'].sum()
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1: st.metric("📥 Total Entradas (Ofertas/PIX)", f"R$ {tot_ofertas:,.2f}")
        with col_c2: st.metric("📈 Rendimentos (Retidos)", f"R$ {tot_rendimentos:,.2f}")
        with col_c3: st.metric("⭐ VALOR LÍQUIDO PARA A CÚRIA", f"R$ {tot_ofertas:,.2f}")
        
        t_aba1, t_aba2 = st.tabs(["💰 Entradas de Ofertas", "📈 Juros/Selic Identificados"])
        with t_aba1: st.dataframe(df_ofertas[['Descrição', 'Valor']], use_container_width=True, hide_index=True)
        with t_aba2: st.dataframe(df_rendimentos[['Descrição', 'Valor']], use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhuma transação válida identificada no PDF da poupança.")

# =========================================================================
# FLUXO CONTAS CORRENTES (161 E 140)
# =========================================================================
elif st.session_state[chave_store_banco] and ("Poupança" in conta_ativa or st.session_state[chave_store_sistema]):
    chave_banco = f"cortes_banco_{conta_ativa}"
    chave_sistema = f"cortes_sistema_{conta_ativa}"
    chave_hist_banco = f"hist_banco_dia_{conta_ativa}"
    chave_hist_sistema = f"hist_sistema_dia_{conta_ativa}"
    
    if chave_banco not in st.session_state: st.session_state[chave_banco] = []
    if chave_sistema not in st.session_state: st.session_state[chave_sistema] = []
    if chave_hist_banco not in st.session_state: st.session_state[chave_hist_banco] = {}
    if chave_hist_sistema not in st.session_state: st.session_state[chave_hist_sistema] = {}
    if 'historico_passos' not in st.session_state: st.session_state.historico_passos = []
    if 'indice_data' not in st.session_state: st.session_state.indice_data = 0

    df_banco_orig, df_sistema_orig, mapa_saldos = carregar_dados_da_sessao(
        conta_ativa, st.session_state[chave_store_banco], st.session_state[chave_store_sistema]
    )
    
    if df_banco_orig is not None and not df_banco_orig.empty:
        df_banco_pendente = df_banco_orig[~df_banco_orig['id_banco'].isin(st.session_state[chave_banco])]
        if df_sistema_orig is not None and not df_sistema_orig.empty:
            df_sistema_pendente = df_sistema_orig[~df_sistema_orig['id_theos'].isin(st.session_state[chave_sistema])]
        else:
            df_sistema_pendente = pd.DataFrame(columns=['id_theos', 'Data', 'Tipo', 'Descrição', 'Valor'])

        todas_datas = sorted(list(set(df_banco_orig['Data'].unique()).union(set(df_sistema_orig['Data'].unique() if df_sistema_orig is not None else []))), key=lambda x: pd.to_datetime(x, dayfirst=True))

        with st.sidebar:
            st.markdown(f"### 🎛️ Painel - {conta_ativa.split('-')[0]}")
            st.caption("Navegação operacional")
            st.markdown("---")
            data_selecionada = st.selectbox("📆 Selecione o Dia:", todas_datas, index=min(st.session_state.indice_data, len(todas_datas)-1))
            st.session_state.indice_data = todas_datas.index(data_selecionada)
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("◀ Anterior", use_container_width=True) and st.session_state.indice_data > 0:
                    st.session_state.indice_data -= 1
                    st.rerun()
            with col_b2:
                if st.button("Próximo ▶", use_container_width=True) and st.session_state.indice_data < len(todas_datas) - 1:
                    st.session_state.indice_data += 1
                    st.rerun()
            st.markdown("---")
            if st.button("↩️ Desfazer Última Baixa", use_container_width=True) and st.session_state.historico_passos:
                ultimo_passo = st.session_state.historico_passos.pop()
                dt_passo = ultimo_passo['data']
                for b_id in ultimo_passo['banco_ids']:
                    st.session_state[chave_banco].remove(b_id)
                    st.session_state[chave_hist_banco][dt_passo] = [x for x in st.session_state[chave_hist_banco][dt_passo] if x['id_banco'] != b_id]
                for t_id in ultimo_passo['theos_ids']:
                    st.session_state[chave_sistema].remove(t_id)
                    st.session_state[chave_hist_sistema][dt_passo] = [x for x in st.session_state[chave_hist_sistema][dt_passo] if x['id_theos'] != t_id]
                st.rerun()

        info_saldo = mapa_saldos.get(data_selecionada, {'Anterior': 0.0, 'Final': 0.0})
        df_banco_dia = df_banco_orig[df_banco_orig['Data'] == data_selecionada]
        fluxo_dia = df_banco_dia['Valor'].sum()
        
        st.markdown("---")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1: st.metric(label="💰 Saldo Anterior Real", value=f"R$ {info_saldo['Anterior']:,.2f}")
        with col_s2: st.metric(label="🔄 Movimentação Líquida", value=f"R$ {fluxo_dia:,.2f}", delta=f"{fluxo_dia:,.2f}")
        with col_s3: st.metric(label="🏦 Saldo Final Sicoob", value=f"R$ {info_saldo['Final']:,.2f}")

        aba_conciliacao, aba_historico = st.tabs(["🔄 Esteira de Conciliação Diária", "📋 Histórico de Fechamento"])

        with aba_conciliacao:
            st.markdown("#### ⚡ Ações Rápidas do Dia")
            if st.button("🚀 Conciliar Dia Inteiro Automaticamente (Dar Baixa Geral Sem Seleção)", type="primary", use_container_width=True):
                df_banco_dia_pendente = df_banco_dia[~df_banco_dia['id_banco'].isin(st.session_state[chave_banco])]
                df_sistema_dia_pendente = df_sistema_pendente[df_sistema_pendente['Data'] == data_selecionada]
                
                if not df_banco_dia_pendente.empty or not df_sistema_dia_pendente.empty:
                    passo_automatico = {'data': data_selecionada, 'banco_ids': [], 'theos_ids': []}
                    if data_selecionada not in st.session_state[chave_hist_banco]: st.session_state[chave_hist_banco][data_selecionada] = []
                    if data_selecionada not in st.session_state[chave_hist_sistema]: st.session_state[chave_hist_sistema][data_selecionada] = []
                    
                    chave_edicoes_banco = f"edicoes_banco_{conta_ativa}"
                    chave_edicoes_sistema = f"edicoes_sistema_{conta_ativa}"
                    
                    for _, b in df_banco_dia_pendente.iterrows():
                        b_id = b['id_banco']
                        desc_banco = st.session_state.get(chave_edicoes_banco, {}).get(b_id, {}).get('Descrição', b.get('Detalhe_Limpo', b['Histórico']))
                        val_banco = st.session_state.get(chave_edicoes_banco, {}).get(b_id, {}).get('Valor', b['Valor'])
                        st.session_state[chave_banco].append(b_id)
                        passo_automatico['banco_ids'].append(b_id)
                        st.session_state[chave_hist_banco][data_selecionada].append({'id_banco': b_id, 'Descrição': desc_banco, 'Valor': val_banco})
                        
                    for _, t in df_sistema_dia_pendente.iterrows():
                        t_id = t['id_theos']
                        desc_sistema = st.session_state.get(chave_edicoes_sistema, {}).get(t_id, {}).get('Descrição', t['Descrição'])
                        val_sistema = st.session_state.get(chave_edicoes_sistema, {}).get(t_id, {}).get('Valor', t['Valor'])
                        st.session_state[chave_sistema].append(t_id)
                        passo_automatico['theos_ids'].append(t_id)
                        st.session_state[chave_hist_sistema][data_selecionada].append({'id_theos': t_id, 'Descrição': desc_sistema, 'Valor': val_sistema})
                        
                    st.session_state.historico_passos.append(passo_automatico)
                    st.toast(f"Fechamento completo efetuado para o dia {data_selecionada}!", icon="⚡")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### 🔍 Filtro Tático Operacional")
            tipos_disponiveis = sorted(list(set(df_banco_dia['Tipo'].unique()).union(set(df_sistema_pendente[df_sistema_pendente['Data'] == data_selecionada]['Tipo'].unique()))))
            tipo_filtro = st.selectbox("🎯 Filtrar tela por Tipo de Transação:", ["Todos"] + tipos_disponiveis)

            df_banco_tela = df_banco_dia[~df_banco_dia['id_banco'].isin(st.session_state[chave_banco])]
            df_sistema_tela = df_sistema_pendente[df_sistema_pendente['Data'] == data_selecionada]

            if tipo_filtro != "Todos":
                df_banco_tela = df_banco_tela[df_banco_tela['Tipo'] == tipo_filtro]
                df_sistema_tela = df_sistema_tela[df_sistema_tela['Tipo'] == tipo_filtro]

            valores_banco_abs = df_banco_tela['Valor'].abs().tolist()
            valores_sistema_abs = df_sistema_tela['Valor'].abs().tolist() if not df_sistema_tela.empty else []

            if f"marcar_todos_b_{data_selecionada}_{tipo_filtro}" not in st.session_state: st.session_state[f"marcar_todos_b_{data_selecionada}_{tipo_filtro}"] = False
            if f"marcar_todos_s_{data_selecionada}_{tipo_filtro}" not in st.session_state: st.session_state[f"marcar_todos_s_{data_selecionada}_{tipo_filtro}"] = False

            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="titulo-coluna"><span style="font-size:24px;">🏦</span><div class="texto-header-col">Extrato Sicoob</div></div>', unsafe_allow_html=True)
                container_calculo_banco = st.empty()
                if not df_banco_tela.empty and st.button("⭐ Selecionar Match Automático (Banco)", key=f"btn_b_{data_selecionada}_{tipo_filtro}"):
                    st.session_state[f"marcar_todos_b_{data_selecionada}_{tipo_filtro}"] = True
                    st.rerun()

                selecionados_banco = []
                soma_banco_atual = 0.0
                chave_edicoes_banco = f"edicoes_banco_{conta_ativa}"
                if chave_edicoes_banco not in st.session_state: st.session_state[chave_edicoes_banco] = {}

                for _, row in df_banco_tela.iterrows():
                    b_id = row['id_banco']
                    desc_banco = st.session_state[chave_edicoes_banco].get(b_id, {}).get('Descrição', row.get('Detalhe_Limpo', row['Histórico']))
                    val_banco = st.session_state[chave_edicoes_banco].get(b_id, {}).get('Valor', row['Valor'])
                    v_abs = abs(val_banco)
                    valor_padrao_chk = (v_abs in valores_sistema_abs) or st.session_state[f"marcar_todos_b_{data_selecionada}_{tipo_filtro}"]
                    
                    col_chk, col_edit = st.columns([0.88, 0.12])
                    with col_chk:
                        if st.checkbox(f"{row.get('Tipo', '🔹 OUTROS')} | R$ {v_abs:,.2f} | {desc_banco[:35]}", key=f"b_{b_id}", value=valor_padrao_chk):
                            row_mod = row.copy()
                            row_mod['Detalhe_Limpo'] = desc_banco
                            row_mod['Valor'] = val_banco
                            selecionados_banco.append(row_mod)
                            soma_banco_atual += val_banco
                    with col_edit:
                        with st.popover("⚙️"):
                            novo_desc = st.text_input("Descrição:", value=desc_banco, key=f"desc_inp_b_{b_id}")
                            novo_val = st.number_input("Valor:", value=float(val_banco), key=f"val_inp_b_{b_id}")
                            if st.button("Salvar", key=f"btn_salvar_b_{b_id}"):
                                st.session_state[chave_edicoes_banco][b_id] = {'Descrição': novo_desc, 'Valor': novo_val}
                                st.rerun()
                container_calculo_banco.markdown(f'<div class="caixa-calculo">📊 Selecionados: {len(selecionados_banco)} itens | Soma: R$ {soma_banco_atual:,.2f}</div>', unsafe_allow_html=True)

            with col2:
                lbl_sist = "💻 Paróquia / Eclesial (Dízimos)" if "140" in conta_ativa else "💻 Paróquia / Boletim Theos"
                st.markdown('<div class="titulo-coluna-igreja"><span style="font-size:24px;">⛪</span><div class="texto-header-col">' + lbl_sist + '</div></div>', unsafe_allow_html=True)
                container_calculo_sistema = st.empty()
                if not df_sistema_tela.empty and st.button("⭐ Selecionar Match Automático (Sistema)", key=f"btn_s_{data_selecionada}_{tipo_filtro}"):
                    st.session_state[f"marcar_todos_s_{data_selecionada}_{tipo_filtro}"] = True
                    st.rerun()

                selecionados_sistema = []
                soma_
