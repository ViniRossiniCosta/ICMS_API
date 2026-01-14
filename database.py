from supabase import create_client, Client
from config import Config
from datetime import datetime
import json

class SupabaseDB:
    def __init__(self):
        Config.validate()
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    def inserir_aliquotas_internas(self, aliquotas_dict, fonte='conta_azul'):
        """Insere ou atualiza alíquotas internas"""
        registros_inseridos = 0
        erros = []
        
        for uf, aliquota in aliquotas_dict.items():
            try:
                # Desativa registros antigos
                self.client.table('aliquotas_internas').update({
                    'ativo': False
                }).eq('uf', uf).eq('ativo', True).execute()
                
                # Insere novo registro
                data = {
                    'uf': uf,
                    'aliquota': float(aliquota),
                    'fonte': fonte,
                    'data_extracao': datetime.now().isoformat(),
                    'ativo': True
                }
                
                self.client.table('aliquotas_internas').insert(data).execute()
                registros_inseridos += 1
                
            except Exception as e:
                erros.append(f"Erro ao inserir {uf}: {str(e)}")
        
        return registros_inseridos, erros
    
    def inserir_aliquotas_interestaduais(self, matriz_dict, fonte='conta_azul'):
        """Insere ou atualiza alíquotas interestaduais em lote"""
        registros_inseridos = 0
        erros = []
        
        # Desativa todos os registros antigos
        try:
            self.client.table('aliquotas_interestaduais').update({
                'ativo': False
            }).eq('ativo', True).execute()
        except Exception as e:
            print(f"Aviso ao desativar registros: {e}")
        
        # Prepara lista de registros para inserção em lote
        registros = []
        for uf_origem, destinos in matriz_dict.items():
            for uf_destino, aliquota in destinos.items():
                registros.append({
                    'uf_origem': uf_origem,
                    'uf_destino': uf_destino,
                    'aliquota': float(aliquota),
                    'fonte': fonte,
                    'data_extracao': datetime.now().isoformat(),
                    'ativo': True
                })
        
        # Insere em lotes de 100 registros
        batch_size = 100
        for i in range(0, len(registros), batch_size):
            batch = registros[i:i + batch_size]
            try:
                self.client.table('aliquotas_interestaduais').insert(batch).execute()
                registros_inseridos += len(batch)
            except Exception as e:
                erros.append(f"Erro no lote {i//batch_size + 1}: {str(e)}")
        
        return registros_inseridos, erros
    
    def registrar_historico(self, fonte, status, total_registros, mensagem=''):
        """Registra histórico de atualização"""
        try:
            data = {
                'fonte': fonte,
                'status': status,
                'total_registros_inseridos': total_registros,
                'mensagem': mensagem,
                'data_extracao': datetime.now().isoformat()
            }
            
            self.client.table('historico_atualizacoes').insert(data).execute()
            return True
        except Exception as e:
            print(f"Erro ao registrar histórico: {e}")
            return False
    
    def importar_json(self, json_path):
        """Importa dados do JSON gerado pelo scraper"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            fonte = dados['metadata']['fontes_utilizadas'][0] if dados['metadata']['fontes_utilizadas'] else 'desconhecida'
            
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
            
            status = 'sucesso' if len(todos_erros) == 0 else 'parcial'
            mensagem = f"Importados {total_internas} alíquotas internas e {total_inter} interestaduais"
            
            if todos_erros:
                mensagem += f". Erros: {'; '.join(todos_erros[:5])}"
            
            self.registrar_historico(fonte, status, total_registros, mensagem)
            
            return {
                'sucesso': True,
                'total_registros': total_registros,
                'total_internas': total_internas,
                'total_interestaduais': total_inter,
                'erros': todos_erros
            }
            
        except Exception as e:
            self.registrar_historico('importacao_json', 'erro', 0, str(e))
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
            print(f"Erro ao consultar alíquota: {e}")
            return None
    
    def listar_aliquotas_internas(self):
        """Lista todas as alíquotas internas ativas"""
        try:
            response = self.client.table('aliquotas_internas').select(
                'uf, aliquota, fonte, data_extracao'
            ).eq('ativo', True).order('uf').execute()
            
            return response.data
        except Exception as e:
            print(f"Erro ao listar alíquotas internas: {e}")
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
            print(f"Erro ao obter matriz completa: {e}")
            return {}
    
    def obter_historico(self, limit=10):
        """Retorna histórico de atualizações"""
        try:
            response = self.client.table('historico_atualizacoes').select('*').order(
                'created_at', desc=True
            ).limit(limit).execute()
            
            return response.data
        except Exception as e:
            print(f"Erro ao obter histórico: {e}")
            return []