import os
import re
import hashlib
import json
from datetime import datetime
from typing import Optional

# ✅ Regex aprimorado para atributos M3U
regex_attr = re.compile(r'''([\w-]+)=["']([^"']*)["']''')

# 📡 Lista de EPGs organizados por região
EPG_URLS = [
    "https://m3u4u.com/epg/jq2zy9epr3bwxmgwyxr5",
    "https://m3u4u.com/epg/3wk1y24kx7uzdevxygz7",
    "https://www.open-epg.com/files/brazil1.xml.gz",
    "https://www.open-epg.com/files/brazil2.xml.gz",
    "https://www.open-epg.com/files/portugal1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz",
]

# 🛡️ Headers anti-bloqueio para requests [[27]][[29]]
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def extrair_atributos(linha: str) -> dict:
    """Extrai atributos da linha #EXTINF"""
    attrs = dict(regex_attr.findall(linha))
    return {
        "tvg_id": attrs.get("tvg-id", "").strip(),
        "tvg_name": attrs.get("tvg-name", "").strip(),
        "tvg_logo": attrs.get("tvg-logo", "").strip(),
        "group": attrs.get("group-title", "OUTROS").strip() or "OUTROS"
    }

def extrair_nome(linha: str) -> str:
    """Extrai nome do canal da linha #EXTINF"""
    if "," in linha:
        return linha.split(",")[-1].strip()
    return "Sem Nome"
def limpar_texto(txt: Optional[str]) -> str:
    """Limpa e valida texto"""
    return (txt or "").strip()

def gerar_hash_url(url: str) -> str:
    """Gera hash único para URL (deduplicação)"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def processar_lista(pasta_entrada: str, pasta_saida: str, usuario: str = "guest") -> list:
    """Processa arquivos M3U e gera playlist consolidada"""
    urls_vistas = set()
    canais = []
    epg_string = ",".join(EPG_URLS)
    
    # Header profissional com metadados
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
                            "tvg_logo": limpar_texto(attrs["tvg_logo"]),                            "group": limpar_texto(attrs["group"]) or "OUTROS"
                        }
                    
                    elif linha.startswith("http") and dados_extinf:
                        url_hash = gerar_hash_url(linha)
                        
                        # ✅ Evita duplicatas
                        if url_hash not in urls_vistas:
                            urls_vistas.add(url_hash)
                            canal = {**dados_extinf, "url": linha, "hash": url_hash}
                            canais.append(canal)
                        
                        dados_extinf = None
        except Exception as e:
            print(f"⚠️ Erro ao processar {arquivo}: {e}")
            continue
    
    # 💾 Salvar playlist com timestamp
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
    
    # 💾 Salvar JSON para API
    with open(os.path.join(pasta_saida, "playlists.json"), "w", encoding="utf-8") as f:
        json.dump({"usuario": usuario, "timestamp": timestamp, "canais": canais}, f, indent=2, ensure_ascii=False)
    
    return canais