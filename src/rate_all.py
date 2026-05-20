import urllib.request
import json
import sys
import os
import ssl
import graph_tool.all as gt
from pathlib import Path

from eval import evaluate
from puzzle import Puzzle
from graph import generate_graph
from solve import solve
from rate import rate_puzzle

ssl._create_default_https_context = ssl._create_unverified_context

url_base = "https://klotski.pauek.dev/api/puzzles"


def get_puzzle_ids():
    "Obté la llista dels 100 puzzles millor valorats del repositori"
    with urllib.request.urlopen(url_base) as response:
        return json.loads(response.read().decode())


def load_puzzle_by_id(puzzle_id: str) -> Puzzle:
    "Loads a puzzle object"
    url = f"{url_base}/{puzzle_id}"

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    return Puzzle.from_json(json.dumps(data["puzzle"]))


def main():
    puzzle_ids = get_puzzle_ids()

    for id in puzzle_ids:
        if id == "c2ada9aa25284e001614f9a06c5677ea7b0c2144abe8fe0df693ce44aba6f3b4":
            continue
        print(f"Evaluant puzzle amb id {id}")
        puzzle = load_puzzle_by_id(id)

        g = generate_graph(puzzle)

        g_for_solve = gt.Graph(g, prune=False)
        moves = solve(g_for_solve, puzzle, "", export=False)

        score, _ = evaluate(puzzle, g, len(moves))
        rate_puzzle(id, score)


if __name__ == "__main__":
    main()
