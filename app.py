import cv2
import pytesseract
import re
import numpy as np

class ProcessadorHospitalar:
    def __init__(self):
        # Configurações de login e ADM (Simulado para a estrutura do site)
        self.admin_config = {"login_tipo": "CPF", "senha_len": 6}

    def alinhar_e_limpar(self, imagem_path):
        """Corrige inclinação e remove ruídos (carimbos/canetas leves)"""
        img = cv2.imread(imagem_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Threshold adaptativo para separar o texto de manchas/carimbos
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # Rotação automática (Alinhamento)
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45: angle = -(90 + angle)
        else: angle = -angle
        
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        img_rotacionada = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return img_rotacionada

    def extrair_dados(self, texto_ocr):
        """Busca TUSS -> Nome -> Valor com Regex avançado"""
        itens_processados = []
        
        # Regex para capturar: [Código] [Descrição] [Valor]
        # Captura valores como 1.000,00 ou 10,50
        padrao_linha = re.compile(r'(\d{8,10})?.*?\s+([A-Za-z\s]+)\s+R?\$?\s*([\d\.,]+)')
        
        lines = texto_ocr.split('\n')
        for line in lines:
            match = padrao_linha.search(line)
            if match:
                codigo, nome, valor_str = match.groups()
                
                # Tratamento de valor financeiro
                valor_limpo = valor_str.replace('.', '').replace(',', '.')
                valor = float(valor_limpo)
                
                categoria = self.categorizar_item(nome.upper(), codigo)
                itens_processados.append({
                    "item": nome.strip(),
                    "valor": valor,
                    "categoria": categoria
                })
        return itens_processados

    def categorizar_item(self, nome, codigo):
        """Regras específicas de agrupamento que você definiu"""
        if "DIETA" in nome:
            return "MEDICAMENTO"
        if "FIO CIRURGICO" in nome or "FIO" in nome:
            return "MATERIAL DESCARTAVEL"
        if any(x in nome for x in ["ORTESE", "PROTESE", "ESPECIAL", "OPME"]):
            return "MATERIAL ESPECIAL"
        return "OUTROS"

    def gerar_tabela_final(self, lista_itens):
        """Soma os valores conforme sua regra de negócio"""
        resumo = {
            "MEDICAMENTO": 0.0,
            "MATERIAL DESCARTAVEL": 0.0,
            "MATERIAL ESPECIAL": 0.0
        }
        
        for item in lista_itens:
            cat = item['categoria']
            if cat in resumo:
                resumo[cat] += item['valor']
        
        return resumo

# --- Exemplo de Uso ---
# proc = ProcessadorHospitalar()
# img_limpa = proc.alinhar_e_limpar('conta_hospitalar.jpg')
# texto = pytesseract.image_to_string(img_limpa)
# resultado = proc.extrair_dados(texto)
# tabela = proc.gerar_tabela_final(resultado)
# print(tabela)
