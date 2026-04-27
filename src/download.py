import urllib.request
import json
import sys
import os
import ssl

# Això desactiva la verificació de certificats SSL de forma global
ssl._create_default_https_context = ssl._create_unverified_context

url_base = "https://klotski.pauek.dev/api/puzzles"

def get_puzzles_list():
    "Obté la llista dels 100 puzzles millor valorats del repositori"
    print("Descarregant llista de puzzles...")
    with urllib.request.urlopen(url_base) as response:
        puzzles = json.loads(response.read().decode())
        for p in puzzles:
            print(f"ID: {p}")


def download_one_puzzle(puzzle_id: int):
    "Descarrega un puzzle específic i el guarda a la carpeta /puzzles"
    url = f"{url_base}/{puzzle_id}"
    print(f"Descarregant el puzzle {puzzle_id}...")
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            
        # Ens assegurem que la carpeta 'puzzles' existeix
        if not os.path.exists('puzzles'):
            os.makedirs('puzzles')
            
        filepath = f"puzzles/{puzzle_id}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
            
        print(f"Guardat correctament a: {filepath}")
        
    except Exception as e:
        print(f"Error descarregant el puzzle: {e}")

if __name__ == "__main__":
    # Si l'usuari posa un argument (python src/download.py 123)
    if len(sys.argv) > 1:
        download_one_puzzle(sys.argv[1])
    # Si no posa res, llistem els puzzles
    else:
        get_puzzles_list()



