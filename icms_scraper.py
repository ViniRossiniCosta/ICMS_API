from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time

class ICMS_Scraper:
    UFs = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RN', 'RS', 
        'RJ', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    
    def __init__(self):
        chrome_options = Options()

        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.url = "https://www.taxgroup.com.br/intelligence/tabela-icms-2026-fique-por-dentro-das-aliquotas-estaduais-atualizadas/"
        self.matriz_completa = {}

    def scrape(self):
        print('Iniciando o scraping das aliquotas de ICMS...')

        try:
            self.driver.get(self.url)
            time.sleep(5)

            # Mapeia sigla do estado para nome completo (usado nos títulos)
            estado_sigla_map = {
                'AC': 'Acre', 'AL': 'Alagoas', 'AM': 'Amazonas', 'AP': 'Amapá',
                'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
                'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul',
                'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná',
                'PE': 'Pernambuco', 'PI': 'Piauí', 'RN': 'Rio Grande do Norte',
                'RS': 'Rio Grande do Sul', 'RJ': 'Rio de Janeiro', 'RO': 'Rondônia',
                'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo',
                'SE': 'Sergipe', 'TO': 'Tocantins'
            }

            # Encontra todos os h2 com nomes de estados
            headings = self.driver.find_elements(By.TAG_NAME, 'h2')
            
            processed_states = set()
            
            for heading in headings:
                heading_text = heading.text.strip()
                
                # Procura por padrão "Tabela ICMS XXXX – Estado" ou "Tabela ICMS XXXX- Estado"
                if 'Tabela ICMS' in heading_text and ('–' in heading_text or '- ' in heading_text):
                    # Separa por hífen (com ou sem espaço)
                    if '–' in heading_text:
                        estado_nome = heading_text.split('–')[-1].strip()
                    else:
                        estado_nome = heading_text.split('- ')[-1].strip()
                    
                    # Encontra a sigla correspondente com busca de correspondência mais longa
                    estado_sigla = None
                    maior_comprimento = 0
                    
                    for sigla, nome in estado_sigla_map.items():
                        if nome.lower() in estado_nome.lower():
                            # Se a correspondência é mais longa, atualiza
                            if len(nome) > maior_comprimento:
                                estado_sigla = sigla
                                maior_comprimento = len(nome)
                    
                    if not estado_sigla:
                        print(f"⚠ Estado não identificado: {estado_nome}")
                        continue
                    
                    # Evita processar o mesmo estado duas vezes
                    if estado_sigla in processed_states:
                        continue
                    processed_states.add(estado_sigla)
                    
                    # Encontra a tabela imediatamente após este heading
                    try:
                        # Encontra a próxima tabela após o heading atual
                        tabela = heading.find_element(By.XPATH, "./following::table[1]")
                        
                        self.matriz_completa[estado_sigla] = {
                            'nome': estado_nome,
                            'aliquotas': {}
                        }
                        
                        pagina_atual = 1
                        while True:
                            try:
                                tbody = tabela.find_element(By.TAG_NAME, 'tbody')
                                rows = tbody.find_elements(By.TAG_NAME, 'tr')
                                
                                # Extrai dados da página atual
                                for row in rows:
                                    cells = row.find_elements(By.TAG_NAME, 'td')
                                    if len(cells) >= 2:
                                        aliquota_str = cells[0].text.strip()
                                        descricao = cells[-1].text.strip()
                                        
                                        # Pula linhas vazias
                                        if not aliquota_str or not descricao:
                                            continue
                                        
                                        try:
                                            aliquota_num = float(aliquota_str.replace('%', '').replace(',', '.').strip())
                                        except ValueError:
                                            aliquota_num = aliquota_str
                                        
                                        # Armazena por descrição para referência (evita duplicatas)
                                        if descricao not in self.matriz_completa[estado_sigla]['aliquotas']:
                                            self.matriz_completa[estado_sigla]['aliquotas'][descricao] = aliquota_num
                                
                                # Procura pelo botão de próxima página
                                proximo_encontrado = False
                                try:
                                    # Tenta encontrar o botão Next de múltiplas formas
                                    next_links = self.driver.find_elements(By.XPATH, 
                                        "//a[contains(text(), 'Next') or contains(text(), 'next') or " +
                                        "contains(@class, 'next') or contains(@aria-label, 'Next')]")
                                    
                                    for next_link in next_links:
                                        try:
                                            classes = next_link.get_attribute('class') or ''
                                            if 'disabled' not in classes and next_link.is_enabled():
                                                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_link)
                                                time.sleep(0.5)
                                                self.driver.execute_script("arguments[0].click();", next_link)
                                                proximo_encontrado = True
                                                time.sleep(2)
                                                pagina_atual += 1
                                                break
                                        except:
                                            continue
                                except:
                                    pass
                                
                                if not proximo_encontrado:
                                    # Tenta buscar por links numéricos de página
                                    try:
                                        all_links = self.driver.find_elements(By.XPATH, "//a")
                                        for link in all_links:
                                            try:
                                                text = link.text.strip()
                                                if text.isdigit():
                                                    num = int(text)
                                                    if num == pagina_atual + 1:
                                                        classes = link.get_attribute('class') or ''
                                                        if 'disabled' not in classes and link.is_enabled():
                                                            self.driver.execute_script("arguments[0].scrollIntoView(true);", link)
                                                            time.sleep(0.5)
                                                            self.driver.execute_script("arguments[0].click();", link)
                                                            proximo_encontrado = True
                                                            time.sleep(2)
                                                            pagina_atual += 1
                                                            break
                                            except:
                                                continue
                                    except:
                                        pass
                                
                                if not proximo_encontrado:
                                    break
                            
                            except Exception as e:
                                print(f"⚠ Erro ao processar página {pagina_atual} de {estado_sigla}: {str(e)}")
                                break
                        
                        print(f"✓ {estado_sigla} ({estado_nome}): {len(self.matriz_completa[estado_sigla]['aliquotas'])} produtos em {pagina_atual} página(s)")
                    
                    except Exception as e:
                        print(f"⚠ Erro ao processar {estado_sigla}: {str(e)}")
                        continue

            self.validar_extracao()

            return self.matriz_completa
        
        except Exception as e:
            print(f"\n✗ ERRO durante extração: {str(e)}")
            import traceback            
            traceback.print_exc()
            return None

    def validar_extracao(self):
        estados_faltantes = [uf for uf in self.UFs if uf not in self.matriz_completa]

        if estados_faltantes:
            print(f" ⚠ ATENÇÃO: Estados faltantes: {estados_faltantes}")
        else:
            print(" ✓ Extração validada com sucesso. Todos os estados presentes.")

        for estado in self.matriz_completa:
            destinos = len(self.matriz_completa[estado])
            
            if destinos < 27:
                print(f"   ⚠ {estado}: apenas {destinos}/27 destinos")

    def salvar_json(self, nome_arquivo='icms_aliquotas.json'):
        if not self.matriz_completa:
            print("Nenhum dado para salvar.")
            return
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(self.matriz_completa, f, ensure_ascii=False, indent=4)
            
        return nome_arquivo
    
    def consultar_aliquota(self, estado, produto):
        if not self.matriz_completa:
            print("Nenhum dado disponível. Execute o método scrape() primeiro.")
            return None
        
        estado = estado.upper()
        produto = produto.lower()

        if estado not in self.matriz_completa:
            print(f"✗ Estado '{estado}' não encontrado")
            return None
        
        estado_data = self.matriz_completa[estado]
        
        # Busca por produto exato ou parcial
        for descricao, aliquota in estado_data['aliquotas'].items():
            if produto in descricao.lower():
                return {
                    'estado': estado,
                    'nome_estado': estado_data['nome'],
                    'produto': descricao,
                    'aliquota': aliquota
                }
        
        print(f"✗ Produto '{produto}' não encontrado para {estado}")
        return None
        
    def gerar_relatorio(self):
        if not self.matriz_completa:
            print("Nenhum dado disponível para gerar relatório.")
            return
        
        print("\n📊 Relatório de Alíquotas de ICMS por Estado:")
        print("=" * 60)

        todas_aliquotas = []
        
        for estado in sorted(self.matriz_completa.keys()):
            estado_data = self.matriz_completa[estado]
            aliquotas = [v for v in estado_data['aliquotas'].values() if isinstance(v, (int, float))]
            
            if aliquotas:
                media = sum(aliquotas) / len(aliquotas)
                minimo = min(aliquotas)
                maximo = max(aliquotas)
                
                print(f"\n{estado} ({estado_data['nome']}):")
                print(f"  Produtos cadastrados: {len(aliquotas)}")
                print(f"  Média das alíquotas: {media:.2f}%")
                print(f"  Alíquota mínima: {minimo:.2f}%")
                print(f"  Alíquota máxima: {maximo:.2f}%")
                
                todas_aliquotas.extend(aliquotas)
        
        if todas_aliquotas:
            print("\n" + "=" * 60)
            print("📈 RESUMO GERAL:")
            print(f"  Total de alíquotas: {len(todas_aliquotas)}")
            print(f"  Média nacional: {sum(todas_aliquotas) / len(todas_aliquotas):.2f}%")
            print(f"  Alíquota mínima: {min(todas_aliquotas):.2f}%")
            print(f"  Alíquota máxima: {max(todas_aliquotas):.2f}%")
    
    def fechar(self):
        self.driver.quit()