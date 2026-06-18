col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="titulo-coluna"><span style="font-size:24px;">🏦</span><div class="texto-header-col">Extrato Sicoob<br><span style="font-size:12px; color:#666; font-weight:normal;">' + str(len(df_banco_tela)) + ' exibidos neste tipo</span></div></div>', unsafe_allow_html=True)
                container_calculo_banco = st.empty()
                
                if not df_banco_tela.empty:
                    if st.button("⭐ Selecionar Match Automático (Banco)", key=f"btn_b_{data_selecionada}_{tipo_filtro}"):
                        st.session_state[f"marcar_todos_b_{data_selecionada}_{tipo_filtro}"] = True
                        st.rerun()

                selecionados_banco = []
                soma_banco_atual = 0.0
                
                if df_banco_tela.empty: 
                    st.success("✅ Nenhum item pendente deste tipo no banco!")
                
                # CHAVE DE EDIÇÃO PARA O BANCO
                chave_edicoes_banco = f"edicoes_banco_{conta_ativa}"
                if chave_edicoes_banco not in st.session_state:
                    st.session_state[chave_edicoes_banco] = {}

                for _, row in df_banco_tela.iterrows():
                    b_id = row['id_banco']
                    
                    # Aplica a edição dinâmica se existir no estado da sessão
                    desc_banco = st.session_state[chave_edicoes_banco].get(b_id, {}).get('Descrição', row.get('Detalhe_Limpo', row['Histórico']))
                    val_banco = st.session_state[chave_edicoes_banco].get(b_id, {}).get('Valor', row['Valor'])
                    
                    v_abs = abs(val_banco)
                    tem_match = v_abs in valores_sistema_abs
                    valor_padrao_chk = tem_match or st.session_state[f"marcar_todos_b_{data_selecionada}_{tipo_filtro}"]
                    tag_match = " ⭐ [BATE]" if tem_match else ""
                    
                    label = f"{row.get('Tipo', '🔹 OUTROS')} | R$ {v_abs:,.2f} | {desc_banco[:35]}{tag_match}"
                    
                    # Divisão de layout: Caixa de Seleção à esquerda e Botão de Edição à direita
                    col_chk, col_edit = st.columns([0.88, 0.12])
                    with col_chk:
                        if st.checkbox(label, key=f"b_{b_id}", value=valor_padrao_chk):
                            # Preserva o item modificado para vinculação nas seleções múltiplas
                            row_modificada = row.copy()
                            row_modificada['Detalhe_Limpo'] = desc_banco
                            row_modificada['Valor'] = val_banco
                            selecionados_banco.append(row_modificada)
                            soma_banco_atual += val_banco
                            
                    with col_edit:
                        with st.popover("⚙️", help="Ajustar dados deste registro do banco"):
                            st.write("✏️ **Corrigir Informações do Extrato**")
                            novo_desc = st.text_input("Alterar Descrição:", value=desc_banco, key=f"desc_inp_b_{b_id}")
                            novo_val = st.number_input("Alterar Valor (R$):", value=float(val_banco), step=1.00, format="%.2f", key=f"val_inp_b_{b_id}")
                            if st.button("Salvar Correção", key=f"btn_salvar_b_{b_id}", use_container_width=True):
                                st.session_state[chave_edicoes_banco][b_id] = {'Descrição': novo_desc, 'Valor': novo_val}
                                st.rerun()
                
                container_calculo_banco.markdown(f'<div class="caixa-calculo">📊 Selecionados: {len(selecionados_banco)} itens | Soma Atual: R$ {soma_banco_atual:,.2f}</div>', unsafe_allow_html=True)

            with col2:
                lbl_sist = "💻 Paróquia / Eclesial (Dízimos)" if "140" in conta_ativa else "💻 Paróquia / Boletim Theos"
                st.markdown('<div class="titulo-coluna-igreja"><span style="font-size:24px;">⛪</span><div class="texto-header-col">' + lbl_sist + '<br><span style="font-size:12px; color:#666; font-weight:normal;">' + str(len(df_sistema_tela)) + ' exibidos neste tipo</span></div></div>', unsafe_allow_html=True)
                container_calculo_sistema = st.empty()
                
                if not df_sistema_tela.empty:
                    if st.button("⭐ Selecionar Match Automático (Sistema)", key=f"btn_s_{data_selecionada}_{tipo_filtro}"):
                        st.session_state[f"marcar_todos_s_{data_selecionada}_{tipo_filtro}"] = True
                        st.rerun()

                selecionados_sistema = []
                soma_sistema_atual = 0.0
                
                if df_sistema_tela.empty: 
                    st.success("✅ Nenhum lançamento pendente deste tipo no sistema.")
                
                # CHAVE DE EDIÇÃO PARA O SISTEMA
                chave_edicoes_sistema = f"edicoes_sistema_{conta_ativa}"
                if chave_edicoes_sistema not in st.session_state:
                    st.session_state[chave_edicoes_sistema] = {}

                for _, row in df_sistema_tela.iterrows():
                    t_id = row['id_theos']
                    
                    # Aplica a edição dinâmica se existir no estado da sessão
                    desc_sistema = st.session_state[chave_edicoes_sistema].get(t_id, {}).get('Descrição', row['Descrição'])
                    val_sistema = st.session_state[chave_edicoes_sistema].get(t_id, {}).get('Valor', row['Valor'])
                    
                    v_abs = abs(val_sistema)
                    tem_match = v_abs in valores_banco_abs
                    valor_padrao_chk = tem_match or st.session_state[f"marcar_todos_s_{data_selecionada}_{tipo_filtro}"]
                    tag_match = " ⭐ [BATE]" if tem_match else ""
                    
                    label = f"{row.get('Tipo', '🔹 OUTROS')} | R$ {v_abs:,.2f} | {desc_sistema[:35]}{tag_match}"
                    
                    # Divisão de layout: Caixa de Seleção à esquerda e Botão de Edição à direita
                    col_chk, col_edit = st.columns([0.88, 0.12])
                    with col_chk:
                        if st.checkbox(label, key=f"t_{t_id}", value=valor_padrao_chk):
                            # Preserva o item modificado para vinculação nas seleções múltiplas
                            row_modificada = row.copy()
                            row_modificada['Descrição'] = desc_sistema
                            row_modificada['Valor'] = val_sistema
                            selecionados_sistema.append(row_modificada)
                            soma_sistema_atual += val_sistema
                            
                    with col_edit:
                        with st.popover("⚙️", help="Ajustar dados deste registro do sistema"):
                            st.write("✏️ **Corrigir Informações do Lançamento**")
                            novo_desc = st.text_input("Alterar Descrição:", value=desc_sistema, key=f"desc_inp_s_{t_id}")
                            novo_val = st.number_input("Alterar Valor (R$):", value=float(val_sistema), step=1.00, format="%.2f", key=f"val_inp_s_{t_id}")
                            if st.button("Salvar Correção", key=f"btn_salvar_s_{t_id}", use_container_width=True):
                                st.session_state[chave_edicoes_sistema][t_id] = {'Descrição': novo_desc, 'Valor': novo_val}
                                st.rerun()
                
                container_calculo_sistema.markdown(f'<div class="caixa-calculo-igreja">📊 Selecionados: {len(selecionados_sistema)} itens | Soma Atual: R$ {soma_sistema_atual:,.2f}</div>', unsafe_allow_html=True)
