from supabase import create_client, Client
from config import Config
from datetime import datetime
import json

class SupabaseDB:
    def __init__(self):
        Config.validate()
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        print("✅ Cliente Supabase inicializado")
    
    def inserir_aliquotas_internas(self, aliquotas_dict, fonte='conta_azul'):
        """Insere ou atualiza alíquotas internas"""
        registros_inseridos = 0
        erros = []
        
        print(f"\n📝 Inserindo {len(aliquotas_dict)} alíquotas internas...")
        
        for uf, aliquota in aliquotas_dict.items():
            try:
                print(f"  Processando {uf}: {aliquota}%")
                
                # Desativa registros antigos
                try:
                    result = self.client.table('aliquotas_internas').update({
                        'ativo': False
                    }).eq('uf', uf).eq('ativo', True).execute()
                    print(f"    ↳ Desativados registros antigos: {len(result.data) if result.data else 0}")
                except Exception as e:
                    print(f"    ⚠️ Aviso ao desativar: {e}")
                
                # Insere novo registro (SEM data_extracao)
                data = {
                    'uf': uf,
                    'aliquota': float(aliquota),
                    'fonte': fonte,
                    'ativo': True
                }
                
                result = self.client.table('aliquotas_internas').insert(data).execute()
                
                if result.data:
                    registros_inseridos += 1
                    print(f"    ✅ Inserido com sucesso")
                else:
                    print(f"    ⚠️ Nenhum dado retornado na inserção")
                
            except Exception as e:
                erro_msg = f"Erro ao inserir {uf}: {str(e)}"
                erros.append(erro_msg)
                print(f"    ❌ {erro_msg}")
        
        print(f"\n✅ Total inserido: {registros_inseridos}/{len(aliquotas_dict)}")
        return registros_inseridos, erros
    
    def inserir_aliquotas_interestaduais(self, matriz_dict, fonte='conta_azul'):
        """Insere ou atualiza alíquotas interestaduais em lote"""
        registros_inseridos = 0
        erros = []
        
        # Conta total de registros
        total_registros = sum(len(destinos) for destinos in matriz_dict.values())
        print(f"\n📝 Inserindo {total_registros} alíquotas interestaduais...")
        
        # Desativa todos os registros antigos
        try:
            result = self.client.table('aliquotas_interestaduais').update({
                'ativo': False
            }).eq('ativo', True).execute()
            print(f"  ↳ Desativados registros antigos: {len(result.data) if result.data else 0}")
        except Exception as e:
            print(f"  ⚠️ Aviso ao desativar registros: {e}")
        
        # Prepara lista de registros para inserção em lote (SEM data_extracao)
        registros = []
        for uf_origem, destinos in matriz_dict.items():
            for uf_destino, aliquota in destinos.items():
                registros.append({
                    'uf_origem': uf_origem,
                    'uf_destino': uf_destino,
                    'aliquota': float(aliquota),
                    'fonte': fonte,
                    'ativo': True
                })
        
        print(f"  📦 Preparados {len(registros)} registros para inserção")
        
        # Insere em lotes de 100 registros
        batch_size = 100
        total_batches = (len(registros) + batch_size - 1) // batch_size
        
        for i in range(0, len(registros), batch_size):
            batch = registros[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            try:
                print(f"  📤 Inserindo lote {batch_num}/{total_batches} ({len(batch)} registros)...")
                result = self.client.table('aliquotas_interestaduais').insert(batch).execute()
                
                if result.data:
                    registros_inseridos += len(batch)
                    print(f"    ✅ Lote {batch_num} inserido com sucesso")
                else:
                    print(f"    ⚠️ Lote {batch_num} não retornou dados")
                    
            except Exception as e:
                erro_msg = f"Erro no lote {batch_num}: {str(e)}"
                erros.append(erro_msg)
                print(f"    ❌ {erro_msg}")
        
        print(f"\n✅ Total inserido: {registros_inseridos}/{len(registros)}")
        return registros_inseridos, erros
    
    def importar_json(self, json_path):
        """Importa dados do JSON gerado pelo scraper"""
        print(f"\n{'='*70}")
        print(f"📥 IMPORTANDO DADOS DO JSON: {json_path}")
        print(f"{'='*70}")
        
        try:
            # Lê o arquivo JSON
            print(f"\n📖 Lendo arquivo JSON...")
            with open(json_path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            print(f"✅ Arquivo lido com sucesso")
            print(f"  - Estados com alíquotas internas: {len(dados['aliquotas_internas'])}")
            print(f"  - Estados na matriz: {len(dados['matriz_interestadual'])}")
            
            fonte = dados['metadata']['fontes_utilizadas'][0] if dados['metadata']['fontes_utilizadas'] else 'desconhecida'
            print(f"  - Fonte: {fonte}")
            
            # Insere alíquotas internas
            total_internas, erros_internas = self.inserir_aliquotas_internas(
                dados['aliquotas_internas'], 
                fonte
            )
            
            # Insere alíquotas interestaduais
            total_inter, erros_inter = self.inserir_aliquotas_interestaduais(
                dados['matriz_interestadual'],
                fonte
            )
            
            total_registros = total_internas + total_inter
            todos_erros = erros_internas + erros_inter
            
            print(f"\n{'='*70}")
            print(f"📊 RESUMO DA IMPORTAÇÃO")
            print(f"{'='*70}")
            print(f"✅ Alíquotas internas: {total_internas}")
            print(f"✅ Alíquotas interestaduais: {total_inter}")
            print(f"✅ Total de registros: {total_registros}")
            
            if todos_erros:
                print(f"\n⚠️ Erros encontrados: {len(todos_erros)}")
                for erro in todos_erros[:5]:
                    print(f"  - {erro}")
                if len(todos_erros) > 5:
                    print(f"  ... e mais {len(todos_erros) - 5} erros")
            
            print(f"{'='*70}\n")
            
            return {
                'sucesso': True,
                'total_registros': total_registros,
                'total_internas': total_internas,
                'total_interestaduais': total_inter,
                'erros': todos_erros
            }
            
        except Exception as e:
            print(f"\n❌ ERRO CRÍTICO na importação: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def consultar_aliquota(self, uf_origem, uf_destino):
        """Consulta alíquota entre dois estados"""
        try:
            response = self.client.table('aliquotas_interestaduais').select('*').eq(
                'uf_origem', uf_origem.upper()
            ).eq(
                'uf_destino', uf_destino.upper()
            ).eq(
                'ativo', True
            ).order('created_at', desc=True).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"❌ Erro ao consultar alíquota: {e}")
            return None
    
    def listar_aliquotas_internas(self):
        """Lista todas as alíquotas internas ativas"""
        try:
            response = self.client.table('aliquotas_internas').select(
                'uf, aliquota, fonte'
            ).eq('ativo', True).order('uf').execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Erro ao listar alíquotas internas: {e}")
            return []
    
    def obter_matriz_completa(self):
        """Retorna a matriz completa de alíquotas"""
        try:
            response = self.client.table('aliquotas_interestaduais').select(
                'uf_origem, uf_destino, aliquota'
            ).eq('ativo', True).execute()
            
            # Organiza em formato de matriz
            matriz = {}
            for registro in response.data:
                origem = registro['uf_origem']
                destino = registro['uf_destino']
                aliquota = registro['aliquota']
                
                if origem not in matriz:
                    matriz[origem] = {}
                
                matriz[origem][destino] = float(aliquota)
            
            return matriz
        except Exception as e:
            print(f"❌ Erro ao obter matriz completa: {e}")
            return {}

    def listar_estados(self):
        """Lista todos os estados cadastrados"""
        try:
            response = self.client.table('estados').select('uf, nome, regiao').order('uf').execute()
            return response.data
        except Exception as e:
            print(f"❌ Erro ao listar estados: {e}")
            return []

    def verificar_conexao(self):
        """Verifica se a conexão com o Supabase está funcionando"""
        try:
            response = self.client.table('estados').select('uf').limit(1).execute()
            return True, f"Conectado - {len(response.data)} registros encontrados"
        except Exception as e:
            return False, str(e)