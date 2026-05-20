import sys
import json
import urllib.request
import urllib.error
import os
import ssl
from pathlib import Path

from puzzle import Puzzle

# Desactivem la verificació SSL de forma global (necessari en alguns entorns macOS)
ssl._create_default_https_context = ssl._create_unverified_context

BASE_URL = "https://klotski.pauek.dev"


def get_token():
    """Llegeix el token d'autenticació des del fitxer token.txt."""
    token_path = "token.txt"
    if not os.path.exists(token_path):
        print(f"❌ Error: No s'ha trobat el fitxer '{token_path}'.")
        sys.exit(1)

    with open(token_path, "r") as f:
        # El .strip() elimina possibles salts de línia o espais invisibles
        return f.read().strip()


def upload_puzzle(puzzle: Puzzle):
    """Envia un puzzle al servidor."""
    token = get_token()
    url = f"{BASE_URL}/api/puzzles"

    # El format de dades net
    dades = puzzle.to_json().encode("utf-8")

    req = urllib.request.Request(
        url,
        data=dades,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201):
                print(f"✅ Èxit! Puzzle enviat correctament.")

    except urllib.error.HTTPError as e:
        print(f"❌ Error HTTP {e.code}: {e.reason}")
        try:
            # Intentem obtenir l'explicació interna del servidor
            error_msg = json.loads(e.read().decode())
            print(f"   Detall del servidor: {error_msg}")
        except:
            pass
    except Exception as e:
        print(f"❌ Error inesperat de connexió: {e}")


def main():
    if len(sys.argv) != 2:
        print("Ús: python src/upload.py <puzzle.json>")
        sys.exit(1)

    filepath_str = sys.argv[1]
    filepath = Path(filepath_str)

    try:
        puzzle = Puzzle.from_json(filepath.read_text())
    except Exception as e:
        print(f"Error en llegir el puzzle: {e}")
        sys.exit(1)

    upload_puzzle(puzzle)


if __name__ == "__main__":
    main()
