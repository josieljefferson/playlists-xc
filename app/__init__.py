import os
import requests
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
from functools import lru_cache
import time

from .auth import require_api_auth, register_user, login_user, USERS_DB
from .m3u_processor import processar_lista, BROWSER_HEADERS
from .utils import get_cached_response

app = Flask(__name__, static_folder="../docs", static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-in-production")

# Configurações
API_REPO = "https://api.github.com/repos/josieljefferson/playlists-xc/contents/"
PASTA_DOWNLOAD = "downloads"
PASTA_OUTPUT = "docs"
os.makedirs(PASTA_DOWNLOAD, exist_ok=True)
os.makedirs(PASTA_OUTPUT, exist_ok=True)

# 🚫 Arquivos ignorados
IGNORAR = {"requirements.txt", ".gitkeep", "README.md"}

@lru_cache(maxsize=100)
def get_cached_headers():
    """Retorna headers otimizados com rotação de User-Agent"""
    import random
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36",
    ]
    headers = BROWSER_HEADERS.copy()
    headers["User-Agent"] = random.choice(user_agents)
    return headers

@app.route("/")
def index():
    """Redireciona para dashboard"""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/register", methods=["POST"])
def api_register():
    """Endpoint de cadastro de usuário"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()    
    if len(username) < 3 or len(password) < 6:
        return jsonify({"success": False, "message": "Usuário mínimo 3 chars, senha mínima 6 chars"}), 400
    
    result = register_user(username, password, email)
    status = 201 if result["success"] else 400
    return jsonify(result), status

@app.route("/api/login", methods=["POST"])
def api_login():
    """Endpoint de login"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    result = login_user(username, password)
    status = 200 if result["success"] else 401
    return jsonify(result), status

@app.route("/api/get.php", methods=["GET"])
@require_api_auth
def api_get_playlist():
    """✅ Endpoint principal da API - Compatível com players IPTV"""
    username = request.current_user
    tipo = request.args.get("type", "m3u")
    output = request.args.get("output", "ts")
    
    # 🔄 Processa playlists (com cache simples)
    cache_key = f"{username}_{tipo}"
    last_update = getattr(api_get_playlist, "last_update", 0)
    now = time.time()
    
    # Atualiza a cada 6 horas ou se não existir
    if now - last_update > 21600 or not os.path.exists(os.path.join(PASTA_OUTPUT, "playlists.m3u")):
        try:
            # Baixar arquivos do repositório
            r = requests.get(API_REPO, headers=get_cached_headers(), timeout=30)
            if r.status_code == 200:
                for item in r.json():
                    nome = item["name"]
                    if nome in IGNORAR or not nome.endswith((".m3u", ".m3u8", ".txt")):
                        continue
                    
                    url = item.get("download_url")
                    if url:
                        try:
                            resp = requests.get(url, headers=get_cached_headers(), timeout=15)
                            if resp.status_code == 200:
                                with open(os.path.join(PASTA_DOWNLOAD, nome), "wb") as f:
                                    f.write(resp.content)                        except:
                            continue
            
            # Processar e gerar playlist
            processar_lista(PASTA_DOWNLOAD, PASTA_OUTPUT, username)
            api_get_playlist.last_update = now
            api_get_playlist.last_count = len(os.listdir(PASTA_DOWNLOAD))
            
        except Exception as e:
            app.logger.error(f"Erro ao atualizar: {e}")
    
    # Retornar no formato solicitado
    if tipo == "m3u_plus":
        return send_from_directory(PASTA_OUTPUT, "playlists.m3u", mimetype="application/x-mpegURL")
    elif tipo == "json":
        return send_from_directory(PASTA_OUTPUT, "playlists.json", mimetype="application/json")
    
    return send_from_directory(PASTA_OUTPUT, "playlists.m3u", mimetype="application/x-mpegURL")

@app.route("/api/status")
def api_status():
    """Endpoint de status para monitoramento"""
    return jsonify({
        "status": "online",
        "usuarios": len(USERS_DB),
        "ultima_atualizacao": getattr(api_get_playlist, "last_update", None),
        "arquivos_baixados": getattr(api_get_playlist, "last_count", 0),
        "timestamp": time.time()
    })

@app.route("/dashboard")
def dashboard():
    """Página do dashboard (requer autenticação via frontend)"""
    return send_from_directory(app.static_folder, "index.html")

# Handler para erros 404
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint não encontrado"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)