"""
IPTV System - Utility Functions
Módulo de funções auxiliares: cache, headers, rate limiting e helpers
"""

import os
import time
import hashlib
import json
import requests
import re
from functools import wraps, lru_cache
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from flask import request, g, jsonify

# 🎯 Configurações globais
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hora padrão
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# 🌐 Headers anti-bloqueio com rotação [[27]][[29]]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "DNT": "1",
}


def get_rotating_headers() -> Dict[str, str]:
    """Retorna headers com User-Agent rotativo para evitar bloqueios"""
    import random
    headers = BASE_HEADERS.copy()    headers["User-Agent"] = random.choice(USER_AGENTS)
    
    # Adicionar headers aleatórios para parecer mais humano
    if random.random() > 0.7:
        headers["Sec-Ch-Ua"] = '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"'
        headers["Sec-Ch-Ua-Mobile"] = "?0"
        headers["Sec-Ch-Ua-Platform"] = '"Windows"'
    
    return headers


def gerar_hash_cache(key: str, *args, **kwargs) -> str:
    """Gera hash MD5 para chave de cache"""
    data = f"{key}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(data.encode()).hexdigest()[:16]


def get_cache_path(key: str) -> str:
    """Retorna caminho do arquivo de cache"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.cache")


def cache_read(key: str, ttl: int = None) -> Optional[Any]:
    """Lê dados do cache se não expirados"""
    if ttl is None:
        ttl = CACHE_TTL
    
    path = get_cache_path(key)
    
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Verificar expiração
        if time.time() - data["timestamp"] < ttl:
            return data["content"]
        else:
            # Cache expirado - remover
            os.remove(path)
            return None
    except (json.JSONDecodeError, IOError):
        return None


def cache_write(key: str, content: Any, ttl: int = None) -> bool:
    """Escreve dados no cache com timestamp"""    if ttl is None:
        ttl = CACHE_TTL
    
    path = get_cache_path(key)
    
    try:
        data = {
            "timestamp": time.time(),
            "ttl": ttl,
            "content": content
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def cache_delete(key: str) -> bool:
    """Remove entrada do cache"""
    path = get_cache_path(key)
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except OSError:
        return False


def cache_cleanup(max_age: int = None) -> int:
    """Limpa cache expirado - retorna número de arquivos removidos"""
    if max_age is None:
        max_age = CACHE_TTL * 2  # 2x o TTL padrão
    
    removed = 0
    now = time.time()
    
    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith(".cache"):
            continue
        
        path = os.path.join(CACHE_DIR, filename)
        try:
            if now - os.path.getmtime(path) > max_age:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    
    return removed

def fetch_with_retry(
    url: str, 
    method: str = "GET", 
    headers: Dict = None, 
    max_retries: int = None,
    timeout: int = None,
    **kwargs
) -> Optional[requests.Response]:
    """
    Faz request HTTP com retry exponencial e headers anti-bloqueio
    """
    if max_retries is None:
        max_retries = MAX_RETRIES
    if timeout is None:
        timeout = REQUEST_TIMEOUT
    if headers is None:
        headers = get_rotating_headers()
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=timeout,
                **kwargs
            )
            
            # Sucesso para códigos 2xx
            if response.status_code < 400:
                return response
            
            # Para 429 (rate limit), esperar mais
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                time.sleep(min(retry_after, 30))
                continue
                
            # Para 4xx/5xx, tentar novamente com backoff exponencial
            if response.status_code >= 400:
                wait_time = min(2 ** attempt, 10)  # Max 10 segundos
                time.sleep(wait_time)
                # Rotacionar headers na próxima tentativa
                headers = get_rotating_headers()
                continue
                        except requests.exceptions.Timeout:
            last_error = "Timeout"
        except requests.exceptions.ConnectionError:
            last_error = "ConnectionError"
        except requests.exceptions.RequestException as e:
            last_error = str(e)
        
        # Backoff exponencial entre tentativas
        if attempt < max_retries:
            time.sleep(min(2 ** attempt, 10))
    
    # Todas as tentativas falharam
    if last_error:
        print(f"❌ Request falhou após {max_retries + 1} tentativas: {last_error}")
    return None


def rate_limit(max_requests: int = 60, window: int = 60):
    """
    Decorator para rate limiting simples por IP
    max_requests: número máximo de requisições
    window: janela de tempo em segundos
    """
    # Armazenamento em memória (use Redis em produção)
    requests_log: Dict[str, list] = {}
    
    def decorator(f: Callable):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Identificador: IP do cliente ou username se autenticado
            client_id = getattr(request, "current_user", None) or request.remote_addr or "unknown"
            now = time.time()
            
            # Limpar entradas antigas
            if client_id in requests_log:
                requests_log[client_id] = [
                    t for t in requests_log[client_id] 
                    if now - t < window
                ]
            else:
                requests_log[client_id] = []
            
            # Verificar limite
            if len(requests_log[client_id]) >= max_requests:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Máximo de {max_requests} requisições por {window}s",
                    "retry_after": int(window - (now - requests_log[client_id][0]))
                }), 429
                        # Registrar requisição
            requests_log[client_id].append(now)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


def sanitize_filename(filename: str, default: str = "file") -> str:
    """Sanitiza nome de arquivo para evitar path traversal"""
    # Remover caracteres perigosos
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remover paths relativos
    sanitized = os.path.basename(sanitized)
    # Garantir que não está vazio
    return sanitized if sanitized else default


def format_timestamp(dt: datetime = None, timezone: str = "America/Fortaleza") -> str:
    """Formata timestamp para exibição em BRT"""
    if dt is None:
        dt = datetime.utcnow()
    
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        dt_brt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(timezone))
        return dt_brt.strftime("%d/%m/%Y - %H:%M:%S")
    except ImportError:
        # Fallback sem zoneinfo
        return dt.strftime("%d/%m/%Y - %H:%M:%S") + " UTC"


def log_request(endpoint: str, user: str = None, metadata: Dict = None):
    """Log simplificado de requisições (substitua por serviço real em produção)"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "user": user,
        "ip": request.remote_addr,
        "method": request.method,
        "user_agent": request.headers.get("User-Agent", "")[:100],
        **(metadata or {})
    }
    
    # Em produção: enviar para CloudWatch, Datadog, etc.
    # Para desenvolvimento: print ou arquivo
    print(f"[LOG] {json.dumps(log_entry, ensure_ascii=False)}")


# 🎯 Decorator para cache de funçõesdef cached_function(ttl: int = None, key_prefix: str = ""):
    """Decorator para cache de resultados de função"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gerar chave de cache única
            func_name = func.__name__
            cache_key = gerar_hash_cache(f"{key_prefix}{func_name}", *args, **kwargs)
            
            # Tentar ler do cache
            cached = cache_read(cache_key, ttl)
            if cached is not None:
                return cached
            
            # Executar função e salvar resultado
            result = func(*args, **kwargs)
            cache_write(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


# 🔄 Inicialização de cache ao importar módulo
def init_cache():
    """Inicializa diretório de cache e limpa expirados"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    removed = cache_cleanup()
    if removed > 0:
        print(f"🧹 Cache cleanup: {removed} arquivos removidos")


# Auto-inicializar
init_cache()