# Chaves de Estado Fixas na Sessão (Persistem ao F5)
chave_store_banco = f"bytes_banco_{conta_ativa}"
chave_store_sistema = f"bytes_sistema_{conta_ativa}"
chave_store_sipag = f"bytes_sipag_{conta_ativa}"
chave_nome_banco = f"nome_banco_{conta_ativa}"
chave_nome_sistema = f"nome_sistema_{conta_ativa}"
chave_nome_sipag = f"nome_sipag_{conta_ativa}"

# Inicialização segura na sessão se não existirem
if chave_store_banco not in st.session_state: st.session_state[chave_store_banco] = None
if chave_store_sistema not in st.session_state: st.session_state[chave_store_sistema] = None
if chave_store_sipag not in st.session_state: st.session_state[chave_store_sipag] = None

st.markdown("### 📥 Carregar Arquivos do Período")
col_up1, col_up2, col_up3 = st.columns(3)

with col_up1:
    # Mudamos o 'key' do widget para não colidir diretamente com o armazenamento
    u_extrato = st.file_uploader("📂 Arraste o Extrato do Sicoob:", type=["xlsx", "xls", "pdf"], key=f"widget_up_banco_{conta_ativa}")
    
    # ATENÇÃO: Só atualiza a sessão se o usuário REALMENTE enviou um arquivo novo. 
    # Se u_extrato for None (como após um F5), mantém o que já estava guardado!
    if u_extrato is not None:
        st.session_state[chave_store_banco] = u_extrato.getvalue()
        st.session_state[chave_nome_banco] = u_extrato.name
        
    if st.session_state[chave_store_banco] is not None:
        st.success(f"🟢 Memória Ativa: {st.session_state.get(chave_nome_banco, 'Extrato Guardado')}")

with col_up2:
    u_sistema = st.file_uploader("📂 Arraste o Relatório do Boletim / Sistema:", type=["xlsx", "xls", "csv"], key=f"widget_up_sist_{conta_ativa}")
    if u_sistema is not None:
        st.session_state[chave_store_sistema] = u_sistema.getvalue()
        st.session_state[chave_nome_sistema] = u_sistema.name
        
    if st.session_state[chave_store_sistema] is not None:
        st.success(f"🟢 Memória Ativa: {st.session_state.get(chave_nome_sistema, 'Sistema Guardado')}")

with col_up3:
    u_sipag = st.file_uploader("📂 Planilha do Cartão SIPAG (CSV):", type=["csv", "xlsx"], key=f"widget_up_sipag_{conta_ativa}")
    if u_sipag is not None:
        st.session_state[chave_store_sipag] = u_sipag.getvalue()
        st.session_state[chave_nome_sipag] = u_sipag.name
        
    if st.session_state[chave_store_sipag] is not None:
        st.success(f"🟢 Memória Ativa: {st.session_state.get(chave_nome_sipag, 'SIPAG Guardada')}")

# Botão para limpar a memória explicitamente se o usuário quiser trocar os arquivos
if st.session_state[chave_store_banco] or st.session_state[chave_store_sistema] or st.session_state[chave_store_sipag]:
    if st.button("🗑️ Trocar / Limpar Arquivos da Tela", use_container_width=True):
        st.session_state[chave_store_banco] = None
        st.session_state[chave_store_sistema] = None
        st.session_state[chave_store_sipag] = None
        st.session_state[chave_nome_banco] = None
        st.session_state[chave_nome_sistema] = None
        st.session_state[chave_nome_sipag] = None
        st.rerun()
