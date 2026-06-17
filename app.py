import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # Silencia avisos de conexão no terminal

import streamlit as st
import pandas as pd
import re
import io

# Configuração da página em modo AMPLO
st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

# --- ESTILIZAÇÃO CUSTOMIZADA (CSS) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; padding: 10px 20px; }
    thead th { background-color: #f0f2f6 !important; color: #31333F !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho com Identidade Paroquial
st.title("⛪ Sistema Integrado de Conciliação - Paróquia São Francisco de Assis")
st.caption("Painel Avançado Multi-Contas integrado ao Sicoob, Theos e Eclesial com upload dinâmico de arquivos.")

# --- SELETOR DA CONTA ATIVA NO TOPO DO APP ---
conta_ativa = st.selectbox(
    "🏦 Escolha a Conta Bancária que deseja conciliar agora:",
    ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)"]
)

# --- FUNÇÃO DE CONVERSÃO MONETÁRIA ---
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

# --- FUNÇÃO DE LIMPEZA E EXTRAÇÃO DE NOMES DO SICOOB ---
def extrair_detalhe_limpo(historico, detalhes):
    hist_u = str(historico).upper().strip()
    det_u = str(detalhes).upper().strip()
    
    tipo = "🔹 OUTROS"
    if "PIX RECEBIDO" in hist_u or "RECEBIDO DE OUTRA IF" in hist_u: tipo = "🟢 PIX RECEBIDO"
    elif "PIX ENVIADO" in hist_u or "PIX TRANSFERIDO" in hist_u: tipo = "🔴 PIX ENVIADO"
    elif "PAGTO TITULO" in hist_u or "PAGAMENTO" in hist_u: tipo = "🔴 PAGTO TITULO"
    elif "TARIFA" in hist_u or "TAR EXTRATO" in hist_u: tipo = "🔴 TAR TARIFA"
    elif "ESTORNO" in hist_u: tipo = "🟢 ESTORNO"
    elif "TRANSF" in hist_u and "RECEB" in hist_u: tipo = "🟢 TRANSF RECEBIDA"
    elif "TRANSF" in hist_u: tipo = "🔴 TRANSF ENVIADA"

    limpeza_regex = [
        r"RECEBIDO DE OUTRA IF", r"PIX TRANSFERIDO", r"PIX RECEBIDO", r"PAGTO TITULO INTERNET",
        r"COMPLEMENTO:", r"VALOR DO COMPROMISSO", r"COBRANCA SICOOB", r"FAVORECIDO:", r"PAGADOR:",
        r"REMETENTE:", r"AGENCIA:", r"CONTA:", r"CPF:", r"CNPJ:", r"-\s*$"
    ]
    
    nome_isolado = det_u
    for padrao in limpeza_regex:
        nome_isolado = re.sub(padrao, "", nome_isolado)
        
    nome_isolado = re.sub(r'\s+', ' ', nome_isolado).strip()
    nome_isolado = nome_isolado.lstrip('-').strip()
    
    if not nome_isolado or len(nome_isolado) < 3:
        nome_isolado = hist_u

    return tipo, nome_isolado

# --- LEITURA PADRÃO DO EXTRATO DO SICOOB ---
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
            v_limpo = converter_valor_extrato(row.iloc[3])
            linha_mestre = {
                'Data': pd.to_datetime(str(data_orig).strip(), dayfirst=True).strftime('%d/%m/%Y'),
                'Documento': str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else '',
                'Histórico': historico, 'Valor': v_limpo, 'Detalhes': ''
            }
        else:
            if linha_mestre:
                texto_detalhe = " ".join([str(v).strip() for v in row.values if pd.notna(v)])
                linha_mestre['Detalhes'] += " " + texto_detalhe
                
    if linha_mestre: dados_banco_brutos.append(linha_mestre)
    return dados_banco_brutos, saldo_anterior_inicial, saldos_finais_por_dia

