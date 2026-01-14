from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
from datetime import datetime

class ICMS_Scraper:
    UFs = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RN', 'RS', 
        'RJ', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    
    # Fontes de dados
    FONTES = {
        'conta_azul': 'https://contaazul.com/blog/tabela-de-aliquota-interestadual/',
        'svrs': 'https://dfe-portal.svrs.rs.gov.br/Difal/aliquotas'
    }
    
    def __init__(self, headless=True):
        """
        Inicializa o scraper
        """
        chrome_options = Options()
        
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.matriz_icms = {}
        self.aliquotas_internas = {}
        self.aliquotas_internas_fontes = {}
        self.fonte_utilizada = []
        self.erros = []

    def scrape_conta_azul(self):
        """Extrai dados da Conta Azul"""
        print('\n📊 Tentando extrair de Conta Azul...')
        
        try:
            self.driver.get(self.FONTES['conta_azul'])
            time.sleep(5)

            # Encontra a tabela principal
            tabela = self.driver.find_element(By.TAG_NAME, 'table')
            
            # Extrai todas as linhas da tabela
            all_rows = tabela.find_elements(By.TAG_NAME, 'tr')
            
            if len(all_rows) == 0:
                raise Exception("Nenhuma linha encontrada na tabela")
            
            # Primeira linha é o cabeçalho
            header_row = all_rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, 'td')
            
            # Se não houver td, tenta th
            if len(header_cells) == 0:
                header_cells = header_row.find_elements(By.TAG_NAME, 'th')
            
            # Lista de UFs no cabeçalho (pula primeira célula vazia)
            ufs_destino = [cell.text.strip() for cell in header_cells[1:]]
            print(f"  Estados de destino encontrados: {len(ufs_destino)}")
            
            # Linhas de dados (pula a primeira que é o cabeçalho)
            rows = all_rows[1:]
            
            print(f"  Linhas de dados encontradas: {len(rows)}")
            
            matriz_temp = {}
            aliquotas_internas_temp = {}
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                
                if len(cells) < 2:
                    continue
                
                # Primeira célula é o estado de origem
                uf_origem = cells[0].text.strip()
                
                if uf_origem not in self.UFs:
                    continue
                
                # Inicializa o dicionário para este estado de origem
                matriz_temp[uf_origem] = {}
                
                # Processa cada célula (alíquota para cada destino)
                for i, cell in enumerate(cells[1:], start=0):
                    if i >= len(ufs_destino):
                        break
                    
                    uf_destino = ufs_destino[i]
                    aliquota_text = cell.text.strip()
                    
                    # Tenta converter para número
                    try:
                        # Remove % e converte vírgula para ponto
                        aliquota_limpa = aliquota_text.replace('%', '').replace(',', '.').strip()
                        aliquota_num = float(aliquota_limpa)
                        
                        # Armazena alíquota interna (origem = destino)
                        if uf_origem == uf_destino:
                            aliquotas_internas_temp[uf_origem] = aliquota_num
                        
                        matriz_temp[uf_origem][uf_destino] = aliquota_num
                    except ValueError:
                        # Se não conseguir converter, mantém como texto
                        matriz_temp[uf_origem][uf_destino] = aliquota_text
                
                print(f"  ✓ {uf_origem}: {len(matriz_temp[uf_origem])} alíquotas extraídas")

            self.fonte_utilizada.append('conta_azul')
            self.aliquotas_internas_fontes['conta_azul'] = aliquotas_internas_temp
            
            return matriz_temp, aliquotas_internas_temp
        
        except Exception as e:
            erro_msg = f"Erro ao extrair de Conta Azul: {str(e)}"
            print(f"  ✗ {erro_msg}")
            self.erros.append(erro_msg)
            return None, None

    def scrape_svrs(self):
        """Extrai dados do portal SVRS"""
        print('\n📊 Tentando extrair de SVRS (Portal DIFAL)...')
        
        try:
            self.driver.get(self.FONTES['svrs'])
            time.sleep(5)

            # Tenta encontrar a tabela (pode ter estrutura diferente)
            tabelas = self.driver.find_elements(By.TAG_NAME, 'table')
            
            if len(tabelas) == 0:
                raise Exception("Nenhuma tabela encontrada")
            
            # Usa a primeira tabela encontrada
            tabela = tabelas[0]
            
            # Extrai todas as linhas
            all_rows = tabela.find_elements(By.TAG_NAME, 'tr')
            
            if len(all_rows) == 0:
                raise Exception("Nenhuma linha encontrada na tabela")
            
            # Processa de forma similar
            header_row = all_rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, 'td')
            
            if len(header_cells) == 0:
                header_cells = header_row.find_elements(By.TAG_NAME, 'th')
            
            ufs_destino = [cell.text.strip() for cell in header_cells[1:]]
            print(f"  Estados de destino encontrados: {len(ufs_destino)}")
            
            rows = all_rows[1:]
            print(f"  Linhas de dados encontradas: {len(rows)}")
            
            matriz_temp = {}
            aliquotas_internas_temp = {}
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, 'td')
                
                if len(cells) < 2:
                    continue
                
                uf_origem = cells[0].text.strip()
                
                if uf_origem not in self.UFs:
                    continue
                
                matriz_temp[uf_origem] = {}
                
                for i, cell in enumerate(cells[1:], start=0):
                    if i >= len(ufs_destino):
                        break
                    
                    uf_destino = ufs_destino[i]
                    aliquota_text = cell.text.strip()
                    
                    try:
                        aliquota_limpa = aliquota_text.replace('%', '').replace(',', '.').strip()
                        aliquota_num = float(aliquota_limpa)
                        
                        if uf_origem == uf_destino:
                            aliquotas_internas_temp[uf_origem] = aliquota_num
                        
                        matriz_temp[uf_origem][uf_destino] = aliquota_num
                    except ValueError:
                        matriz_temp[uf_origem][uf_destino] = aliquota_text
                
                print(f"  ✓ {uf_origem}: {len(matriz_temp[uf_origem])} alíquotas extraídas")

            self.fonte_utilizada.append('svrs')
            self.aliquotas_internas_fontes['svrs'] = aliquotas_internas_temp
            
            return matriz_temp, aliquotas_internas_temp
        
        except Exception as e:
            erro_msg = f"Erro ao extrair de SVRS: {str(e)}"
            print(f"  ✗ {erro_msg}")
            self.erros.append(erro_msg)
            return None, None

    def comparar_aliquotas_internas(self):
        """Compara alíquotas internas de diferentes fontes e escolhe a mais recente/correta"""
        print('\n🔍 Comparando alíquotas internas entre fontes...')
        
        if len(self.aliquotas_internas_fontes) < 2:
            print('  ⚠ Apenas uma fonte disponível, não há comparação')
            return
        
        # Prioridade: SVRS > Conta Azul (SVRS é fonte oficial)
        fonte_prioritaria = 'svrs' if 'svrs' in self.aliquotas_internas_fontes else 'conta_azul'
        
        print(f'  📌 Fonte prioritária: {fonte_prioritaria.upper()}')
        
        diferencas = []
        
        for uf in self.UFs:
            valores = {}
            for fonte, aliquotas in self.aliquotas_internas_fontes.items():
                if uf in aliquotas:
                    valores[fonte] = aliquotas[uf]
            
            if len(valores) > 1:
                valores_unicos = set(valores.values())
                if len(valores_unicos) > 1:
                    diferencas.append({
                        'uf': uf,
                        'valores': valores,
                        'escolhido': valores.get(fonte_prioritaria, list(valores.values())[0])
                    })
                    print(f'  ⚠ {uf}: Diferença encontrada - {valores}')
                    print(f'    → Usando: {valores.get(fonte_prioritaria, list(valores.values())[0])}%')
            
            # Define a alíquota interna usando a fonte prioritária
            if fonte_prioritaria in valores:
                self.aliquotas_internas[uf] = valores[fonte_prioritaria]
            elif len(valores) > 0:
                self.aliquotas_internas[uf] = list(valores.values())[0]
        
        if len(diferencas) == 0:
            print('  ✓ Todas as alíquotas coincidem entre as fontes')
        else:
            print(f'  📊 Total de diferenças encontradas: {len(diferencas)}')

    def scrape(self):
        """Tenta extrair dados de múltiplas fontes com redundância"""
        print('='*70)
        print('🚀 Iniciando scraping de alíquotas ICMS interestadual')
        print('='*70)
        
        # Tenta Conta Azul primeiro
        matriz_ca, aliq_int_ca = self.scrape_conta_azul()
        
        # Tenta SVRS como backup/complemento
        matriz_svrs, aliq_int_svrs = self.scrape_svrs()
        
        # Escolhe a melhor fonte
        if matriz_ca and len(matriz_ca) > 0:
            self.matriz_icms = matriz_ca
            print('\n✓ Usando dados da Conta Azul como base principal')
        elif matriz_svrs and len(matriz_svrs) > 0:
            self.matriz_icms = matriz_svrs
            print('\n✓ Usando dados do SVRS como base principal')
        else:
            print('\n✗ Falha ao extrair dados de todas as fontes')
            return None
        
        # Compara e consolida alíquotas internas
        self.comparar_aliquotas_internas()
        
        # Validação final
        self.validar_extracao()
        
        return self.matriz_icms

    def validar_extracao(self):
        """Valida a extração dos dados"""
        print('\n📋 Validando extração...')
        
        estados_faltantes = [uf for uf in self.UFs if uf not in self.matriz_icms]

        if estados_faltantes:
            print(f"  ⚠ Estados faltantes: {estados_faltantes}")
            self.erros.append(f"Estados faltantes: {', '.join(estados_faltantes)}")
        else:
            print("  ✓ Todos os 27 estados presentes")

        # Valida se cada estado tem alíquotas para todos os destinos
        for estado in self.matriz_icms:
            destinos = len(self.matriz_icms[estado])
            
            if destinos < 27:
                msg = f"{estado}: apenas {destinos}/27 destinos"
                print(f"  ⚠ {msg}")
                self.erros.append(msg)
            else:
                print(f"  ✓ {estado}: completo ({destinos}/27)")

    def salvar_json(self, nome_arquivo='icms_interestadual.json'):
        """Salva os dados em JSON"""
        if not self.matriz_icms:
            print("Nenhum dado para salvar.")
            return None
        
        dados_completos = {
            'matriz_interestadual': self.matriz_icms,
            'aliquotas_internas': self.aliquotas_internas,
            'aliquotas_internas_por_fonte': self.aliquotas_internas_fontes,
            'metadata': {
                'fontes_consultadas': list(self.FONTES.keys()),
                'fontes_utilizadas': self.fonte_utilizada,
                'data_extracao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_estados': len(self.matriz_icms),
                'total_aliquotas': sum(len(destinos) for destinos in self.matriz_icms.values()),
                'erros': self.erros if self.erros else []
            }
        }
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados_completos, f, ensure_ascii=False, indent=4)
        
        print(f"\n✓ Dados salvos em '{nome_arquivo}'")
        return nome_arquivo
    
    def get_dados_completos(self):
        """Retorna os dados completos como dicionário (útil para integração direta)"""
        return {
            'matriz_interestadual': self.matriz_icms,
            'aliquotas_internas': self.aliquotas_internas,
            'aliquotas_internas_por_fonte': self.aliquotas_internas_fontes,
            'metadata': {
                'fontes_consultadas': list(self.FONTES.keys()),
                'fontes_utilizadas': self.fonte_utilizada,
                'data_extracao': datetime.now().isoformat(),
                'total_estados': len(self.matriz_icms),
                'total_aliquotas': sum(len(destinos) for destinos in self.matriz_icms.values()),
                'erros': self.erros if self.erros else []
            }
        }
    
    def consultar_aliquota(self, uf_origem, uf_destino):
        """Consulta a alíquota interestadual entre dois estados"""
        if not self.matriz_icms:
            print("Nenhum dado disponível. Execute o método scrape() primeiro.")
            return None
        
        uf_origem = uf_origem.upper()
        uf_destino = uf_destino.upper()

        if uf_origem not in self.matriz_icms:
            print(f"✗ Estado de origem '{uf_origem}' não encontrado")
            return None
        
        if uf_destino not in self.matriz_icms[uf_origem]:
            print(f"✗ Estado de destino '{uf_destino}' não encontrado para origem {uf_origem}")
            return None
        
        aliquota = self.matriz_icms[uf_origem][uf_destino]
        
        return {
            'origem': uf_origem,
            'destino': uf_destino,
            'aliquota': aliquota,
            'tipo': 'interna' if uf_origem == uf_destino else 'interestadual'
        }
    
    def calcular_icms(self, uf_origem, uf_destino, valor_operacao):
        """Calcula o valor do ICMS para uma operação"""
        resultado = self.consultar_aliquota(uf_origem, uf_destino)
        
        if not resultado:
            return None
        
        aliquota = resultado['aliquota']
        
        if isinstance(aliquota, (int, float)):
            valor_icms = valor_operacao * (aliquota / 100)
            
            return {
                'origem': uf_origem,
                'destino': uf_destino,
                'valor_operacao': valor_operacao,
                'aliquota_percentual': aliquota,
                'valor_icms': round(valor_icms, 2),
                'tipo': resultado['tipo']
            }
        else:
            print(f"✗ Não foi possível calcular. Alíquota não numérica: {aliquota}")
            return None
    
    def calcular_difal(self, uf_origem, uf_destino, valor_operacao):
        """Calcula o Diferencial de Alíquota (DIFAL)"""
        if uf_origem == uf_destino:
            print("⚠ DIFAL não se aplica para operações dentro do mesmo estado")
            return None
        
        # Alíquota interestadual (origem -> destino)
        aliquota_interestadual = self.matriz_icms.get(uf_origem, {}).get(uf_destino)
        
        # Alíquota interna do estado de destino
        aliquota_interna_destino = self.aliquotas_internas.get(uf_destino)
        
        if not aliquota_interestadual or not aliquota_interna_destino:
            print("✗ Não foi possível calcular DIFAL. Dados incompletos.")
            return None
        
        # Diferencial de alíquota
        diferencial = aliquota_interna_destino - aliquota_interestadual
        valor_difal = valor_operacao * (diferencial / 100)
        
        return {
            'origem': uf_origem,
            'destino': uf_destino,
            'valor_operacao': valor_operacao,
            'aliquota_interestadual': aliquota_interestadual,
            'aliquota_interna_destino': aliquota_interna_destino,
            'diferencial_aliquota': diferencial,
            'valor_difal': round(valor_difal, 2)
        }
        
    def gerar_relatorio(self):
        """Gera relatório estatístico das alíquotas"""
        if not self.matriz_icms:
            print("Nenhum dado disponível para gerar relatório.")
            return
        
        print("\n" + "="*70)
        print("📊 RELATÓRIO DE ALÍQUOTAS ICMS INTERESTADUAL")
        print("="*70)
        
        # Informações sobre as fontes
        print(f"\n🔗 Fontes utilizadas: {', '.join(self.fonte_utilizada)}")
        
        # Alíquotas internas por estado
        print("\n🏛️  ALÍQUOTAS INTERNAS (por estado):")
        print("-" * 70)
        for uf in sorted(self.aliquotas_internas.keys()):
            print(f"  {uf}: {self.aliquotas_internas[uf]}%")
        
        # Estatísticas de alíquotas interestaduais
        todas_aliquotas_inter = []
        for origem in self.matriz_icms:
            for destino, aliquota in self.matriz_icms[origem].items():
                if origem != destino and isinstance(aliquota, (int, float)):
                    todas_aliquotas_inter.append(aliquota)
        
        if todas_aliquotas_inter:
            print("\n📈 ESTATÍSTICAS GERAIS (Operações Interestaduais):")
            print("-" * 70)
            print(f"  Total de alíquotas interestaduais: {len(todas_aliquotas_inter)}")
            print(f"  Alíquota mínima: {min(todas_aliquotas_inter)}%")
            print(f"  Alíquota máxima: {max(todas_aliquotas_inter)}%")
            print(f"  Alíquota média: {sum(todas_aliquotas_inter) / len(todas_aliquotas_inter):.2f}%")
            
            # Conta quantas vezes cada alíquota aparece
            from collections import Counter
            contador = Counter(todas_aliquotas_inter)
            print(f"\n  Distribuição de alíquotas:")
            for aliquota, qtd in sorted(contador.items()):
                print(f"    {aliquota}%: {qtd} ocorrências")
        
        # Mostra erros se houver
        if self.erros:
            print("\n⚠️  AVISOS E ERROS:")
            print("-" * 70)
            for erro in self.erros:
                print(f"  • {erro}")
        
        print("\n" + "="*70)
    
    def fechar(self):
        """Fecha o navegador"""
        try:
            self.driver.quit()
            print("🔒 Navegador fechado")
        except:
            pass
