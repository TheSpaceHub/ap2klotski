import sys
import json
import graph_tool.all as gt
from puzzle import Puzzle, State
from pathlib import Path


def create_base_matrix(W, H, walls):
    """Crea la matriu inicial només amb les parets (-2). Les cel·les buides són -1."""
    mat = [[-1 for _ in range(W)] for _ in range(H)]
    for x, y in walls:
        mat[y][x] = -2
    return mat


def build_state_matrix(state, base_matrix, pieces):
    """Genera la matriu del tauler inserint les peces a la matriu base."""
    # Creem una còpia ràpida de la matriu base
    mat = [row[:] for row in base_matrix]

    for piece_id, (pos_x, pos_y) in enumerate(state):
        for rel_x, rel_y in pieces[piece_id]:
            mat[pos_y + rel_y][pos_x + rel_x] = piece_id

    return mat


def is_valid_move(piece_id, pos_x, pos_y, dx, dy, piece_shape, mat, W, H):
    """Comprova si una peça es pot moure en la direcció indicada (dx, dy)."""
    for rel_x, rel_y in piece_shape:
        nx = pos_x + rel_x + dx
        ny = pos_y + rel_y + dy

        # 1. Comprovar límits del tauler
        if nx < 0 or nx >= W or ny < 0 or ny >= H:
            return False

        # 2. Comprovar col·lisions amb parets (-2) o altres peces (diferents de piece_id)
        if mat[ny][nx] != -1 and mat[ny][nx] != piece_id:
            return False

    return True


def generate_graph(puzzle: Puzzle) -> gt.Graph:
    """Construeix el graf d'estats utilitzant graph-tool i DFS."""
    W = puzzle.get_width()
    H = puzzle.get_height()
    pieces = [x.get_coords() for x in puzzle.get_pieces()]
    walls = puzzle.get_walls()

    # L'estat inmutable serà una tupla de tuples: ((x1, y1), (x2, y2), ...)
    start_state = puzzle.get_start().get_positions()

    base_matrix = create_base_matrix(W, H, walls)

    # Inicialitzem el graf dirigit
    g = gt.Graph(directed=True)

    # Propietats per guardar la informació rellevant als vèrtexs i arestes
    vp_state = g.new_vertex_property(
        "string"
    )  # Guardarem l'estat com a JSON string per recuperar-lo
    ep_piece = g.new_edge_property("int")  # Índex de la peça moguda
    ep_dir = g.new_edge_property("string")  # Direcció del moviment ("N", "S", "E", "W")

    g.vertex_properties["state"] = vp_state
    g.edge_properties["piece"] = ep_piece
    g.edge_properties["dir"] = ep_dir

    # Estructures per a la cerca BFS
    visited = {}  # Diccionari per mapar: estat_tupla -> vertex_id
    queue = [start_state]

    # Creem el node arrel
    v_start = g.add_vertex()
    vp_state[v_start] = json.dumps(start_state)
    visited[start_state] = v_start

    # Vectors de moviment
    moves = [(0, -1, "N"), (0, 1, "S"), (1, 0, "E"), (-1, 0, "W")]

    print(
        f"Generant graf... Aquesta operació pot trigar segons la complexitat del puzzle."
    )

    while queue:
        current_state = queue.pop()
        v_current = visited[current_state]

        # Reconstruïm la matriu física d'aquest estat en O(1) respecte a allocs massius
        mat = build_state_matrix(current_state, base_matrix, pieces)

        # Provem de moure cada peça en totes les direccions
        for piece_id, (px, py) in enumerate(current_state):
            piece_shape = pieces[piece_id]

            for dx, dy, direction in moves:
                if is_valid_move(piece_id, px, py, dx, dy, piece_shape, mat, W, H):
                    # Generem el nou estat canviant només la coordenada d'aquesta peça
                    new_state_list = list(current_state)
                    new_state_list[piece_id] = (px + dx, py + dy)
                    new_state = tuple(new_state_list)

                    # Si és un estat nou, l'afegim al graf i a la cua
                    if new_state not in visited:
                        v_new = g.add_vertex()
                        vp_state[v_new] = json.dumps(new_state)
                        visited[new_state] = v_new
                        queue.append(new_state)
                    else:
                        v_new = visited[new_state]

                    # Creem l'aresta que connecta l'estat actual amb el nou
                    # Ens assegurem de no duplicar arestes si s'arriba per vies diferents (tot i que en aquest joc el graf sol ser simple)
                    if g.edge(v_current, v_new) is None:
                        e = g.add_edge(v_current, v_new)
                        ep_piece[e] = piece_id
                        ep_dir[e] = direction

    print(
        f"Graf completat: {g.num_vertices()} estats (vèrtexs) i {g.num_edges()} moviments (arestes)."
    )
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

    # Guardem el graf. Substituïm .json per .graphml
    out_filepath = filepath_str.replace(".json", ".graphml")
    if out_filepath == filepath_str:
        out_filepath += ".graphml"

    g.save(out_filepath)
    print(f"Graf guardat correctament a: {out_filepath}")


if __name__ == "__main__":
    main()