# --- MOTOR DE INTELIGÊNCIA DE CARREGAMENTO POR UPLOAD ---
def carregar_dados_upload(modo_conta, file_banco, file_sistema):
    if not file_banco or not file_sistema:
        return None, None, {}
        
    dados_b, s_ant, s_finais = processar_extrato_sicoob(file_banco)
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
            'Tipo': '💳 SIPAG LOTE', 'Detalhe_Limpo': "VENDAS CARTÕES DE CRÉDITO/DÉBITO (Agrupado)",
            'Valor': round(v_tot, 2), 'Histórico': 'SIPAG', 'Detalhes': ''
        })
        idx_b += 1
        
    dados_contrapartida = []
    idx_t = 0
    
    if "Conta 161" in modo_conta:
        # Processamento do Boletim do Theos (Excel)
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
                        tipo_sys = "🟢 ENTRADA" if v_liq > 0 else "🔴 SAÍDA"
                        dados_contrapartida.append({
                            'id_theos': f"T_{idx_t}", 'Data': dt_obj.strftime('%d/%m/%Y'),
                            'Tipo': tipo_sys, 'Descrição': desc, 'Valor': round(v_liq, 2)
                        })
                        idx_t += 1
    else:
        # Processamento do Dízimo Eclesial (CSV)
        try:
            # Tenta decodificar o arquivo enviado dinamicamente
            conteudo = file_sistema.getvalue().decode('utf-8', errors='ignore')
            df_e = pd.read_csv(io.StringIO(conteudo), skiprows=9, on_bad_lines='skip')
            df_e = df_e[df_e['Dt.Oferta'].str.contains('/', na=False)]
            df_e = df_e[df_e['Nome'].notna() & (df_e['Nome'] != 'Nome')]
            for idx_e, row in df_e.iterrows():
                try:
                    v_ecl = float(str(row['Valor (R$)']).strip().replace(',', '.'))
                    dt_obj = pd.to_datetime(row['Dt.Oferta'].strip(), dayfirst=True, errors='coerce')
                    if pd.notna(dt_obj) and v_ecl > 0:
                        dados_contrapartida.append({
                            'id_theos': f"T_{idx_e}", 'Data': dt_obj.strftime('%d/%m/%Y'),
                            'Tipo': "🟢 DÍZIMO ECLESIAL", 'Descrição': str(row['Nome']).strip(), 'Valor': round(v_ecl, 2)
                        })
                except: continue
        except Exception as e:
            st.error(f"Erro ao processar o formato do arquivo Eclesial: {e}")
            
    mapa_saldos = {dia: {'Anterior': s_ant if i==0 else list(s_finais.values())[i-1], 'Final': v} for i, (dia, v) in enumerate(s_finais.items())}
    return pd.DataFrame(dados_banco_finais), pd.DataFrame(dados_contrapartida), mapa_saldos

# --- INTERFACE DE ARRASTAR E SOLTAR ARQUIVOS ---
st.markdown("### 📥 Carregar Arquivos do Dia")
col_up1, col_up2 = st.columns(2)

with col_up1:
    u_extrato = st.file_uploader("📂 Arraste o Extrato Excel do Sicoob aqui:", type=["xlsx", "xls"])

with col_up2:
    if "Conta 161" in conta_ativa:
        u_sistema = st.file_uploader("📂 Arraste o Relatório do Boletim (Theos) aqui:", type=["xlsx", "xls"])
    else:
        u_sistema = st.file_uploader("📂 Arraste a Conferência do Dízimo (Eclesial) aqui:", type=["csv"])

# --- GERENCIAMENTO DE SESSÕES ---
chave_banco = f"cortes_banco_{conta_ativa}"
chave_sistema = f"cortes_sistema_{conta_ativa}"
if chave_banco not in st.session_state: st.session_state[chave_banco] = []
if chave_sistema not in st.session_state: st.session_state[chave_sistema] = []
if 'historico_cortes' not in st.session_state: st.session_state.historico_cortes = []
if 'historico_passos' not in st.session_state: st.session_state.historico_passos = []
if 'indice_data' not in st.session_state: st.session_state.indice_data = 0

