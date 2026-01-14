from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from database import SupabaseDB
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Inicializa banco
db = SupabaseDB()

@app.route("/")
def index():
    return jsonify({
        "nome": "API de Alíquotas ICMS",
        "versao": "1.0",
        "descricao": "API para consulta e cálculo de alíquotas ICMS interestaduais",
        "endpoints": {
            "/": "GET - Informações da API",
            "/aliquota": "GET - Consulta alíquota (params: origem, destino)",
            "/calcular-icms": "POST - Calcula valor do ICMS",
            "/calcular-difal": "POST - Calcula DIFAL",
            "/aliquotas-internas": "GET - Lista todas alíquotas internas",
            "/matriz-completa": "GET - Retorna matriz completa",
            "/atualizar": "POST - Executa scraping e atualiza dados",
            "/importar-json": "POST - Importa dados de um JSON",
            "/historico": "GET - Histórico de atualizações"
        }
    })

@app.route("/aliquota", methods=['GET'])
def consultar_aliquota():
    """Consulta alíquota entre dois estados"""
    origem = request.args.get('origem', '').upper()
    destino = request.args.get('destino', '').upper()
    
    if not origem or not destino:
        return jsonify({
            "erro": "Parâmetros 'origem' e 'destino' são obrigatórios"
        }), 400
    
    resultado = db.consultar_aliquota(origem, destino)
    
    if not resultado:
        return jsonify({
            "erro": f"Alíquota não encontrada para {origem} -> {destino}"
        }), 404
    
    return jsonify({
        "origem": resultado['uf_origem'],
        "destino": resultado['uf_destino'],
        "aliquota": float(resultado['aliquota']),
        "fonte": resultado['fonte'],
        "data_extracao": resultado['data_extracao'],
        "tipo": "interna" if origem == destino else "interestadual"
    })

@app.route("/calcular-icms", methods=['POST'])
def calcular_icms():
    """Calcula valor do ICMS"""
    dados = request.get_json()
    
    origem = dados.get('origem', '').upper()
    destino = dados.get('destino', '').upper()
    valor = dados.get('valor_operacao')
    
    if not all([origem, destino, valor]):
        return jsonify({
            "erro": "Campos obrigatórios: origem, destino, valor_operacao"
        }), 400
    
    try:
        valor = float(valor)
    except ValueError:
        return jsonify({"erro": "valor_operacao deve ser um número"}), 400
    
    resultado = db.consultar_aliquota(origem, destino)
    
    if not resultado:
        return jsonify({
            "erro": f"Alíquota não encontrada para {origem} -> {destino}"
        }), 404
    
    aliquota = float(resultado['aliquota'])
    valor_icms = valor * (aliquota / 100)
    
    return jsonify({
        "origem": origem,
        "destino": destino,
        "valor_operacao": valor,
        "aliquota_percentual": aliquota,
        "valor_icms": round(valor_icms, 2),
        "tipo": "interna" if origem == destino else "interestadual"
    })

@app.route("/calcular-difal", methods=['POST'])
def calcular_difal():
    """Calcula Diferencial de Alíquota"""
    dados = request.get_json()
    
    origem = dados.get('origem', '').upper()
    destino = dados.get('destino', '').upper()
    valor = dados.get('valor_operacao')
    
    if origem == destino:
        return jsonify({
            "erro": "DIFAL não se aplica para operações dentro do mesmo estado"
        }), 400
    
    try:
        valor = float(valor)
    except ValueError:
        return jsonify({"erro": "valor_operacao deve ser um número"}), 400
    
    # Busca alíquota interestadual
    aliq_inter = db.consultar_aliquota(origem, destino)
    
    if not aliq_inter:
        return jsonify({
            "erro": "Alíquota interestadual não encontrada"
        }), 404
    
    # Busca alíquota interna do destino
    aliq_interna = db.consultar_aliquota(destino, destino)
    
    if not aliq_interna:
        return jsonify({
            "erro": "Alíquota interna do destino não encontrada"
        }), 404
    
    aliquota_inter = float(aliq_inter['aliquota'])
    aliquota_interna = float(aliq_interna['aliquota'])
    
    diferencial = aliquota_interna - aliquota_inter
    valor_difal = valor * (diferencial / 100)
    
    return jsonify({
        "origem": origem,
        "destino": destino,
        "valor_operacao": valor,
        "aliquota_interestadual": aliquota_inter,
        "aliquota_interna_destino": aliquota_interna,
        "diferencial_aliquota": round(diferencial, 2),
        "valor_difal": round(valor_difal, 2)
    })

