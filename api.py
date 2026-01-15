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

# ============================================
# ROTAS DE INFORMAÇÃO E STATUS
# ============================================

@app.route("/")
def index():
    """Informações gerais da API"""
    return jsonify({
        "nome": "API de Alíquotas ICMS",
        "versao": "2.0",
        "descricao": "API para consulta e cálculo de alíquotas ICMS interestaduais",
        "documentacao": {
            "informacao": {
                "/": "GET - Informações da API",
                "/health": "GET - Status da API e conexão com banco",
                "/api/info": "GET - Metadados e estatísticas da base de dados"
            },
            "consultas": {
                "/api/estados": "GET - Lista todos os estados",
                "/api/estados/{uf}": "GET - Informações de um estado específico",
                "/api/aliquotas/interna/{uf}": "GET - Alíquota interna de um estado",
                "/api/aliquotas/internas": "GET - Todas as alíquotas internas",
                "/api/aliquotas/interestadual": "GET - Alíquota entre dois estados (params: origem, destino)",
                "/api/aliquotas/matriz": "GET - Matriz completa de alíquotas"
            },
            "calculos": {
                "/api/calcular/icms": "POST - Calcula valor do ICMS",
                "/api/calcular/difal": "POST - Calcula DIFAL (Diferencial de Alíquota)"
            },
            "admin": {
                "/api/admin/atualizar": "POST - Executa scraping e atualiza dados (requer autenticação futura)"
            }
        }
    })

@app.route("/health", methods=['GET'])
def health():
    """Health check da API"""
    try:
        conectado, mensagem = db.verificar_conexao()
        
        if conectado:
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "message": mensagem,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "database": "disconnected",
                "error": mensagem,
                "timestamp": datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route("/api/info", methods=['GET'])
