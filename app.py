import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)  # Silencia avisos no terminal

import streamlit as st
import pandas as pd
import re
import io

# Tenta importar o leitor de PDF (instalar via requirements.txt)
try:
    import pypdf
except ImportError:
    pypdf = None

# Configuração da página em modo AMPLO
st.set_page_config(page_title="Conciliador Multi-Contas São Francisco", layout="wide")

# =========================================================================
# 🔐 SISTEMA DE SEGURANÇA E CONTROLO DE ACESSO
# =========================================================================
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
                <p style="text-align: center; color: #6c757d; font-size: 14px; margin-bottom: 25px;">Acesso Restrito ao Painel de Conciliation Financeira</p>
            </div>
        """, unsafe_allow_html=True)
        
        usuario_input = st.text_input("👤 Nome de Usuário:")
        senha_input = st.text_input("🔑 Senha de Acesso:", type="password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔓 Entrar no Sistema", type="primary", use_container_width=True):
            if usuario_input == "secretaria" and senha_input == "sf@2026":
                st.session_state.autenticado = True
                st.session_state.usuario_logado = usuario_input
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos! Tente novamente.")
                
    st.stop()

# =========================================================================
# ⛪ O SISTEMA SÓ COMEÇA DAQUI PARA BAIXO SE ESTIVER AUTENTICADO
# =========================================================================

# --- IMAGENS EMBUTIDAS EM VETOR ---
IMAGEM_BANCO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="45" height="45" style="vertical-align: middle; margin-right: 10px;"><rect x="15" y="75" width="70" height="12" rx="2" fill="#003366"/><polygon points="50,15 10,40 90,40" fill="#004B87"/><rect x="25" y="40" width="8" height="35" fill="#006699"/><rect x="46" y="40" width="8" height="35" fill="#006699"/><rect x="67" y="40" width="8" height="35" fill="#006699"/><circle cx="50" cy="28" r="4" fill="#FFD700"/></svg>"""
IMAGEM_IGREJA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="45" height="45" style="vertical-align: middle; margin-right: 10px;"><path d="M50 12 L82 45 L18 45 Z" fill="#8B4513"/><rect x="26" y="45" width="48" height="42" rx="2" fill="#D2B48C"/><rect x="44" y="62" width="12" height="25" rx="3" fill="#5C4033"/><path d="M50 45 A 8 8 0 0 1 50 29 A 8 8 0 0 1 50 45 Z" fill="#F5F5DC"/><line x1="50" y1="2" x2="50" y2="15" stroke="#FFD700" stroke-width="4"/><line x1="42" y1="8" x2="58" y2="8" stroke="#FFD700" stroke-width="4"/></svg>"""

# --- ESTILIZAÇÃO CUSTOMIZADA (CSS) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; padding: 10px 20px; }
    thead th { background-color: #f0f2f6 !important; color: #31333F !important; font-weight: bold !important; }
    .titulo-coluna { display: flex; align-items: center; background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #004B87; margin-bottom: 15px; }
    .titulo-coluna-igreja { display: flex; align-items: center; background-color: #fdfaf6; padding: 10px; border-radius: 8px; border-left: 5px solid #8B4513; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho Principal
st.title("⛪ Sistema Integrado de Conciliação - Paróquia São Francisco de Assis")

# Botão de Logoff na barra lateral
with st.sidebar:
    st.markdown("### 👤 Usuário Ativo")
    st.info(f"Conectado como: **{st.session_state.usuario_logado}**")
    if st.button("🔒 Sair do Sistema (Logoff)", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_logado = ""
        st.rerun()
    st.markdown("---")

# --- SELETOR DA CONTA ATIVA NO TOPO DO APP ---
conta_ativa = st.selectbox(
    "🏦 Escolha a Conta Bancária que deseja conciliar agora:",
    ["Conta 161 - Geral (Theos)", "Conta 140 - Dízimo (Eclesial)", "Contas Poupança - PIX Oferta (Centros de Custo)"]
)

# --- FUNÇÃO DE CONVERSÃO MONETÁRIA DE TEXTO ---
def limpar_valor_string(texto_val):
    if not texto_val: return 0.0
    texto_val = str(texto_val).strip().upper()
    eh_debito = '-' in texto_val or 'D' in texto_val
    apenas_num = re.sub(r'[^\d,,.]', '', texto_val)
    if not apenas_num: return 0.0
    if ',' in apenas_num and '.' in apenas_num:
        apenas_num = apenas_num.replace('.', '')
    apenas_num = apenas_num.replace(',', '.')
    try:
        val = float(apenas_num)
        return -val if eh_debito else val
    except:
        return 0.0

# --- MOTOR DE LEITURA EXCLUSIVO PARA O PDF DA POUPANÇA ---
def extrair_dados_pdf_poupanca(arquivo_pdf):
    if pypdf is None:
        st.error("Erro: A biblioteca 'pypdf' não está instalada. Crie o arquivo requirements.txt.")
        return []
        
    leitores_pdf = pypdf.PdfReader(arquivo_pdf)
    linhas_finais = []
    
    # Padrão Regex para capturar data brasileira dd/mm/aaaa
    regex_data = re.compile(r'(\d{2}/\d{2}/\d{4})')
    
    for pagina in leitores_pdf.pages:
        texto_pag = pagina.extract_text()
        if not texto_pag: continue
        
        for linha in texto_pag.split('\n'):
            linha_u = linha.upper().strip()
            # Procura por linhas que tenham datas e valores válidos
            contem_data = regex_data.search(linha_u)
            if contem_data:
                data_encontrada = contem_data.group(1)
                
                # Identifica o tipo do lançamento
                tipo = "🔹 OFERTA / PIX"
                if "JUROS" in linha_u or "REND" in linha_u or "SELIC" in linha_u or "CRED.REND" in linha_u:
                    tipo = "📈 RENDIMENTO POUPANÇA"
                elif "SALDO" in linha_u:
                    continue # Ignora linhas de saldo do PDF
                
                # Procura o valor no final da linha (ex: 150,00 ou 1.250,33C)
                partes = linha_u.split()
                if len(partes) >= 3:
                    valor_str = partes[-1]
                    valor_num = limpar_valor_string(valor_str)
                    
                    # Se o último bloco não virou número, tenta o penúltimo (tratamento de letras C/D coladas)
                    if valor_num == 0.0 and len(partes) > 1:
                        valor_str = partes[-2]
                        valor_num = limpar_valor_string(valor_str)
                        
                    if valor_num != 0.0:
                        # Limpa a descrição removendo a data e o valor
                        desc_limpa = linha_u.replace(data_encontrada, "").replace(partes[-1], "").strip()
                        linhas_finais.append({
                            'Data': data_encontrada,
                            'Tipo': tipo,
                            'Descrição': desc_limpa,
                            'Valor': valor_num
                        })
                        
    return linhas_finais

# --- RENDERIZAÇÃO DA INTERFACE POR TIPO DE CONTA ---
st.markdown("### 📥 Carregar Arquivos")

if "Poupança" in conta_ativa:
    u_pdf = st.file_uploader("📂 Arraste o Extrato em formato PDF da Poupança aqui:", type=["pdf"])
    
    if u_pdf:
        with st.spinner("Processando e calculando dados do PDF..."):
            dados_pdf = extrair_dados_pdf_poupanca(u_pdf)
            
        if dados_pdf:
            df_p = pd.DataFrame(dados_pdf)
            st.success("✅ Extrato em PDF lido com sucesso!")
            
            st.markdown("---")
            st.subheader("📊 Relatório de Repasse para a Cúria (Expurgo de Selic/Juros)")
            
            # Seletor de datas baseado nas datas encontradas no PDF
            todas_datas = sorted(df_p['Data'].unique(), key=lambda x: pd.to_datetime(x, dayfirst=True))
            data_sel = st.selectbox("📆 Escolha o Dia do Repasse:", todas_datas)
            
            # Filtragem do dia específico
            df_dia = df_p[df_p['Data'] == data_sel]
            
            df_ofertas = df_dia[df_dia['Tipo'] == "🔹 OFERTA / PIX"]
            df_rendimentos = df_dia[df_dia['Tipo'] == "📈 RENDIMENTO POUPANÇA"]
            
            tot_ofertas = df_ofertas[df_ofertas['Valor'] > 0]['Valor'].sum()
            tot_rendimentos = df_rendimentos['Valor'].sum()
            valor_liquido = tot_ofertas
            
            # Cards de visualização matemática
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1: st.metric("📥 Total Entradas (Ofertas/PIX)", f"R$ {tot_ofertas:,.2f}")
            with col_c2: st.metric("📈 Rendimentos Isolados (Selic/Juros)", f"R$ {tot_rendimentos:,.2f}", delta="- Rendimento Retido", delta_color="inverse")
            with col_c3: st.metric("⭐ VALOR LÍQUIDO PARA A CÚRIA", f"R$ {valor_liquido:,.2f}")
            
            # Tabelas na tela
            st.markdown("### 🔍 Detalhes dos Lançamentos do Dia")
            t_aba1, t_aba2 = st.tabs(["💰 Entradas de Ofertas", "📈 Juros/Selic Retidos"])
            
            with t_aba1:
                if not df_ofertas.empty:
                    st.dataframe(df_ofertas[['Descrição', 'Valor']], use_container_width=True, hide_index=True)
                else: st.info("Nenhuma oferta ou PIX neste dia.")
                
            with t_aba2:
                if not df_rendimentos.empty:
                    st.dataframe(df_rendimentos[['Descrição', 'Valor']], use_container_width=True, hide_index=True)
                    st.success(f"✅ O valor de R$ {tot_rendimentos:,.2f} foi removido do repasse automaticamente.")
                else: st.info("Nenhum juro ou rendimento creditado nesta data.")
        else:
            st.warning("⚠️ Nenhuma linha de movimentação financeira válida foi encontrada dentro do PDF enviado. Verifique se o arquivo está correto.")

else:
    # Código padrão para as contas 161 e 140 que utilizam Excel e CSV
    st.info("💡 Para as contas Geral e Dízimo, utilize a versão padrão de conciliação enviando os arquivos Excel/CSV.")