import sys
import json
import graph_tool.all as gt
from graph import generate_graph
from solve import solve
from puzzle import Puzzle
from logic import Move
from pathlib import Path


def eval(puzzle: Puzzle, graph: gt.Graph, moves: list[Move]):
    """Assigna una evaluació al puzzle segons la seva estructure, el seu graf i la solució més curta"""
    return 5 * min(1, len(moves) / 15)


def main():
    if len(sys.argv) != 2:
        print("Ús: python src/eval.py <puzzle.json>")
        sys.exit(1)

    filepath = Path(sys.argv[1])

    try:
        puzzle = Puzzle.from_json(filepath.read_text())
    except Exception as e:
        print(f"Error en llegir el puzzle: {e}")
        sys.exit(1)

    g = generate_graph(puzzle)

    moves = solve(g, puzzle, "", False)
    print(eval(puzzle, g, moves))


if __name__ == "__main__":
    main()