@app.route("/aliquotas-internas", methods=['GET'])
def listar_aliquotas_internas():
    """Lista todas as alíquotas internas"""
    aliquotas = db.listar_aliquotas_internas()
    
    # Formata para dict simples {UF: aliquota}
    resultado = {item['uf']: float(item['aliquota']) for item in aliquotas}
    
    return jsonify(resultado)

@app.route("/matriz-completa", methods=['GET'])
def matriz_completa():
    """Retorna matriz completa de alíquotas"""
    matriz = db.obter_matriz_completa()
    
    return jsonify({
        "matriz_interestadual": matriz,
        "total_estados": len(matriz)
    })

@app.route("/atualizar", methods=['POST'])
def atualizar_dados():
    """Força atualização dos dados via scraping"""
    try:
        from icms_scraper import ICMS_Scraper
        
        print("🚀 Iniciando scraping...")
        scraper = ICMS_Scraper()
        scraper.scrape()
        
        # Salva temporariamente em JSON
        json_file = 'temp_icms.json'
        scraper.salvar_json(json_file)
        scraper.fechar()
        
        # Importa para o Supabase
        print("📤 Importando para Supabase...")
        resultado = db.importar_json(json_file)
        
        # Remove arquivo temporário
        if os.path.exists(json_file):
            os.remove(json_file)
        
        if resultado['sucesso']:
            return jsonify({
                "mensagem": "Dados atualizados com sucesso",
                "total_registros": resultado['total_registros'],
                "total_internas": resultado['total_internas'],
                "total_interestaduais": resultado['total_interestaduais'],
                "data_atualizacao": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "erro": "Falha ao atualizar dados",
                "detalhes": resultado.get('erro')
            }), 500
            
    except Exception as e:
        return jsonify({
            "erro": f"Falha ao atualizar: {str(e)}"
        }), 500

@app.route("/importar-json", methods=['POST'])
def importar_json():
    """Importa dados de um arquivo JSON"""
    dados = request.get_json()
    json_path = dados.get('json_path', 'icms_interestadual.json')
    
    if not os.path.exists(json_path):
        return jsonify({
            "erro": f"Arquivo não encontrado: {json_path}"
        }), 404
    
    resultado = db.importar_json(json_path)
    
    if resultado['sucesso']:
        return jsonify({
            "mensagem": "Dados importados com sucesso",
            "total_registros": resultado['total_registros'],
            "total_internas": resultado['total_internas'],
            "total_interestaduais": resultado['total_interestaduais']
        })
    else:
        return jsonify({
            "erro": "Falha ao importar dados",
            "detalhes": resultado.get('erro')
        }), 500

@app.route("/historico", methods=['GET'])
def historico():
    """Retorna histórico de atualizações"""
    limit = request.args.get('limit', 10, type=int)
    
    historico_list = db.obter_historico(limit)
    
    return jsonify({
        "historico": historico_list,
        "total": len(historico_list)
    })

@app.route("/health", methods=['GET'])
def health():
    """Endpoint de health check"""
    try:
        # Testa conexão com Supabase
        db.client.table('estados').select('uf').limit(1).execute()
        
        return jsonify({
            "status": "ok",
            "database": "conectado",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "erro",
            "database": "desconectado",
            "erro": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    try:
        Config.validate()
        print(f"✅ Configurações validadas")
        print(f"🚀 Iniciando API na porta {Config.FLASK_PORT}")
        app.run(host='127.0.0.1', port=Config.FLASK_PORT, debug=True)
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")