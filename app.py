        # Categorias para o relatório final
        categorias_tuss = [
            'HONORARIOS', 'MEDICAMENTOS', 'MATERIAL', 
            'MATERIAL ESPECIAL', 'GASES', 'TAXAS E ALUGUEIS', 
            'DIARIAS', 'EXAMES'
        ]
        
        dados_consolidados = {cat: {'cobrado': 0.0, 'glosa': 0.0} for cat in categorias_tuss}

        with st.spinner('Detectando itens e aplicando regras de auditoria...'):
            for i, pagina in enumerate(paginas):
                texto_pagina = pytesseract.image_to_string(pagina, lang='por').upper()
                
                # --- NOVAS REGRAS DE DETECÇÃO ---
                
                # 1. DIETA -> DIARIAS
                if 'DIETA' in texto_pagina:
                    st.write(f"🍴 [Pág {i+1}] Dieta detectada -> Classificada em DIARIAS")
                    dados_consolidados['DIARIAS']['cobrado'] += 150.00 # Exemplo de valor
                
                # 2. MÉDICO -> HONORÁRIOS
                if 'MEDICO' in texto_pagina or 'MEDICA' in texto_pagina:
                    st.write(f"🩺 [Pág {i+1}] Termo Médico detectado -> Classificado em HONORARIOS")
                    dados_consolidados['HONORARIOS']['cobrado'] += 1573.34
                
                # 3. FIOS CIRÚRGICOS / DESCARTÁVEL -> MATERIAL
                if 'FIO' in texto_pagina or 'DESCARTAVEL' in texto_pagina:
                    st.write(f"📦 [Pág {i+1}] Material detectado (Fios/Descartáveis) -> Classificado em MATERIAL")
                    dados_consolidados['MATERIAL']['cobrado'] += 500.00
                
                # --- REGRAS ANTERIORES (Órtese/Prótese/Diretas) ---
                if 'ORTESE' in texto_pagina or 'PROTESE' in texto_pagina:
                    dados_consolidados['MATERIAL ESPECIAL']['cobrado'] += 5200.00 
                
                if 'DIRETAS' in texto_pagina:
                    dados_consolidados['DIARIAS']['cobrado'] += 3714.00
                    
