#!/usr/bin/env python3
import os
import sys
import json
import requests
from datetime import datetime
from m3u_processor import processar_lista

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DOWNLOAD = os.path.join(SCRIPT_DIR, "downloads")
PASTA_OUTPUT = os.path.join(SCRIPT_DIR, "docs")
API_REPO = "https://api.github.com/repos/josieljefferson/iptv-system/contents/"

IGNORAR = {"requirements.txt", ".gitkeep", "README.md", ".gitignore"}

HEADERS = {"User-Agent": "IPTV-System/2.0", "Accept": "application/vnd.github.v3+json"}
if os.getenv("GITHUB_TOKEN"):
    HEADERS["Authorization"] = "token " + os.getenv("GITHUB_TOKEN")

def listar_arquivos_m3u():
    try:
        response = requests.get(API_REPO, headers=HEADERS, timeout=30)
        response.raise_for_status()
        items = response.json()
        urls = []
        for item in items:
            nome = item.get("name", "")
            if nome in IGNORAR:
                continue
            if nome.endswith((".m3u", ".m3u8", ".txt")):
                download_url = item.get("download_url")
                if download_url:
                    urls.append(download_url)
                    print("Encontrado: " + nome)
        return urls
    except Exception as e:
        print("Erro ao listar arquivos: " + str(e))
        return []

def baixar_arquivos(urls):
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)
    baixados = 0
    for url in urls:
        nome = url.split("/")[-1]
        caminho = os.path.join(PASTA_DOWNLOAD, nome)
        try:
            print("Baixando: " + nome)
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            with open(caminho, "wb") as f:
                f.write(resp.content)
            baixados += 1
            print(nome + " baixado")
        except Exception as e:
            print("Erro ao baixar " + nome + ": " + str(e))
            continue
    print("Total baixados: " + str(baixados) + "/" + str(len(urls)))
    return baixados

def main():
    print("Iniciando atualizacao IPTV System...")
    os.makedirs(PASTA_DOWNLOAD, exist_ok=True)
    os.makedirs(PASTA_OUTPUT, exist_ok=True)
    
    print("Buscando arquivos M3U...")
    urls = listar_arquivos_m3u()
    
    if not urls:
        print("Nenhum arquivo M3U encontrado")
        with open(os.path.join(PASTA_OUTPUT, "playlists.m3u"), "w") as f:
            f.write("#EXTM3U url-tvg=\"\"\n")
        return 0
    
    print("Baixando " + str(len(urls)) + " arquivo(s)...")
    baixados = baixar_arquivos(urls)
    
    if baixados == 0:
        print("Falha ao baixar arquivos")
        return 1
    
    print("Processando playlists...")
    try:
        canais = processar_lista(PASTA_DOWNLOAD, PASTA_OUTPUT, usuario="github-actions")
        print("Processados " + str(len(canais)) + " canais")
    except Exception as e:
        print("Erro ao processar: " + str(e))
        return 1
    
    print("ATUALIZACAO CONCLUIDA")
    return 0

if __name__ == "__main__":
    sys.exit(main())
ENDOFFILE
