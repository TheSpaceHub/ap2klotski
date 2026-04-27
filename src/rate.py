import sys
import json
import urllib.request
import urllib.error
import os
import ssl

# Desactivem la verificació SSL de forma global (necessari en alguns entorns macOS)
ssl._create_default_https_context = ssl._create_unverified_context

BASE_URL = "https://klotski.pauek.dev"

def get_token():
    """Llegeix el token d'autenticació des del fitxer token.txt."""
    token_path = "token.txt"
    if not os.path.exists(token_path):
        print(f"❌ Error: No s'ha trobat el fitxer '{token_path}'.")
        sys.exit(1)
        
    with open(token_path, 'r') as f:
        # El .strip() elimina possibles salts de línia o espais invisibles
        return f.read().strip()

def rate_puzzle(puzzle_id, rating):
    """Envia la valoració d'un puzzle al servidor."""
    token = get_token()
    puzzle_id = puzzle_id.strip()
    url = f"{BASE_URL}/api/puzzles/{puzzle_id}/stars"
    
    # El format de dades net
    dades = json.dumps({"stars": rating}).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=dades,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0"
        }
    )
    
    print(f"📡 Enviant {rating} estrelles al puzzle: {puzzle_id[:8]}...")
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201):
                print(f"✅ Èxit! Valoració enviada correctament.")
                
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
    if len(sys.argv) != 3:
        print("Ús: python src/rate.py <ID_del_puzzle> <valoració_0_a_5>")
        sys.exit(1)
        
    puzzle_id = sys.argv[1]
    
    try:
        rating = float(sys.argv[2])
        if rating < 0.0 or rating > 5.0:
            raise ValueError()
    except ValueError:
        print("❌ Error: La valoració ha de ser un número decimal entre 0.0 i 5.0")
        sys.exit(1)
        
    rate_puzzle(puzzle_id, rating)

if __name__ == "__main__":
    main()