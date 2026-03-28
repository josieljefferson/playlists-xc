import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
import jwt

# Configurações
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
TOKEN_EXPIRY = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash seguro de senha com salt"""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verifica senha contra hash armazenado"""
    test_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(test_hash, hashed)

def generate_token(username: str) -> str:
    """Gera JWT token para o usuário"""
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict | None:
    """Verifica e decodifica JWT token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_api_auth(f):
    """Decorator para proteger endpoints da API"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Método 1: Bearer Token (Header)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):            token = auth_header[7:]
            payload = verify_token(token)
            if payload:
                request.current_user = payload["username"]
                return f(*args, **kwargs)
        
        # Método 2: Query Params (compatibilidade M3U)
        username = request.args.get("username")
        password = request.args.get("password")
        api_key = os.getenv(f"API_KEY_{username.upper()}" if username else "")
        
        if username and password and api_key:
            expected_hash, salt = hash_password(password, os.getenv(f"SALT_{username.upper()}", ""))
            if hmac.compare_digest(api_key, expected_hash):
                request.current_user = username
                return f(*args, **kwargs)
        
        return jsonify({"error": "Unauthorized", "message": "Credenciais inválidas"}), 401
    return decorated

# Banco de usuários em memória (substitua por banco real em produção)
USERS_DB = {}

def register_user(username: str, password: str, email: str = "") -> dict:
    """Registra novo usuário"""
    if username in USERS_DB:
        return {"success": False, "message": "Usuário já existe"}
    
    hashed, salt = hash_password(password)
    USERS_DB[username] = {
        "password_hash": hashed,
        "salt": salt,
        "email": email,
        "created_at": datetime.utcnow().isoformat()
    }
    # Salvar credenciais para API em variáveis de ambiente (opcional)
    api_key = hashed  # Usa o hash como API key
    os.environ[f"API_KEY_{username.upper()}"] = api_key
    os.environ[f"SALT_{username.upper()}"] = salt
    
    return {"success": True, "message": "Usuário registrado com sucesso"}

def login_user(username: str, password: str) -> dict:
    """Faz login e retorna token"""
    user = USERS_DB.get(username)
    if not user:
        return {"success": False, "message": "Usuário não encontrado"}
    
    if verify_password(password, user["password_hash"], user["salt"]):
        token = generate_token(username)        return {"success": True, "token": token, "username": username}
    
    return {"success": False, "message": "Senha incorreta"}