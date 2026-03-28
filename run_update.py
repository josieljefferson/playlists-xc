#!/usr/bin/env python3
"""
Wrapper para executar script_update.py em qualquer estrutura
"""
import os
import sys
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Possíveis locais para o script principal
    possible_paths = [
        os.path.join(script_dir, "script_update.py"),
        os.path.join(script_dir, "app", "script_update.py"),
        os.path.join(script_dir, "src", "script_update.py"),
    ]
    
    # Encontrar o script existente
    script_path = None
    for path in possible_paths:
        if os.path.isfile(path):
            script_path = path
            break
    
    if not script_path:
        print("❌ Erro: script_update.py não encontrado em nenhum dos caminhos:")
        for p in possible_paths:
            print(f"   - {p}")
        return 1
    
    print(f"✅ Executando: {script_path}")
    
    # Executar com o mesmo ambiente Python
    result = subprocess.run(
        [sys.executable, script_path] + sys.argv[1:],
        cwd=script_dir,
        env=os.environ.copy()
    )
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())