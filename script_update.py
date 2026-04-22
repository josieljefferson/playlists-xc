#!/usr/bin/env python3
import os
from m3u_processor import processar_lista

def main():
    pasta_entrada = "."
    pasta_saida = "docs"
    usuario = "Josiel Jefferson"

    print("🚀 Iniciando processamento...")

    canais = processar_lista(pasta_entrada, pasta_saida, usuario)

    if canais:
        print(f"📺 Total de canais: {len(canais)}")
    else:
        print("⚠️ Nenhum canal encontrado")

if __name__ == "__main__":
    main()
