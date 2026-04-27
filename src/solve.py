import sys
import graph_tool.all as gt
from puzzle import Puzzle, State
from logic import Move
import json
from pathlib import Path

Coord = tuple[int, int]
FastState = list[Coord]


def is_win(node: FastState, goals: tuple[tuple[int, Coord], ...]) -> bool:
    """Determina si l'estat (node) és guanyador"""
    for g in goals:
        if node[g[0]][0] != g[1][0] or node[g[0]][1] != g[1][1]:
            print(node)
            print(node[g[0]][0])
            print(g[1][0])
            print(node[g[0]][1])
            print(g[1][1])
            return False
    return True


def extract_moves(g: gt.Graph, e_path) -> list[Move]:
    """
    Donat el graf i el camí d'arestes retorna els moviments fets
    """

    # Access the property maps bound to the graph
    ep_piece = g.edge_properties["piece"]
    ep_dir = g.edge_properties["dir"]

    solution_moves: list[Move] = []

    for e in e_path:

        piece_id = int(ep_piece[e])
        direction = str(ep_dir[e])

        solution_moves.append((piece_id, direction, 1))

    return solution_moves


def moves_to_json(moves: list[Move], output_file: str) -> None:
    """Donada la llista de moviments, crea un .json amb els moviments"""
    with open(output_file, "w") as f:
        json.dump(moves, f)


def solve(graph: gt.Graph, puzzle: Puzzle, output_file: str) -> None:
    
    """Donat un graf de graph-tool i el puzzle, realitza un bfs per resoldre el puzzle i guarda el json a output_file"""
    
    import time
    
    
    winning_states: list[FastState] = []
    for node in graph.vertices():
        if is_win(graph.vp["state"][node], puzzle.get_goals()):
            winning_states.append(node)
            print("WIN")
            exit()

    print(len(winning_states))

    # we create a "won" state
    win_node = graph.add_vertex()
    for node in winning_states:
        graph.add_edge(win_node, node)

    start_node = graph.vertex(0)

    # run graph-tool bfs
    _, full_edge_path = gt.shortest_path(graph, start_node, win_node)

    edge_path = full_edge_path[:-1]  # remove win node
    print(len(edge_path))

    moves = extract_moves(graph, edge_path)

    moves_to_json(moves, output_file)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        graph_file = sys.argv[1]
        puzzle_file = Path(sys.argv[2])
        puzzle = Puzzle.from_json(puzzle_file.read_text())
        graph = gt.load_graph(graph_file)
        solve(graph, puzzle, str(puzzle_file)[:-5] + "_moves.json")
    else:
        print("Usage: solve.py <graph_file> <puzzle_file>")
        print(sys.argv)
