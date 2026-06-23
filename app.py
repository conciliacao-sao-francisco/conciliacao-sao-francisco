def carregar_dados_upload(modo_conta, file_banco, file_sistema):
    if not file_banco: return None, None, {}
    dados_b, s_ant, s_finais = processar_extrato_sicoob(file_banco)
    dados_banco_finais = []
    sipag_por_dia = {}
    idx_b = 0
    
    # 1. PROCESSAMENTO DO BANCO (Mantido igual ao seu original)
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
    if file_sistema:
        if "161" in modo_conta:
            df_t_bruto = pd.read_excel(file_sistema, skiprows=7).dropna(how='all')
            
            # --- NOVA LÓGICA DE AGRUPAMENTO DE CARTÃO PARA O THEOS ---
            cartao_sistema_por_dia = {}
            
            for _, row in df_t_bruto.iterrows():
                if len(row) < 23: continue
                dt_val = row.iloc[0]
                if pd.notna(dt_val) and ('-' in str(dt_val) or '/' in str(dt_val)):
                    desc = str(row.iloc[9]).strip()
                    desc_upper = desc.upper()
                    
                    ent = float(row.iloc[16]) if pd.notna(row.iloc[16]) else 0.0
                    sai = float(row.iloc[22]) if pd.notna(row.iloc[22]) else 0.0
                    v_liq = ent - sai
                    
                    if v_liq != 0 and "SUBTOTAL" not in desc_upper:
                        dt_obj = pd.to_datetime(str(dt_val)[:10], errors='coerce')
                        if pd.notna(dt_obj):
                            data_formatada = dt_obj.strftime('%d/%m/%Y')
                            
                            # Verifica se a descrição indica que é uma transação de cartão/sipag no boletim
                            if any(x in desc_upper for x in ["CARTAO", "CARTÃO", "CREDITO", "DEBITO", "SIPAG"]):
                                # Agrupa o valor no dicionário do dia correspondente
                                cartao_sistema_por_dia[data_formatada] = cartao_sistema_por_dia.get(data_formatada, 0.0) + v_liq
                            else:
                                # Se for outro tipo de lançamento, insere normalmente
                                dados_contrapartida.append({
                                    'id_theos': f"T_{idx_t}", 'Data': data_formatada,
                                    'Tipo': "🟢 PIX RECEBIDO" if v_liq > 0 else "🔴 SAÍDA", 
                                    'Descrição': desc, 'Valor': round(v_liq, 2)
                                })
                                idx_t += 1
            
            # Após processar todas as linhas, insere os lotes diários de cartões calculados do sistema
            for dia, v_tot_sist in cartao_sistema_por_dia.items():
                dados_contrapartida.append({
                    'id_theos': f"T_{idx_t}", 'Data': dia,
                    'Tipo': "💳 SIPAG LOTE",  # Mantemos o mesmo tipo do banco para o filtro bater
                    'Descrição': "COMPENSAÇÃO CARTÃO BOLETIM (Agrupado)", 
                    'Valor': round(v_tot_sist, 2)
                })
                idx_t += 1
            # --------------------------------------------------------

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
                            'Tipo': "🟢 PIX RECEBIDO", 'Descrição': str(row['Nome']).strip(), 'Valor': round(v_ecl, 2)
                        })
                        idx_t += 1
            except: pass

    mapa_saldos = {dia: {'Anterior': s_ant if i==0 else list(s_finais.values())[i-1], 'Final': v} for i, (dia, v) in enumerate(s_finais.items())}
    return pd.DataFrame(dados_banco_finais), pd.DataFrame(dados_contrapartida), mapa_saldos
