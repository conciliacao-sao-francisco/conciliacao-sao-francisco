import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

import streamlit as st
import pandas as pd
import re
import io
import datetime

# --- IMPORTAÇÕES E CONFIGURAÇÕES INICIAIS ---
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

# --- FUNÇÃO DE MATCH POR APROXIMAÇÃO (AJUSTE DE TAXA) ---
def sao_valores_compativeis(valor_banco, valor_sistema, margem=0.06):
    """
    Verifica se o valor do banco (líquido) é compatível com o do sistema (bruto),
    considerando uma margem de perda de até 6% (taxa de cartão).
    """
    if valor_sistema == 0: return False
    proporcao = valor_banco / valor_sistema
    # O banco deve ser entre 94% e 100% do valor do sistema
    return (1 - margem) <= proporcao <= 1.00

# --- FUNÇÕES DE PROCESSAMENTO (Mantidas as originais) ---
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
    if "PIX" in hist_u: tipo = "🟢 PIX"
    elif "SIPAG" in hist_u or "COMPRAS" in hist_u: tipo = "💳 SIPAG / CARTÃO"
    elif "TARIFA" in hist_u: tipo = "🔴 TARIFA"
    return tipo, det_u

def processar_extrato_sicoob(arquivo_upload):
    df_s_bruto = pd.read_excel(arquivo_upload, skiprows=1)
    dados_banco_brutos = []
    # ... (Lógica de processamento de linhas mantida igual ao seu original)
    return dados_banco_brutos, 0.0, {}

# --- BLOCO PRINCIPAL (Simplificado para focar na nova lógica) ---
# ... [AUTENTICAÇÃO E CSS MANTIDOS] ...

# --- DENTRO DA ABA DE CONCILIAÇÃO ---
# No loop de exibição dos checkboxes:

# ... (dentro de aba_conciliacao)
    # Lógica de match aprimorada:
    for _, row in df_banco_tela.iterrows():
        v_abs = abs(row['Valor'])
        
        # Novo Match por Aproximação
        tem_match = False
        for v_sist in valores_sistema_abs:
            if sao_valores_compativeis(v_abs, v_sist):
                tem_match = True
                break
        
        valor_padrao_chk = tem_match or st.session_state[f"marcar_todos_b_{data_selecionada}_{tipo_filtro}"]
        
        # Aviso visual de Ajuste de Taxa
        tag_match = " 💸 [AJUSTE TAXA]" if tem_match else ""
        label = f"{row.get('Tipo', '🔹')} | R$ {v_abs:,.2f} | {row.get('Detalhe_Limpo', row['Histórico'])[:35]}{tag_match}"
        
        if st.checkbox(label, key=f"b_{row['id_banco']}", value=valor_padrao_chk):
            selecionados_banco.append(row)
            soma_banco_atual += row['Valor']

# ... [RESTANTE DO CÓDIGO DE CONFIRMAÇÃO DE BAIXA]
