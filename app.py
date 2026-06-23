import streamlit as st
import datetime

# --- INSIRA ESTE BLOCO NO SEU CÓDIGO ONDE DESEJAR EXIBIR O FORMULÁRIO ---

st.markdown("### 📝 Registrar Movimentação Bancária (Padrão Boletim Theòs)")

# Container externo para simular a tela do sistema
with st.container(border=True):
    
    # -------------------------------------------------------------------------
    # SEÇÃO 1: CABEÇALHO (Origem e Banco)
    # -------------------------------------------------------------------------
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.text_input("Origem", value="BNC - Banco", disabled=True, key="lnc_origem")
    with c2:
        # Busca automaticamente a conta ativa selecionada no topo do seu site
        st.text_input("Código Banco", value="161" if "161" in conta_ativa else "140", disabled=True)
    with c3:
        st.text_input("Nome do Banco / Conta", value=conta_ativa, disabled=True)
        
    cc1, cc2, cc3 = st.columns(3)
    cc1.caption("💰 **Saldo atual:** R$ 0,00")
    cc2.caption("🔢 **Nº recibo:** --")
    cc3.caption("🔢 **Nº lançamento:** --")

    st.markdown("<hr style='margin: 10px 0; border-color: #dee2e6;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # SEÇÃO 2: LANÇAMENTO (Dados principais)
    # -------------------------------------------------------------------------
    st.markdown("<span style='color: #003366; font-weight: bold;'>🔹 Lançamento</span>", unsafe_allow_html=True)
    
    l_col1, l_col2 = st.columns([1, 1])
    with l_col1:
        data_lanc = st.date_input("Data", value=datetime.date.today(), format="DD/MM/YYYY", key="lnc_data")
    with l_col2:
        tipo_mov = st.selectbox("Entrada/Saída", ["Entrada", "Saída"], key="lnc_tipo")
        
    # Campos de busca (Simulando as lupas do Theòs)
    lanc_padrao = st.text_input("🔍 Lançamento padrão (Nome ou Código):", placeholder="Ex: 102 - RECEITA DE DIZIMO")
    centro_custo_lnc = st.text_input("🔍 Centro de custo:", placeholder="Ex: 01.01 - PAROQUIA SAO FRANCISCO")
    nominal_cheque = st.text_input("Nominal cheque / Favorecido:")

    st.markdown("<hr style='margin: 10px 0; border-color: #dee2e6;'>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # SEÇÃO 3: PARTIDAS (Valores e Documento)
    # -------------------------------------------------------------------------
    st.markdown("<span style='color: #003366; font-weight: bold;'>🔹 Partidas</span>", unsafe_allow_html=True)
    
    with st.container(border=True):
        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        with p_col1:
            tipo_doc = st.selectbox("Tipo de documento", ["<Nenhum>", "PIX", "BOLETO", "DINHEIRO", "CHEQUE", "TRANSFERENCIA"])
        with p_col2:
            num_doc = st.text_input("Documento (Nº Ref.)", placeholder="Digite o número se houver")
        with p_col3:
            valor_lnc = st.number_input("Valor R$", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            
        hist_padrao = st.text_input("🔍 Histórico padrão:")
        hist_comp = st.text_area("Histórico complementar:", value="(DOCUMENTO)", height=80)
        
        # Alinhamento do botão e totalizador igual à imagem
        b_col1, b_col2 = st.columns([3, 1])
        with b_col1:
            st.markdown("<br>", unsafe_allow_html=True)
            # Checkbox de múltiplas partidas
            multi_partidas = st.checkbox("Lançamento multipartidas")
        with b_col2:
            st.write("") # Espaçador
            btn_adicionar = st.button("➕ Adicionar Partida", use_container_width=True)
            
    # -------------------------------------------------------------------------
    # SEÇÃO 4: SALVAR NO EXCEL (Simulando o botão Gravar do sistema)
    # -------------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    col_salvar1, col_salvar2 = st.columns([2, 1])
    
    with col_salvar2:
        if st.button("💾 Gravar Lançamento no Boletim", type="primary", use_container_width=True):
            # Lógica que junta as informações na memória do Streamlit
            novo_ajuste = {
                "id": f"MANUAL_{int(datetime.datetime.now().timestamp())}",
                "acao": "inserir",
                "data": data_lanc.strftime('%d/%m/%Y'),
                "desc": f"{lanc_padrao} - {hist_comp}".strip().upper(),
                "valor": valor_lnc if tipo_mov == "Entrada" else -valor_lnc,
                "origem": "Sistema"  # Vai direto para a coluna do Boletim Theòs no site
            }
            
            # Alimenta a memória de modificações que você já tem no código
            st.session_state[chave_modificacoes].append(novo_ajuste)
            
            # Salva no arquivo JSON de cache para não perder ao atualizar a página
            with open(arq_cache_modificacoes, "w", encoding="utf-8") as f:
                json.dump(st.session_state[chave_modificacoes], f, ensure_ascii=False)
                
            st.success("✅ Lançamento simulado com sucesso no Boletim!")
            st.rerun()
