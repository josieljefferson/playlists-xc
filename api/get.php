<?php
/**
 * IPTV System - API Endpoint PHP
 * Compatibilidade com players que exigem .php
 * 
 * @author ☆Josiel Jefferson☆
 * @email josielluz@proton.me
 * @version 2.0.0
 */

// 🔒 Configurações de segurança
header("Content-Type: application/x-mpegURL; charset=utf-8");
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Cache-Control: post-check=0, pre-check=0", false);
header("Pragma: no-cache");
header("X-Content-Type-Options: nosniff");
header("X-Frame-Options: DENY");

// 🌍 CORS para acesso cross-origin
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$allowed = [
    'https://josieljefferson12.github.io',
    'https://playlists-xc.onrender.com',
    'http://localhost:3000'
];
if (in_array($origin, $allowed)) {
    header("Access-Control-Allow-Origin: $origin");
    header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
    header("Access-Control-Allow-Headers: Content-Type, Authorization");
}
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// 🔐 Configurações do sistema
$API_BASE = getenv('API_BASE_URL') ?: 'https://playlists-xc.onrender.com';
$PYTHON_API = "$API_BASE/api/get.php"; // Endpoint Python real
$CACHE_TTL = 3600; // 1 hora em segundos
$CACHE_DIR = __DIR__ . '/../cache';

// 📁 Criar diretório de cache se não existir
if (!is_dir($CACHE_DIR)) {
    mkdir($CACHE_DIR, 0755, true);
}

// 🔑 Função para validar credenciais
function validateCredentials($username, $password) {
    $api_key = getenv("API_KEY_" . strtoupper($username));
    $salt = getenv("SALT_" . strtoupper($username));    
    if (!$api_key || !$salt) {
        return false;
    }
    
    // Hash da senha fornecida
    $test_hash = hash_pbkdf2("sha256", $password, $salt, 100000, 64, true);
    $test_hex = bin2hex($test_hash);
    
    // Comparação segura contra timing attacks
    return hash_equals($api_key, $test_hex);
}

// 🔄 Função para gerar cache key
function getCacheKey($username, $type, $output) {
    return md5("playlist_{$username}_{$type}_{$output}");
}

// 💾 Função para ler/escrever cache
function getCachedPlaylist($key) {
    global $CACHE_DIR, $CACHE_TTL;
    $file = "$CACHE_DIR/{$key}.m3u";
    
    if (file_exists($file) && (time() - filemtime($file)) < $CACHE_TTL) {
        return file_get_contents($file);
    }
    return false;
}

function setCachedPlaylist($key, $content) {
    global $CACHE_DIR;
    $file = "$CACHE_DIR/{$key}.m3u";
    file_put_contents($file, $content, LOCK_EX);
}

// 📥 Capturar parâmetros da requisição
$username = $_GET['username'] ?? $_POST['username'] ?? '';
$password = $_GET['password'] ?? $_POST['password'] ?? '';
$type = $_GET['type'] ?? $_GET['output'] ?? 'm3u';
$output = $_GET['output'] ?? 'ts';
$token = $_SERVER['HTTP_AUTHORIZATION'] ?? $_GET['token'] ?? '';

// 🔐 Validar autenticação
$authorized = false;

// Método 1: Bearer Token
if (!empty($token) && stripos($token, 'Bearer ') === 0) {
    $jwt = substr($token, 7);
    // Verificação simplificada - em produção, validar JWT propriamente
    $authorized = !empty($jwt) && strlen($jwt) > 20;}

// Método 2: Username + Password
if (!$authorized && !empty($username) && !empty($password)) {
    $authorized = validateCredentials($username, $password);
}

// ❌ Acesso negado
if (!$authorized) {
    http_response_code(401);
    echo json_encode([
        "error" => "Unauthorized",
        "message" => "Credenciais inválidas ou ausentes",
        "hint" => "Use: ?username=SEU_USER&password=SUA_SENHA&type=m3u_plus"
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// 🎯 Definir tipo de conteúdo de saída
$contentType = match($type) {
    'json' => 'application/json',
    'm3u_plus', 'm3u8' => 'application/x-mpegURL',
    default => 'application/x-mpegURL'
};
header("Content-Type: {$contentType}; charset=utf-8");

// 🔄 Tentar servir do cache primeiro
$cacheKey = getCacheKey($username, $type, $output);
$cached = getCachedPlaylist($cacheKey);

if ($cached !== false) {
    echo $cached;
    exit;
}

// 🌐 Proxy para API Python (fallback inteligente)
function fetchFromPythonAPI($base, $user, $pass, $type, $output) {
    $url = sprintf("%s?username=%s&password=%s&type=%s&output=%s",
        $base,
        urlencode($user),
        urlencode($pass),
        urlencode($type),
        urlencode($output)
    );
    
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,        CURLOPT_TIMEOUT => 30,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_USERAGENT => 'playlists-xc-PHP/2.0 (compatible; IPTV Player)',
        CURLOPT_HTTPHEADER => [
            'Accept: */*',
            'Accept-Language: pt-BR,pt;q=0.9',
            'Cache-Control: no-cache'
        ],
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($httpCode === 200 && !empty($response)) {
        return $response;
    }
    
    error_log("PHP Proxy Error: HTTP $httpCode - $error");
    return false;
}

// 🔄 Buscar playlist da API Python
$playlist = fetchFromPythonAPI($PYTHON_API, $username, $password, $type, $output);

if ($playlist !== false) {
    // 💾 Salvar em cache
    setCachedPlaylist($cacheKey, $playlist);
    echo $playlist;
} else {
    // 🚨 Fallback: Playlist mínima de erro
    http_response_code(503);
    echo "#EXTM3U url-tvg=\"\"\n";
    echo "# ❌ Serviço temporariamente indisponível\n";
    echo "# 🔄 Tente novamente em alguns minutos\n";
    echo "#EXTINF:-1 tvg-name=\"Erro\" group-title=\"Sistema\",⚠️ Servidor Ocupado\n";
    echo "https://httpbin.org/status/503\n";
}

// 🧹 Limpeza opcional de cache antigo (1% de chance por requisição)
if (rand(1, 100) === 1) {
    foreach (glob("$CACHE_DIR/*.m3u") as $file) {
        if (is_file($file) && (time() - filemtime($file)) > ($CACHE_TTL * 2)) {
            @unlink($file);
        }
    }
}?>