import sys
import json
import graph_tool.all as gt
from puzzle import Puzzle, State
from pathlib import Path
from collections import deque

def create_base_matrix(W, H, walls):
    """Crea un array 1D inicial només amb les parets (-2). Les cel·les buides són -1."""
    mat = [-1] * (W * H)
    for x, y in walls:
        mat[y * W + x] = -2
    return mat

def build_state_matrix(state, base_matrix, pieces, W):
    """Genera la matriu (internament 1D) del tauler utilitzant una còpia ràpida en memòria contigua."""
    mat = base_matrix[:]  # Còpia O(n) molt ràpida a nivell de C
    
    for piece_id, (pos_x, pos_y) in enumerate(state):
        base_idx = pos_y * W + pos_x
        for rel_x, rel_y in pieces[piece_id]:
            mat[base_idx + (rel_y * W + rel_x)] = piece_id
            
    return mat

def is_valid_move(piece_id, pos_x, pos_y, dx, dy, piece_shape, mat, W, H):
    """Comprova col·lisions de manera eficient amb límits 2D i array 1D."""
    for rel_x, rel_y in piece_shape:
        nx = pos_x + rel_x + dx
        ny = pos_y + rel_y + dy

        # 1. Comprovar límits
        if nx < 0 or nx >= W or ny < 0 or ny >= H:
            return False

        # 2. Comprovar col·lisions utilitzant mapeig 1D (y * W + x)
        cell_val = mat[ny * W + nx]
        if cell_val != -1 and cell_val != piece_id:
            return False

    return True

def generate_graph(puzzle: Puzzle) -> gt.Graph:
    """Construeix el graf d'estats utilitzant graph-tool i DFS optimitzat."""
    W = puzzle.get_width()
    H = puzzle.get_height()
    pieces = [x.get_coords() for x in puzzle.get_pieces()]
    walls = puzzle.get_walls()

    start_state = puzzle.get_start().get_positions()
    base_matrix = create_base_matrix(W, H, walls)

    g = gt.Graph(directed=True)
    
    vp_state = g.new_vertex_property("string")
    ep_piece = g.new_edge_property("int")
    ep_dir = g.new_edge_property("string")

    g.vertex_properties["state"] = vp_state
    g.edge_properties["piece"] = ep_piece
    g.edge_properties["dir"] = ep_dir

    visited = {}
    queue = deque([start_state])

    v_start = g.add_vertex()
    # RESTORED: format JSON exacte
    vp_state[v_start] = json.dumps(start_state) 
    visited[start_state] = v_start

    moves = [(0, -1, "N"), (0, 1, "S"), (1, 0, "E"), (-1, 0, "W")]

    print("Generant graf... Aquesta operació pot trigar segons la complexitat del puzzle.")

    while queue:
        current_state = queue.pop() 
        v_current = visited[current_state]

        mat = build_state_matrix(current_state, base_matrix, pieces, W)

        for piece_id, (px, py) in enumerate(current_state):
            piece_shape = pieces[piece_id]

            for dx, dy, direction in moves:
                if is_valid_move(piece_id, px, py, dx, dy, piece_shape, mat, W, H):
                    
                    # Utilitzem slicing de tuples per evitar el cost d'instanciar una llista
                    new_state = current_state[:piece_id] + ((px + dx, py + dy),) + current_state[piece_id + 1:]

                    if new_state not in visited:
                        v_new = g.add_vertex()
                        # RESTORED: format JSON exacte
                        vp_state[v_new] = json.dumps(new_state)
                        visited[new_state] = v_new
                        queue.append(new_state)
                    else:
                        v_new = visited[new_state]

                    # Afegim l'aresta directament
                    e = g.add_edge(v_current, v_new)
                    ep_piece[e] = piece_id
                    ep_dir[e] = direction

    print(f"Graf completat: {g.num_vertices()} estats i {g.num_edges()} moviments.")
    return g

def main():
    if len(sys.argv) != 2:
        print("Ús: python src/graph.py <ruta_al_puzzle.json>")
        sys.exit(1)

    filepath_str = sys.argv[1]
    filepath = Path(filepath_str)

    try:
        puzzle = Puzzle.from_json(filepath.read_text())
    except Exception as e:
        print(f"Error en llegir el puzzle: {e}")
        sys.exit(1)

    g = generate_graph(puzzle)

    out_filepath = filepath_str.replace(".json", ".graphml")
    if out_filepath == filepath_str:
        out_filepath += ".graphml"

    g.save(out_filepath)
    print(f"Graf guardat correctament a: {out_filepath}")

if __name__ == "__main__":
    main()