# Executa o cruzamento apenas se os dois arquivos forem inseridos na tela
if u_extrato and u_sistema:
    df_banco_orig, df_sistema_orig, mapa_saldos = carregar_dados_upload(conta_ativa, u_extrato, u_sistema)
    
    if df_banco_orig is not None and not df_banco_orig.empty:
        if 'Tipo' not in df_banco_orig.columns: df_banco_orig['Tipo'] = "🔹 OUTROS"
        if 'Detalhe_Limpo' not in df_banco_orig.columns: df_banco_orig['Detalhe_Limpo'] = df_banco_orig['Histórico']

        df_banco_pendente = df_banco_orig[~df_banco_orig['id_banco'].isin(st.session_state[chave_banco])]
        if df_sistema_orig is not None and not df_sistema_orig.empty:
            df_sistema_pendente = df_sistema_orig[~df_sistema_orig['id_theos'].isin(st.session_state[chave_sistema])]
        else:
            df_sistema_pendente = pd.DataFrame(columns=['id_theos', 'Data', 'Tipo', 'Descrição', 'Valor'])

        todas_datas = sorted(list(set(df_banco_orig['Data'].unique()).union(set(df_sistema_orig['Data'].unique() if df_sistema_orig is not None else []))),
                             key=lambda x: pd.to_datetime(x, dayfirst=True))

        # --- CONTROLADOR LATERAL DE DIAS ---
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
                for b_id in ultimo_passo['banco_ids']: st.session_state[chave_banco].remove(b_id)
                for t_id in ultimo_passo['theos_ids']: st.session_state[chave_sistema].remove(t_id)
                st.rerun()

        # --- CARDS DE SALDO NO TOPO ---
        info_saldo = mapa_saldos.get(data_selecionada, {'Anterior': 0.0, 'Final': 0.0})
        df_banco_dia = df_banco_orig[df_banco_orig['Data'] == data_selecionada]
        fluxo_dia = df_banco_dia['Valor'].sum()
        
        st.markdown("---")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1: st.metric(label="💰 Saldo Anterior Real", value=f"R$ {info_saldo['Anterior']:,.2f}")
        with col_s2: st.metric(label="🔄 Movimentação Líquida", value=f"R$ {fluxo_dia:,.2f}", delta=f"{fluxo_dia:,.2f}")
        with col_s3: st.metric(label="🏦 Saldo Final Sicoob", value=f"R$ {info_saldo['Final']:,.2f}")

        # --- ABAS INTERATIVAS ---
        aba_conciliacao, aba_historico = st.tabs(["🔄 Esteira de Conciliação Diária", "📋 Histórico de Fechamento"])

        with aba_conciliacao:
            st.markdown(f"#### Lançamentos pendentes em: `{data_selecionada}`")
            df_banco_tela = df_banco_dia[~df_banco_dia['id_banco'].isin(st.session_state[chave_banco])]
            df_sistema_tela = df_sistema_pendente[df_sistema_pendente['Data'] == data_selecionada]

            valores_banco_abs = df_banco_tela['Valor'].abs().tolist()
            valores_sistema_abs = df_sistema_tela['Valor'].abs().tolist() if not df_sistema_tela.empty else []

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### 🏦 Extrato Sicoob (Detalhado)")
                selecionados_banco = []
                if df_banco_tela.empty: st.caption("Tudo liquidado neste dia!")
                for _, row in df_banco_tela.iterrows():
                    v_abs = abs(row['Valor'])
                    tem_match = v_abs in valores_sistema_abs
                    tag_match = " ⭐ [BATE]" if tem_match else ""
                    
                    label = f"{row.get('Tipo', '🔹 OUTROS')} | R$ {v_abs:,.2f} | {row.get('Detalhe_Limpo', row['Histórico'])[:40]}{tag_match}"
                    if st.checkbox(label, key=f"b_{row['id_banco']}", value=tem_match):
                        selecionados_banco.append(row)

            with col2:
                lbl_sist = "💻 Paróquia/Eclesial (Dízimos)" if "140" in conta_ativa else "💻 Paróquia/Boletim Theos"
                st.markdown(f"##### {lbl_sist}")
                selecionados_sistema = []
                if df_sistema_tela.empty: st.caption("Nenhum lançamento no sistema hoje.")
                for _, row in df_sistema_tela.iterrows():
                    v_abs = abs(row['Valor'])
                    tem_match = v_abs in valores_banco_abs
                    tag_match = " ⭐ [BATE]" if tem_match else ""
                    
                    label = f"{row.get('Tipo', '🔹 OUTROS')} | R$ {v_abs:,.2f} | {row['Descrição'][:40]}{tag_match}"
                    if st.checkbox(label, key=f"t_{row['id_theos']}", value=tem_match):
                        selecionados_sistema.append(row)

            # Confirmador de Baixas Dinâmico
            st.markdown("---")
            if selecionados_banco or selecionados_sistema:
                if st.button("✂️ Confirmar Baixa dos Itens Selecionados", type="primary", use_container_width=True):
                    passo_atual = {'banco_ids': [], 'theos_ids': []}
                    for b in selecionados_banco:
                        st.session_state[chave_banco].append(b['id_banco'])
                        passo_atual['banco_ids'].append(b['id_banco'])
                        st.session_state.historico_cortes.append({'Conta': conta_ativa.split('-')[0], 'Origem': 'Banco', 'Data': data_selecionada, 'Descrição': b.get('Detalhe_Limpo', b['Histórico']), 'Valor': b['Valor']})
                    for t in selecionados_sistema:
                        st.session_state[chave_sistema].append(t['id_theos'])
                        passo_atual['theos_ids'].append(t['id_theos'])
                        st.session_state.historico_cortes.append({'Conta': conta_ativa.split('-')[0], 'Origem': 'Sistema', 'Data': data_selecionada, 'Descrição': t['Descrição'], 'Valor': t['Valor']})
                    st.session_state.historico_passos.append(passo_atual)
                    st.toast("Baixa efetuada com sucesso!", icon="✅")
                    st.rerun()

        with aba_historico:
            if st.session_state.historico_cortes:
                st.markdown("#### 📋 Relatório de Itens Fechados nesta Sessão")
                df_hist = pd.DataFrame(st.session_state.historico_cortes)
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_hist.to_excel(writer, sheet_name='Conciliado', index=False)
                st.download_button(label="📥 Baixar Planilha de Fechamento (.xlsx)", data=output.getvalue(), file_name="Fechamento_Paroquial.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else:
                st.info("Nenhuma baixa efetuada na sessão atual.")
else:
    st.info("💡 Para iniciar, escolha a conta no topo e arraste os dois arquivos correspondentes nas caixas acima.")