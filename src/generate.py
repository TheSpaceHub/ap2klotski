import json
import random
import sys
import os

def get_piece_shapes():
    """Retorna les formes clàssiques de peces en format canònic (relatiu a 0,0)."""
    return [
        [[0, 0], [0, 1], [1, 0], [1, 1]],  # 2x2 (Peça objectiu)
        [[0, 0], [0, 1]],                  # 1x2 (Vertical)
        [[0, 0], [1, 0]],                  # 2x1 (Horitzontal)
        [[0, 0]]                           # 1x1 (Quadrat petit)
    ]

def can_place(board, shape, px, py, W, H):
    """Comprova si una peça encaixa al tauler en la posició (px, py) sense solapar-se."""
    for rx, ry in shape:
        nx, ny = px + rx, py + ry
        if nx < 0 or nx >= W or ny < 0 or ny >= H:
            return False
        if board[ny][nx] != -1:
            return False
    return True

def generate_random_puzzle(W=4, H=5):
    """Genera un puzzle aleatori de peces lliscants seguint les regles estructurals."""
    board = [[-1 for _ in range(W)] for _ in range(H)]
    shapes = get_piece_shapes()
    pieces_info = [] 
    
    # 1. Col·locar la peça objectiu (2x2) lluny de la meta
    goal_shape = shapes[0]
    gx = random.randint(0, W - 2)
    gy = random.randint(0, H - 3) 
    
    for rx, ry in goal_shape:
        board[gy + ry][gx + rx] = 0
    pieces_info.append({"shape": goal_shape, "px": gx, "py": gy, "is_goal": True})
    
    # 2. Omplir la resta del tauler fins a deixar 2 espais buits
    empty_spaces = W * H - len(goal_shape)
    attempts = 0
    
    while empty_spaces > 2 and attempts < 200:
        shape = random.choice(shapes[1:]) 
        px = random.randint(0, W - 1)
        py = random.randint(0, H - 1)
        
        if can_place(board, shape, px, py, W, H):
            for rx, ry in shape:
                board[py + ry][px + rx] = len(pieces_info)
            pieces_info.append({"shape": shape, "px": px, "py": py, "is_goal": False})
            empty_spaces -= len(shape)
        attempts += 1
        
    # 3. Canonicalització: Ordenar per forma i després per posició
    def sort_key(p):
        return (sorted(p["shape"]), p["px"], p["py"])
        
    pieces_info.sort(key=sort_key)
    
    # 4. Construir el diccionari final en format estàndard
    puzzle_pieces = []
    start_positions = []
    goals = []
    
    for i, p in enumerate(pieces_info):
        puzzle_pieces.append(p["shape"])
        start_positions.append([p["px"], p["py"]])
        if p["is_goal"]:
            # Meta estàndard del Klotski: Centre de la fila inferior
            goals.append({"i": i, "pos": [1, H - 2]})
            
    puzzle = {
        "W": W,
        "H": H,
        "walls": [],
        "pieces": puzzle_pieces,
        "start": start_positions,
        "goals": goals
    }
    
    return puzzle

def main():
    if len(sys.argv) != 2:
        print("Ús: python src/generate.py <ruta_sortida.json>")
        sys.exit(1)
        
    out_filepath = sys.argv[1]
    
    # Genera i guarda el puzzle
    puzzle = generate_random_puzzle(W=4, H=5)
    
    # Crea el directori si no existeix
    out_dir = os.path.dirname(out_filepath)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    with open(out_filepath, 'w') as f:
        json.dump(puzzle, f, indent=2)
        
    print(f"Puzzle generat correctament: {out_filepath}")

if __name__ == "__main__":
    main()