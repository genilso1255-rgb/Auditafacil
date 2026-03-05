def processar_contas(arquivos):
    resumo = {
        "HONORARIOS": 0.0, "MEDICAMENTOS": 0.0, "MATERIAL": 0.0,
        "GASES": 0.0, "TAXAS E ALUGUEIS": 0.0, "DIARIA DE ENFERMARIA": 0.0,
        "EXAMES": 0.0, "MATERIAL ESPECIAL (OPME)": 0.0
    }
    itens_detalhados = []

    for arq in arquivos:
        img_pil = Image.open(arq)
        img = np.array(img_pil.convert('RGB'))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # MELHORIA: Aumentamos o contraste para ignorar caneta azul/vermelha
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        texto = pytesseract.image_to_string(gray, lang='por')

        for linha in texto.split('\n'):
            linha = linha.strip().upper()
            # Busca qualquer número que pareça valor financeiro (ex: 336,33 ou 1.009,02)
            valores_encontrados = re.findall(r'(\d[\d\.,]+)', linha)
            
            if valores_encontrados:
                # Pegamos o último número da linha (que na sua conta é sempre o VI Total)
                valor_str = valores_encontrados[-1]
                try:
                    val = float(valor_str.replace('.', '').replace(',', '.'))
                    
                    # Identificação por palavras-chave das suas fotos reais
                    cat = "OUTROS"
                    if any(x in linha for x in ["SALA", "TAXA", "REGISTRO", "ALUGUE"]): cat = "TAXAS E ALUGUEIS"
                    elif any(x in linha for x in ["GASES", "OXIGENIO", "AR COMP"]): cat = "GASES"
                    elif any(x in linha for x in ["MEDIC", "DIETA", "SOLUCAO", "AMP", "VUL"]): cat = "MEDICAMENTOS"
                    elif any(x in linha for x in ["MATER", "FIO", "DESCART", "SERINGA", "AGULHA", "LUV"]): cat = "MATERIAL"
                    elif any(x in linha for x in ["DIARIA", "APART", "ENFERM"]): cat = "DIARIA DE ENFERMARIA"
                    elif any(x in linha for x in ["OPME", "ORTESE", "PROTESE", "ESPECIAL", "SINTESE"]): cat = "MATERIAL ESPECIAL (OPME)"
                    elif "HONOR" in linha: cat = "HONORARIOS"
                    elif "EXAME" in linha: cat = "EXAMES"

                    if cat in resumo:
                        resumo[cat] += val
                        itens_detalhados.append({"Item": linha[:30], "Cat": cat, "Valor": val})
                except: continue
    return resumo, itens_detalhados
    
