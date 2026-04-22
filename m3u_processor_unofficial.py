#!/usr/bin/env python3
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
]

def extrair_atributos(linha):
    attrs = dict(regex_attr.findall(linha))
    return {
        "tvg_id": attrs.get("tvg-id", "").strip(),
        "tvg_name": attrs.get("tvg-name", "").strip(),
        "tvg_logo": attrs.get("tvg-logo", "").strip(),
        "group": attrs.get("group-title", "OUTROS").strip() or "OUTROS"
    }

def extrair_nome(linha):
    if "," in linha:
        return linha.split(",")[-1].strip()
    return "Sem Nome"

def limpar_texto(txt):
    return (txt or "").strip()

def processar_lista(pasta_entrada, pasta_saida, usuario="guest"):
    urls_vistas = set()
    canais = []
    epg_string = ",".join(EPG_URLS)
    
    header = '#EXTM3U url-tvg="' + epg_string + '"\n\n'
    header += '#PLAYLISTV: pltv-name="Josiel Jefferson"\n\n'
    
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
            print(f"Erro ao processar {arquivo}: {e}")
            continue
    
    caminho_saida = os.path.join(pasta_saida, "playlists.m3u")
    timestamp = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
    
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("# Atualizado em " + timestamp + " BRT\n\n")
        for c in canais:
            f.write('#EXTINF:-1 tvg-id="' + c["tvg_id"] + '" ')
            f.write('tvg-name="' + c["tvg_name"] + '" ')
            f.write('tvg-logo="' + c["tvg_logo"] + '" ')
            f.write('group-title="' + c["group"] + '",' + c["nome"] + '\n')
            f.write(c["url"] + "\n\n")
    
    with open(os.path.join(pasta_saida, "playlists.json"), "w", encoding="utf-8") as f:
        json.dump({"usuario": usuario, "timestamp": timestamp, "canais": canais}, f, indent=2, ensure_ascii=False)
    
    return canais
ENDOFFILE