def api_info():
    """Metadados e estatísticas da base de dados"""
    try:
        estados = db.listar_estados()
        aliquotas_internas = db.listar_aliquotas_internas()
        matriz = db.obter_matriz_completa()
        
        total_interestaduais = sum(len(destinos) for destinos in matriz.values())
        
        return jsonify({
            "estatisticas": {
                "total_estados": len(estados),
                "total_aliquotas_internas": len(aliquotas_internas),
                "total_aliquotas_interestaduais": total_interestaduais
            },
            "ultima_atualizacao": datetime.now().isoformat(),
            "fonte": "conta_azul"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ROTAS DE ESTADOS
# ============================================

@app.route("/api/estados", methods=['GET'])
def listar_estados():
    """Lista todos os estados brasileiros"""
    try:
        estados = db.listar_estados()
        
        return jsonify({
            "data": estados,
            "total": len(estados),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/estados/<string:uf>", methods=['GET'])
def obter_estado(uf):
    """Obtém informações de um estado específico"""
    try:
        uf = uf.upper()
        estados = db.listar_estados()
        estado = next((e for e in estados if e['uf'] == uf), None)
        
        if not estado:
            return jsonify({
                "error": f"Estado '{uf}' não encontrado",
                "valid_ufs": [e['uf'] for e in estados]
            }), 404
        
        # Busca alíquota interna
        aliquota_interna = db.consultar_aliquota(uf, uf)
        
        return jsonify({
            "data": {
                "uf": estado['uf'],
                "nome": estado['nome'],
                "regiao": estado['regiao'],
                "aliquota_interna": float(aliquota_interna['aliquota']) if aliquota_interna else None
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ROTAS DE ALÍQUOTAS
# ============================================

@app.route("/api/aliquotas/interna/<string:uf>", methods=['GET'])
def obter_aliquota_interna(uf):
    """Obtém a alíquota interna de um estado específico"""
    try:
        uf = uf.upper()
        resultado = db.consultar_aliquota(uf, uf)
        
        if not resultado:
            return jsonify({
                "error": f"Alíquota interna não encontrada para o estado '{uf}'"
            }), 404
        
        return jsonify({
            "data": {
                "uf": resultado['uf_origem'],
                "aliquota": float(resultado['aliquota']),
                "fonte": resultado['fonte'],
                "tipo": "interna"
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/aliquotas/internas", methods=['GET'])
def listar_aliquotas_internas():
    """Lista todas as alíquotas internas"""
    try:
        aliquotas = db.listar_aliquotas_internas()
        
        # Formato detalhado
        if request.args.get('format') == 'detailed':
            return jsonify({
                "data": [
                    {
                        "uf": item['uf'],
                        "aliquota": float(item['aliquota']),
                        "fonte": item['fonte']
                    }
                    for item in aliquotas
                ],
                "total": len(aliquotas),
                "timestamp": datetime.now().isoformat()
            })
        
        # Formato simples (padrão): {UF: aliquota}
        resultado = {item['uf']: float(item['aliquota']) for item in aliquotas}
        
        return jsonify({
            "data": resultado,
            "total": len(resultado),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/aliquotas/interestadual", methods=['GET'])
def consultar_aliquota_interestadual():
    """Consulta alíquota interestadual entre dois estados"""
    origem = request.args.get('origem', '').upper()
    destino = request.args.get('destino', '').upper()
    
    if not origem or not destino:
        return jsonify({
            "error": "Parâmetros 'origem' e 'destino' são obrigatórios",
            "example": "/api/aliquotas/interestadual?origem=SP&destino=RJ"
        }), 400
    
    try:
        resultado = db.consultar_aliquota(origem, destino)
        
        if not resultado:
            return jsonify({
                "error": f"Alíquota não encontrada para a operação {origem} → {destino}"
            }), 404
        
        return jsonify({
            "data": {
                "origem": resultado['uf_origem'],
                "destino": resultado['uf_destino'],
                "aliquota": float(resultado['aliquota']),
                "fonte": resultado['fonte'],
                "tipo": "interna" if origem == destino else "interestadual"
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/aliquotas/matriz", methods=['GET'])
def obter_matriz_completa():
    """Retorna a matriz completa de alíquotas interestaduais"""
    try:
        matriz = db.obter_matriz_completa()
        
        # Opção de retornar em formato de lista para facilitar processamento
        if request.args.get('format') == 'list':
            lista = []
            for origem, destinos in matriz.items():
                for destino, aliquota in destinos.items():
                    lista.append({
                        "origem": origem,
                        "destino": destino,
                        "aliquota": aliquota
                    })
            
            return jsonify({
                "data": lista,
                "total": len(lista),
                "timestamp": datetime.now().isoformat()
            })
        
        # Formato padrão: matriz aninhada
        return jsonify({
            "data": matriz,
            "total_estados": len(matriz),
            "total_combinacoes": sum(len(destinos) for destinos in matriz.values()),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ROTAS DE CÁLCULOS
# ============================================

@app.route("/api/calcular/icms", methods=['POST'])
def calcular_icms():
    """
    Calcula o valor do ICMS
    
    Body (JSON):
    {
        "origem": "SP",
        "destino": "RJ",
        "valor_operacao": 1000.00
    }
    """
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                "error": "Body JSON é obrigatório",
                "example": {
                    "origem": "SP",
                    "destino": "RJ",
                    "valor_operacao": 1000.00
                }
            }), 400
        
        origem = dados.get('origem', '').upper()
        destino = dados.get('destino', '').upper()
        valor = dados.get('valor_operacao')
        
        if not all([origem, destino, valor]):
            return jsonify({
                "error": "Campos obrigatórios: origem, destino, valor_operacao"
            }), 400
        
        try:
            valor = float(valor)
        except (ValueError, TypeError):
            return jsonify({"error": "valor_operacao deve ser um número"}), 400
        
        if valor <= 0:
            return jsonify({"error": "valor_operacao deve ser maior que zero"}), 400
        
        resultado = db.consultar_aliquota(origem, destino)
        
        if not resultado:
            return jsonify({
                "error": f"Alíquota não encontrada para {origem} → {destino}"
            }), 404
        
        aliquota = float(resultado['aliquota'])
        valor_icms = valor * (aliquota / 100)
        
        return jsonify({
            "data": {
                "origem": origem,
                "destino": destino,
                "valor_operacao": valor,
                "aliquota_percentual": aliquota,
                "valor_icms": round(valor_icms, 2),
                "valor_com_icms": round(valor + valor_icms, 2),
                "tipo": "interna" if origem == destino else "interestadual"
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/calcular/difal", methods=['POST'])
def calcular_difal():
    """
    Calcula o Diferencial de Alíquota (DIFAL)
    
    Body (JSON):
    {
        "origem": "SP",
        "destino": "RJ",
        "valor_operacao": 1000.00
    }
    """
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                "error": "Body JSON é obrigatório",
                "example": {
                    "origem": "SP",
                    "destino": "RJ",
                    "valor_operacao": 1000.00
                }
            }), 400
        
        origem = dados.get('origem', '').upper()
        destino = dados.get('destino', '').upper()
        valor = dados.get('valor_operacao')
        
        if origem == destino:
            return jsonify({
                "error": "DIFAL não se aplica para operações dentro do mesmo estado"
            }), 400
        
        try:
            valor = float(valor)
        except (ValueError, TypeError):
            return jsonify({"error": "valor_operacao deve ser um número"}), 400
        
        if valor <= 0:
            return jsonify({"error": "valor_operacao deve ser maior que zero"}), 400
        
        # Busca alíquota interestadual
        aliq_inter = db.consultar_aliquota(origem, destino)
        
        if not aliq_inter:
            return jsonify({
                "error": "Alíquota interestadual não encontrada"
            }), 404
        
        # Busca alíquota interna do destino
        aliq_interna = db.consultar_aliquota(destino, destino)
        
        if not aliq_interna:
            return jsonify({
                "error": "Alíquota interna do destino não encontrada"
            }), 404
        
        aliquota_inter = float(aliq_inter['aliquota'])
        aliquota_interna = float(aliq_interna['aliquota'])
        
        diferencial = aliquota_interna - aliquota_inter
        valor_difal = valor * (diferencial / 100)
        
        return jsonify({
            "data": {
                "origem": origem,
                "destino": destino,
                "valor_operacao": valor,
                "aliquota_interestadual": aliquota_inter,
                "aliquota_interna_destino": aliquota_interna,
                "diferencial_aliquota": round(diferencial, 2),
                "valor_difal": round(valor_difal, 2),
                "valor_icms_origem": round(valor * (aliquota_inter / 100), 2),
                "valor_icms_total": round(valor * (aliquota_interna / 100), 2)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ROTAS ADMINISTRATIVAS
# ============================================

@app.route("/api/admin/atualizar", methods=['POST'])
def atualizar_dados():
    """
    Força atualização dos dados via scraping
    
    ATENÇÃO: Esta operação pode demorar alguns minutos
    """
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
                "status": "success",
                "message": "Dados atualizados com sucesso",
                "data": {
                    "total_registros": resultado['total_registros'],
                    "total_internas": resultado['total_internas'],
                    "total_interestaduais": resultado['total_interestaduais']
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Falha ao atualizar dados",
                "error": resultado.get('erro'),
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Falha ao atualizar: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

# ============================================
# TRATAMENTO DE ERROS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas"""
    return jsonify({
        "error": "Rota não encontrada",
        "message": "Consulte a documentação em GET /",
        "timestamp": datetime.now().isoformat()
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handler para métodos HTTP não permitidos"""
    return jsonify({
        "error": "Método HTTP não permitido",
        "message": "Verifique o método correto na documentação",
        "timestamp": datetime.now().isoformat()
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos"""
    return jsonify({
        "error": "Erro interno do servidor",
        "message": "Entre em contato com o suporte",
        "timestamp": datetime.now().isoformat()
    }), 500

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == '__main__':
    try:
        Config.validate()
        print(f"✅ Configurações validadas")
        print(f"🚀 Iniciando API na porta {Config.FLASK_PORT}")
        print(f"📚 Documentação disponível em: http://127.0.0.1:{Config.FLASK_PORT}/")
        app.run(host='127.0.0.1', port=Config.FLASK_PORT, debug=True)
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")