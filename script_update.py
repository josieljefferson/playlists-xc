#!/usr/bin/env python3
"""
IPTV System - Script de Atualização Automática
Executado pelo GitHub Actions a cada 6 horas
"""

import os
import sys
import json
import requests
from datetime import datetime

# ✅ Import do processador (mesma pasta)
from m3u_processor import processar_lista

# 📁 Configurações de paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOAD = os.path.join(SCRIPT_DIR, "downloads")
PASTA_OUTPUT = os.path.join(SCRIPT_DIR, "docs")
API_REPO = "https://api.github.com/repos/josieljefferson/iptv-system/contents/"

# 🚫 Arquivos ignorados
IGNORAR = {"requirements.txt", ".gitkeep", "README.md", ".gitignore"}

# 🌐 Headers para requests
HEADERS = {
    "User-Agent": "IPTV-System/2.0 (GitHub Actions)",
    "Accept": "application/vnd.github.v3+json",
}
if os.getenv("GITHUB_TOKEN"):
    HEADERS["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"


def listar_arquivos_m3u():
    """Lista URLs de download dos arquivos M3U do repositório"""
    try:
        response = requests.get(API_REPO, headers=HEADERS, timeout=30)
        response.raise_for_status()
        items = response.json()
        
        urls = []
        for item in items:
            nome = item.get("name", "")
            # Ignorar arquivos não desejados
            if nome in IGNORAR:
                continue
            # Aceitar apenas listas IPTV
            if nome.endswith((".m3u", ".m3u8", ".txt")):
                download_url = item.get("download_url")
                if download_url:                    urls.append(download_url)
                    print(f"✅ Encontrado: {nome}")
        return urls
    except Exception as e:
        print(f"❌ Erro ao listar arquivos: {e}")
        return []


def baixar_arquivos(urls):
    """Baixa arquivos M3U para pasta local"""
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)
    baixados = 0
    
    for url in urls:
        nome = url.split("/")[-1]
        caminho = os.path.join(PASTA_DOWNLOAD, nome)
        
        try:
            print(f"⬇️ Baixando: {nome}")
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            
            with open(caminho, "wb") as f:
                f.write(resp.content)
            baixados += 1
            print(f"✅ {nome} baixado")
            
        except Exception as e:
            print(f"⚠️ Erro ao baixar {nome}: {e}")
            continue
    
    print(f"📥 Total baixados: {baixados}/{len(urls)}")
    return baixados


def gerar_metadata(canais: list, usuario: str = "system"):
    """Gera arquivo JSON com metadados da playlist"""
    metadata = {
        "gerado_em": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "America/Fortaleza",
        "usuario": usuario,
        "total_canais": len(canais),
        "grupos": list(set(c.get("group", "OUTROS") for c in canais)),
        "versao": "2.0.0"
    }
    
    caminho = os.path.join(PASTA_OUTPUT, "metadata.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        return metadata


def main():
    print("🚀 Iniciando atualização IPTV System...")
    print(f"📁 Diretório: {SCRIPT_DIR}")
    
    # ✅ Criar pastas
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)
    os.makedirs(PASTA_OUTPUT, exist_ok=True)
    
    # 📋 Listar e baixar arquivos
    print("\n🔍 Buscando arquivos M3U...")
    urls = listar_arquivos_m3u()
    
    if not urls:
        print("⚠️ Nenhum arquivo M3U encontrado para processar")
        # Criar playlist vazia válida para não quebrar o sistema
        with open(os.path.join(PASTA_OUTPUT, "playlists.m3u"), "w", encoding="utf-8") as f:
            f.write('#EXTM3U url-tvg=""\n# ⚠️ Nenhuma fonte disponível no momento\n')
        return 0
    
    print(f"\n⬇️ Baixando {len(urls)} arquivo(s)...")
    baixados = baixar_arquivos(urls)
    
    if baixados == 0:
        print("❌ Falha ao baixar arquivos. Abortando.")
        return 1
    
    # 🔄 Processar playlists
    print("\n🔄 Processando playlists...")
    try:
        canais = processar_lista(PASTA_DOWNLOAD, PASTA_OUTPUT, usuario="github-actions")
        print(f"✅ Processados {len(canais)} canais únicos")
    except Exception as e:
        print(f"❌ Erro ao processar: {e}")
        return 1
    
    # 📊 Gerar metadados
    print("\n📊 Gerando metadados...")
    meta = gerar_metadata(canais)
    print(f"📦 Grupos encontrados: {', '.join(meta['grupos'][:5])}")
    
    # ✅ Resumo final
    print("\n" + "="*50)
    print("✅ ATUALIZAÇÃO CONCLUÍDA")
    print(f"📺 Canais: {meta['total_canais']}")
    print(f"📁 Saída: {PASTA_OUTPUT}/playlists.m3u")
    print(f"🕐 Gerado em: {meta['gerado_em']}")
    print("="*50)    
    return 0


if __name__ == "__main__":
    sys.exit(main())