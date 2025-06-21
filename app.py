# app.py - Backend Python para Controle de Grãos

# Importa os módulos necessários
from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
from flask_cors import CORS # Necessário para permitir requisições do frontend (HTML)

# Inicializa a aplicação Flask
app = Flask(__name__)
# Habilita CORS para permitir que seu frontend HTML (rodando em um domínio diferente, como o Canvas)
# possa fazer requisições para este backend. Em um ambiente de produção, configure isso de forma mais restritiva.
CORS(app)

# Define o nome do arquivo do banco de dados SQLite
DATABASE = 'grain_control.db'

# --- Funções para Interagir com o Banco de Dados ---

def get_db_connection():
    """
    Estabelece uma conexão com o banco de dados SQLite.
    Configura row_factory para que as linhas retornadas se comportem como dicionários,
    permitindo acessar as colunas por nome.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Inicializa o banco de dados, criando a tabela 'movimentacoes' se ela ainda não existir.
    A tabela 'movimentacoes' terá:
    - id: Chave primária, auto-incrementável
    - tipo: 'entrada' ou 'saida'
    - data: Data da movimentação (formato TEXT, ex: 'YYYY-MM-DD')
    - produto: Nome do produto
    - quantidade: Quantidade em Kg
    - destino: Destino (para saídas), pode ser nulo
    - timestamp: Data e hora da criação/atualização do registro (para ordenação)
    """
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            data TEXT NOT NULL,
            produto TEXT NOT NULL,
            quantidade REAL NOT NULL,
            destino TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit() # Salva as alterações (criação da tabela) no banco de dados
    conn.close() # Fecha a conexão com o banco de dados

# --- Rotas da API (Endpoints) ---

@app.route('/api/movimentacoes', methods=['GET'])
def get_movimentacoes():
    """
    Endpoint para buscar todas as movimentações.
    Permite filtragem por data de início e fim.
    """
    conn = get_db_connection()
    query_str = 'SELECT * FROM movimentacoes WHERE 1=1'
    params = []

    data_inicio = request.args.get('dataInicio')
    data_fim = request.args.get('dataFim')

    if data_inicio:
        query_str += ' AND data >= ?'
        params.append(data_inicio)
    if data_fim:
        query_str += ' AND data <= ?'
        params.append(data_fim)

    # Ordena as movimentações pelo timestamp de forma descendente (mais recentes primeiro)
    query_str += ' ORDER BY timestamp DESC'

    movimentacoes_db = conn.execute(query_str, params).fetchall()
    conn.close()

    # Converte as linhas do banco de dados para uma lista de dicionários
    # Cada Row object se comporta como um dicionário, então list comprehension já funciona
    movimentacoes_list = [dict(row) for row in movimentacoes_db]
    return jsonify(movimentacoes_list)

@app.route('/api/movimentacoes', methods=['POST'])
def add_movimentacao():
    """
    Endpoint para adicionar uma nova movimentação.
    Recebe os dados via JSON no corpo da requisição.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    tipo = data.get('tipo')
    data_movimentacao = data.get('data')
    produto = data.get('produto')
    quantidade = data.get('quantidade')
    destino = data.get('destino', None) # Destino pode ser opcional

    if not all([tipo, data_movimentacao, produto, quantidade is not None]):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    if not isinstance(quantidade, (int, float)) or quantidade <= 0:
        return jsonify({"error": "Quantidade deve ser um número positivo"}), 400

    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO movimentacoes (tipo, data, produto, quantidade, destino, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
            (tipo, data_movimentacao, produto, quantidade, destino, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Movimentação adicionada com sucesso!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/movimentacoes/<int:movimentacao_id>', methods=['PUT'])
def update_movimentacao(movimentacao_id):
    """
    Endpoint para atualizar uma movimentação existente.
    Recebe o ID da movimentação na URL e os dados atualizados via JSON.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Dados inválidos"}), 400

    tipo = data.get('tipo')
    data_movimentacao = data.get('data')
    produto = data.get('produto')
    quantidade = data.get('quantidade')
    destino = data.get('destino', None)

    if not all([tipo, data_movimentacao, produto, quantidade is not None]):
        return jsonify({"error": "Campos obrigatórios faltando"}), 400

    if not isinstance(quantidade, (int, float)) or quantidade <= 0:
        return jsonify({"error": "Quantidade deve ser um número positivo"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.execute(
            'UPDATE movimentacoes SET tipo = ?, data = ?, produto = ?, quantidade = ?, destino = ?, timestamp = ? WHERE id = ?',
            (tipo, data_movimentacao, produto, quantidade, destino, datetime.now().isoformat(), movimentacao_id)
        )
        conn.commit()
        conn.close()

        if cursor.rowcount == 0:
            return jsonify({"error": "Movimentação não encontrada"}), 404
        return jsonify({"message": "Movimentação atualizada com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/movimentacoes/<int:movimentacao_id>', methods=['DELETE'])
def delete_movimentacao(movimentacao_id):
    """
    Endpoint para excluir uma movimentação.
    Recebe o ID da movimentação na URL.
    """
    try:
        conn = get_db_connection()
        cursor = conn.execute('DELETE FROM movimentacoes WHERE id = ?', (movimentacao_id,))
        conn.commit()
        conn.close()

        if cursor.rowcount == 0:
            return jsonify({"error": "Movimentação não encontrada"}), 404
        return jsonify({"message": "Movimentação excluída com sucesso!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Inicialização da Aplicação ---
# Este bloco garante que o banco de dados seja inicializado (tabela criada)
# quando o script Flask é executado.
with app.app_context():
    init_db()

# Executa o servidor Flask em modo de depuração.
# Em um ambiente de produção, `debug=False` e use um servidor WSGI (Gunicorn, uWSGI).
if __name__ == '__main__':
    app.run(debug=True, port=5000) # Rodando na porta 5000 por padrão
