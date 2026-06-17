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
# LÓGICA DE MATCH POR APROXIMAÇÃO E EXATO
# =========================================================================
def sao_valores_compativeis(valor_banco, valor_sistema, margem=0.06):
    """Verifica se o banco (líquido) é compatível com sistema (bruto) - até 6% de taxa."""
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
        st.markdown("<h2 style='text-align:center; color:#003366;'>⛪ Paróquia São Francisco</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#666;'>Acesso Restrito - Secretaria</p>", unsafe_allow_html=True)
        usuario_input = st.text_input("👤 Usuário:")
        senha_input = st.text_input("🔑 Senha:", type="password")
        lembrar = st.checkbox("Manter conectado", value=True)
        if st.button("🔓 Entrar", use_container_width=True, type="primary"):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                if lembrar and controller:
                    validade = datetime.datetime.now() + datetime.timedelta(days=30)
                    controller.set("paroquia_sf_auth", "token_seguro_sf_2026", expires=validade)
                    controller.set("paroquia_sf_user", usuario_input, expires=validade)
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# =========================================================================
# ESTILIZAÇÕES (CSS)
# =========================================================================
st.markdown("""
    <style>
    .caixa-calculo { background-color: #e3f2fd; padding: 10px; border-radius: 6px; font-weight: bold; color: #0d47a1; text-align: center; }
    .caixa-calculo-igreja { background-color: #efebe9; padding: 10px; border-radius: 6px; font-weight: bold; color: #4e342e; text-align: center; }
    .painel-diferenca { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 2px solid #dee2e6; text-align: center; margin-top: 20px; }
    .titulo-coluna { display: flex; align-items: center; background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid #004B87; margin-bottom: 10px; }
    .titulo-coluna-igreja { display: flex; align-items: center; background-color: #fdfaf6; padding: 12px; border-radius: 8px; border-left: 5px solid #8B4513; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================================
# FUNÇÕES DE PROCESSAMENTO DE ARQUIVOS
# =========================================================================
def converter_valor_extrato(val_str):
    if pd.isna(val_str): return 0.0
    val_str = str(val_str).strip().upper()
    eh_debito = 'D' in val_str or '-' in val_str
    apenas_numeros = re.sub(r'[^\d,,.]', '', val_str).replace('.', '').replace(',', '.')
    try:
        valor = float(apenas_numeros)
        return -valor if eh_debito else valor
    except: return 0.0

def processar_extrato_sicoob(arquivo_upload):
    df_s_bruto = pd.read_excel(arquivo_upload, skiprows=1)
    saldo_anterior = 0.0
    saldos_finais = {}
    dados_banco = []
    
    for _, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        historico = str(row.iloc[2]).strip().upper()
        data = row.iloc[0]
        if "SALDO ANTERIOR" in historico:
            saldo_anterior = abs(converter_valor_extrato(row.iloc[3]))
        if "SALDO DO DIA" in historico and pd.notna(data):
            dt_fmt = pd.to_datetime(str(data).strip(), dayfirst=True).strftime('%d/%m/%Y')
            saldos_finais[dt_fmt] = abs(converter_valor_extrato(row.iloc[3]))

    linha_mestre = None
    for i, row in df_s_bruto.iterrows():
        if len(row) < 4: continue
        data_orig = row.iloc[0]
        historico = str(row.iloc[2]).strip().upper()
        if "SALDO" in historico: continue
        
        if pd.notna(data_orig) and '/' in str(data_orig):
            if linha_mestre: dados_banco.append(linha_mestre)
            linha_mestre = {
                'id_banco': f"B_{i}",
                'Data': pd.to_datetime(str(data_orig).strip(), dayfirst=True).strftime('%d/%m/%Y'),
                'Histórico': historico,
                'Valor': converter_valor_extrato(row.iloc[3]),
                'Detalhes': str(row.iloc[3] if len(row)>3 else "")
            }
        else:
            if linha_mestre:
                texto_detalhe = " ".join([str(v).strip() for v in row.values if pd.notna(v)])
                linha_mestre['Detalhes'] += " " + texto_detalhe
                
    if linha_mestre: dados_banco.append(linha_mestre)
    return dados_banco, saldo_anterior, saldos_finais

def carregar_dados_upload(modo_conta, file_banco, file_sistema):
    if not file_banco: return None, None, {}
    dados_b, s_ant, s_finais = processar_extrato_sicoob(file_banco)
    
    dados_banco_finais = []
    sipag_por_dia = {}
    
    for item in dados_b:
        texto_completo = (item['Histórico'] + " " + item['Detalhes']).upper()
        if "SIPAG" in texto_completo or "COMPRAS" in texto_completo or "MAESTRO" in texto_completo:
            sipag_por_dia[item['Data']] = sipag_por_dia.get(item['Data'], 0.0) + item['Valor']
        else:
            dados_banco_finais.append(item)
            
    for dia, v_tot in sipag_por_dia.items():
        dados_banco_finais.append({
            'id_banco': f"B_SIPAG_{dia}", 'Data': dia,
            'Valor': round(v_tot, 2), 'Histórico': '💳 LOTE SIPAG / VENDAS CARTÕES (Agrupado)', 'Detalhes': ''
        })

    dados_contrapartida = []
    idx_t = 0
    if file_sistema:
        if "161" in modo_conta:
            df_t_bruto = pd.read_excel(file_sistema, skiprows=7).dropna(how='all')
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
                                'Descrição': desc, 'Valor': round(v_liq, 2)
                            })
                            idx_t += 1
        elif "140" in modo_conta:
            try:
                conteudo = file_sistema.getvalue().decode('utf-8', errors='ignore')
                df_e = pd.read_csv(io.StringIO(conteudo), skiprows=9, on_bad_lines='skip')
                df_e = df_e[df_e['Dt.Oferta'].str.contains('/', na=False)]
                for _, row in df_e.iterrows():
                    v_ecl = float(str(row['Valor (R$)']).strip().replace(',', '.'))
                    dt_obj = pd.to_datetime(row['Dt.Oferta'].strip(), dayfirst=True, errors='coerce')
                    if pd.notna(dt_obj) and v_ecl > 0:
                        dados_contrapartida.append({
                            'id_theos': f"T_{idx_t}", 'Data': dt_obj.strftime('%d/%m/%Y'),
                            'Descrição': str(row['Nome']).strip(), 'Valor': round(v_ecl, 2)
                        })
                        idx_t += 1
            except: pass

    mapa_saldos = {dia: {'Anterior': s_ant if i==0 else list(s_finais.values())[i-1], 'Final': v} for i, (dia, v) in enumerate(s_finais.items())}
    return pd.DataFrame(dados_banco_finais), pd.DataFrame(dados_contrapartida), mapa_saldos

# =========================================================================
# INTERFACE PRINCIPAL
# =========================================================================
st.title("⛪ Sistema Integrado de Conciliação Financeira")

with st.sidebar:
    st.info(f"👤 Conectado como: **{st.session_state.usuario_logado}**")
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = ""
        if controller:
            controller.remove("paroquia_sf_auth")
            controller.remove("paroquia_sf_user")
        st.rerun()
    st.markdown("---")

conta_ativa = st.selectbox("🏦 Escolha a Conta para conciliar:", ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)"])

st.markdown("### 📥 Arquivos do Período")
col_up1, col_up2 = st.columns(2)
with col_up1: u_extrato = st.file_uploader("📂 Extrato Excel do Sicoob:", type=["xlsx", "xls"])
with col_up2: u_sistema = st.file_uploader("📂 Relatório do Sistema (Theos/Eclesial):", type=["xlsx", "xls", "csv"])

if u_extrato and u_sistema:
    chave_banco = f"banco_{conta_ativa}"
    chave_sistema = f"sistema_{conta_ativa}"
    if chave_banco not in st.session_state: st.session_state[chave_banco] = []
    if chave_sistema not in st.session_state: st.session_state[chave_sistema] = []
    if 'historico' not in st.session_state: st.session_state.historico = []
    if 'historico_passos' not in st.session_state: st.session_state.historico_passos = []
    if 'idx_data' not in st.session_state: st.session_state.idx_data = 0

    df_banco_orig, df_sistema_orig, mapa_saldos = carregar_dados_upload(conta_ativa, u_extrato, u_sistema)
    
    if df_banco_orig is not None and not df_banco_orig.empty:
        df_b_pendente = df_banco_orig[~df_banco_orig['id_banco'].isin(st.session_state[chave_banco])]
        df_s_pendente = df_sistema_orig[~df_sistema_orig['id_theos'].isin(st.session_state[chave_sistema])] if not df_sistema_orig.empty else pd.DataFrame(columns=['id_theos', 'Data', 'Descrição', 'Valor'])

        todas_datas = sorted(list(set(df_banco_orig['Data'].unique()).union(set(df_sistema_orig['Data'].unique() if df_sistema_orig is not None else []))), key=lambda x: pd.to_datetime(x, dayfirst=True))

        with st.sidebar:
            st.markdown("### 🎛️ Navegação")
            data_selecionada = st.selectbox("📆 Dia:", todas_datas, index=min(st.session_state.idx_data, len(todas_datas)-1))
            st.session_state.idx_data = todas_datas.index(data_selecionada)
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("◀ Anterior", use_container_width=True) and st.session_state.idx_data > 0:
                st.session_state.idx_data -= 1
                st.rerun()
            if col_b2.button("Próximo ▶", use_container_width=True) and st.session_state.idx_data < len(todas_datas) - 1:
                st.session_state.idx_data += 1
                st.rerun()
            st.markdown("---")
            if st.button("↩️ Desfazer Última Baixa", use_container_width=True) and st.session_state.historico_passos:
                ultimo_passo = st.session_state.historico_passos.pop()
                for b_id in ultimo_passo['banco_ids']: st.session_state[chave_banco].remove(b_id)
                for t_id in ultimo_passo['theos_ids']: st.session_state[chave_sistema].remove(t_id)
                st.rerun()

        info_saldo = mapa_saldos.get(data_selecionada, {'Anterior': 0.0, 'Final': 0.0})
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("💰 Saldo Anterior Sicoob", f"R$ {info_saldo['Anterior']:,.2f}")
        col_s2.metric("🔄 Movimento do Dia (Sicoob)", f"R$ {df_banco_orig[df_banco_orig['Data'] == data_selecionada]['Valor'].sum():,.2f}")
        col_s3.metric("🏦 Saldo Final Sicoob", f"R$ {info_saldo['Final']:,.2f}")

        aba_conciliacao, aba_historico = st.tabs(["🔄 Esteira de Conciliação Diária", "📋 Relatório de Fechamento"])

        with aba_conciliacao:
            df_b_tela = df_b_pendente[df_b_pendente['Data'] == data_selecionada]
            df_s_tela = df_s_pendente[df_s_pendente['Data'] == data_selecionada]

            valores_b_abs = df_b_tela['Valor'].abs().tolist()
            valores_s_abs = df_s_tela['Valor'].abs().tolist()

            if f"marcar_{data_selecionada}" not in st.session_state:
                st.session_state[f"marcar_{data_selecionada}"] = False

            col1, col2 = st.columns(2)
            soma_banco_atual = 0.0
            soma_sistema_atual = 0.0
            selecionados_banco = []
            selecionados_sistema = []

            with col1:
                st.markdown(f'<div class="titulo-coluna"><span style="font-size:24px;">🏦</span><div class="texto-header-col">Extrato Sicoob ({len(df_b_tela)} itens)</div></div>', unsafe_allow_html=True)
                container_b = st.empty()
                if st.button("🪄 Marcar Sugestões (Banco)", key=f"btn_b_{data_selecionada}"):
                    st.session_state[f"marcar_{data_selecionada}"] = True
                    st.rerun()

                for _, row in df_b_tela.iterrows():
                    v_real = row['Valor']
                    v_abs = abs(v_real)
                    
                    # Identificador visual de ENTRADA (C) e SAÍDA (D)
                    icone_direcao = "🟢 (C)" if v_real >= 0 else "🔴 (D)"
                    
                    # Inteligência Pro: Descobre se é exato ou taxa (Baseado no valor absoluto)
                    tem_exato = v_abs in valores_s_abs
                    tem_taxa = any(sao_valores_compativeis(v_abs, v_s) for v_s in valores_s_abs)
                    
                    tag = " ⭐ [EXATO]" if tem_exato else (" 💸 [AJUSTE TAXA]" if tem_taxa else "")
                    chk_val = (tem_exato or tem_taxa) or st.session_state[f"marcar_{data_selecionada}"]
                    
                    texto_limpo = f"{row['Histórico']} {row['Detalhes']}".strip()
                    # Rótulo atualizado com o sinal visual C/D
                    label = f"{icone_direcao} R$ {v_abs:,.2f} | {texto_limpo[:40]} {tag}"
                    
                    if st.checkbox(label, key=f"b_{row['id_banco']}", value=chk_val):
                        selecionados_banco.append(row)
                        # Na soma do painel de diferença, continuamos usando o valor absoluto para bater os lados
                        soma_banco_atual += v_abs
                
                container_b.markdown(f'<div class="caixa-calculo">💰 Soma Selecionada: R$ {soma_banco_atual:,.2f}</div>', unsafe_allow_html=True)

            with col2:
                lbl = "Eclesial" if "140" in conta_ativa else "Theos"
                st.markdown(f'<div class="titulo-coluna-igreja"><span style="font-size:24px;">💻</span><div class="texto-header-col">Sistema {lbl} ({len(df_s_tela)} itens)</div></div>', unsafe_allow_html=True)
                container_s = st.empty()
                if st.button("🪄 Marcar Sugestões (Sistema)", key=f"btn_s_{data_selecionada}"):
                    st.session_state[f"marcar_{data_selecionada}"] = True
                    st.rerun()

                for _, row in df_s_tela.iterrows():
                    v_real = row['Valor']
                    v_abs = abs(v_real)
                    
                    # Identificador visual de ENTRADA (C) e SAÍDA (D)
                    icone_direcao = "🟢 (C)" if v_real >= 0 else "🔴 (D)"
                    
                    tem_exato = v_abs in valores_b_abs
                    tem_taxa = any(sao_valores_compativeis(v_b, v_abs) for v_b in valores_b_abs)
                    
                    tag = " ⭐ [EXATO]" if tem_exato else (" 💸 [AJUSTE TAXA]" if tem_taxa else "")
                    chk_val = (tem_exato or tem_taxa) or st.session_state[f"marcar_{data_selecionada}"]
                    
                    # Rótulo atualizado com o sinal visual C/D
                    label = f"{icone_direcao} R$ {v_abs:,.2f} | {row['Descrição'][:40]} {tag}"
                    
                    if st.checkbox(label, key=f"t_{row['id_theos']}", value=chk_val):
                        selecionados_sistema.append(row)
                        soma_sistema_atual += v_abs
                
                container_s.markdown(f'<div class="caixa-calculo-igreja">💰 Soma Selecionada: R$ {soma_sistema_atual:,.2f}</div>', unsafe_allow_html=True)

            # --- PAINEL PRO DE DIFERENÇA ---
            diferenca = abs(soma_banco_atual - soma_sistema_atual)
            eh_diferenca_taxa = diferenca > 0 and (soma_sistema_atual > 0 and (diferenca / soma_sistema_atual) <= 0.06)

            st.markdown("<br>", unsafe_allow_html=True)
            if soma_banco_atual > 0 or soma_sistema_atual > 0:
                if diferenca == 0:
                    status_html = f"<h3 style='color: green;'>✅ Bateu! Diferença zero.</h3>"
                elif eh_diferenca_taxa:
                    status_html = f"<h3 style='color: #d4a017;'>⚠️ Diferença de R$ {diferenca:,.2f} (Admissível por Taxa de Cartão)</h3>"
                else:
                    status_html = f"<h3 style='color: red;'>❌ Alerta: Diferença de R$ {diferenca:,.2f} entre banco e sistema.</h3>"
                
                st.markdown(f"<div class='painel-diferenca'>{status_html}</div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if selecionados_banco or selecionados_sistema:
                if st.button("✂️ Confirmar Baixa dos Itens Selecionados", type="primary", use_container_width=True):
                    passo_atual = {'banco_ids': [], 'theos_ids': []}
                    for b in selecionados_banco:
                        st.session_state[chave_banco].append(b['id_banco'])
                        passo_atual['banco_ids'].append(b['id_banco'])
                        st.session_state.historico.append({'Conta': conta_ativa.split('-')[0], 'Data': data_selecionada, 'Origem': 'Banco', 'Descrição': f"{b['Histórico']} {b['Detalhes']}".strip(), 'Valor': b['Valor']})
                    for t in selecionados_sistema:
                        st.session_state[chave_sistema].append(t['id_theos'])
                        passo_atual['theos_ids'].append(t['id_theos'])
                        st.session_state.historico.append({'Conta': conta_ativa.split('-')[0], 'Data': data_selecionada, 'Origem': 'Sistema', 'Descrição': t['Descrição'], 'Valor': t['Valor']})
                    
                    st.session_state[f"marcar_{data_selecionada}"] = False
                    st.session_state.historico_passos.append(passo_atual)
                    st.toast("Baixa confirmada com sucesso!", icon="✅")
                    st.rerun()

        with aba_historico:
            if st.session_state.historico:
                st.markdown("#### 📋 Itens Fechados nesta Sessão")
                df_hist = pd.DataFrame(st.session_state.historico)
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_hist.to_excel(writer, sheet_name='Conciliado', index=False)
                st.download_button(label="📥 Baixar Planilha de Fechamento (.xlsx)", data=buffer.getvalue(), file_name="Fechamento_Paroquial.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
            else: 
                st.info("Nenhuma baixa efetuada na sessão atual.")
else:
    st.info("💡 Por favor, carregue os relatórios nas caixas acima para iniciar o painel.")
