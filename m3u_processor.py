#!/usr/bin/env python3
"""
IPTV System - Processador de Playlists M3U
"""

import os
import re
import json
from datetime import datetime

regex_attr = re.compile(r'([\w-]+)="([^"]*)"')

EPG_URLS = [
    "https://m3u4u.com/epg/jq2zy9epr3bwxmgwyxr5",
    "https://m3u4u.com/epg/3wk1y24kx7uzdevxygz7",
    "https://www.open-epg.com/files/brazil1.xml.gz",
    "https://www.open-epg.com/files/brazil2.xml.gz",
    "https://www.open-epg.com/files/portugal1.xml.gz",
]


def extrair_atributos(linha):
    """Extrai atributos da linha #EXTINF"""
    attrs = dict(regex_attr.findall(linha))
    return {
        "tvg_id": attrs.get("tvg-id", "").strip(),
        "tvg_name": attrs.get("tvg-name", "").strip(),
        "tvg_logo": attrs.get("tvg-logo", "").strip(),
        "group": attrs.get("group-title", "OUTROS").strip() or "OUTROS"
    }


def extrair_nome(linha):
    """Extrai nome do canal"""
    if "," in linha:
        return linha.split(",")[-1].strip()
    return "Sem Nome"


def limpar_texto(txt):
    """Limpa texto"""
    return (txt or "").strip()


def processar_lista(pasta_entrada, pasta_saida, usuario="guest"):
    """Processa arquivos M3U e gera playlist consolidada"""
    urls_vistas = set()
    canais = []
    epg_string = ",".join(EPG_URLS)
        header = (
        f'#EXTM3U url-tvg="{epg_string}" x-tvg-url="{epg_string}"\n\n'
        f'#PLAYLISTV: '
        f'pltv-logo="https://cdn-icons-png.flaticon.com/256/25/25231.png" '
        f'pltv-name="☆Josiel Jefferson☆" '
        f'pltv-description="Playlist GitHub Pages - Atualizada" '
        f'pltv-author="☆Josiel Jefferson☆" '
        f'pltv-site="https://josieljefferson12.github.io/" '
        f'pltv-email="josielluz@proton.me" '
        f'pltv-user="{usuario}"\n\n'
    )
    
    for arquivo in os.listdir(pasta_entrada):
        if not arquivo.endswith((".m3u", ".m3u8", ".txt")):
            continue
        
        caminho = os.path.join(pasta_entrada, arquivo)
        dados_extinf = None
        
        try:
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha or linha.startswith("#EXTM3U"):
                        continue
                    
                    if linha.startswith("#EXTINF"):
                        attrs = extrair_atributos(linha)
                        nome = extrair_nome(linha)
                        dados_extinf = {
                            "nome": limpar_texto(nome) or "Sem Nome",
                            "tvg_id": limpar_texto(attrs["tvg_id"]),
                            "tvg_name": limpar_texto(attrs["tvg_name"]) or nome,
                            "tvg_logo": limpar_texto(attrs["tvg_logo"]),
                            "group": limpar_texto(attrs["group"]) or "OUTROS"
                        }
                    
                    elif linha.startswith("http") and dados_extinf:
                        if linha not in urls_vistas:
                            urls_vistas.add(linha)
                            canal = {**dados_extinf, "url": linha}
                            canais.append(canal)
                        dados_extinf = None
        except Exception as e:
            print(f"⚠️ Erro ao processar {arquivo}: {e}")
            continue
    
    caminho_saida = os.path.join(pasta_saida, "playlists.m3u")
    timestamp = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(f"# 🔄 Atualizado em {timestamp} BRT\n\n")
        
        for c in canais:
            f.write(
                f'#EXTINF:-1 tvg-id="{c["tvg_id"]}" '
                f'tvg-name="{c["tvg_name"]}" '
                f'tvg-logo="{c["tvg_logo"]}" '
                f'group-title="{c["group"]}",{c["nome"]}\n'
            )
            f.write(c["url"] + "\n\n")
    
    with open(os.path.join(pasta_saida, "playlists.json"), "w", encoding="utf-8") as f:
        json.dump({"usuario": usuario, "timestamp": timestamp, "canais": canais}, f, indent=2, ensure_ascii=False)
    
    return canais