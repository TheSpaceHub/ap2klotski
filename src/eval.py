"""
Avaluador de puzzles de peces lliscants.

Calcula una puntuació de 0 a 5 a partir de quatre mètriques del graf d'estats:

    L = longitud de la solució òptima
    V = mida de l'espai d'estats (log10 de vèrtexs)
    A = nombre de punts d'articulació (estructura de "fases")
    R = ratio L / diàmetre del graf

score = 5 · (0.4·Ln + 0.2·Vn + 0.2·An + 0.2·Rn)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import graph_tool.all as gt

from puzzle import Puzzle
from graph import generate_graph
from solve import solve


# Caps de normalització: a partir d'aquí la mètrica satura a 1.
LENGTH_CAP = 50
LOG_STATES_CAP = 5.0  # 10^5 = 100 000 estats és el màxim "útil"
ARTICULATION_CAP = 5

# Pesos de cada component dins de la mitjana ponderada (sumen 1).
WEIGHTS = {"L": 0.4, "V": 0.2, "A": 0.2, "R": 0.2}


def _normalize_length(L: int) -> float:
    return min(L / LENGTH_CAP, 1.0)


def _normalize_states(V: int) -> float:
    if V <= 1:
        return 0.0
    return min(math.log10(V) / LOG_STATES_CAP, 1.0)


def _normalize_articulation(A: int) -> float:
    return min(A / ARTICULATION_CAP, 1.0)


def _normalize_ratio(R: float) -> float:
    return min(max(R, 0.0), 1.0)


def _graph_metrics(graph: gt.Graph) -> tuple[int, int, int]:
    """
    Retorna (V, A, diameter) tractant el graf com a no-dirigit
    (cada moviment és reversible).
    """
    was_directed = graph.is_directed()
    graph.set_directed(False)
    try:
        V = graph.num_vertices()
        _, articulation, _ = gt.label_biconnected_components(graph)
        # articulation.a és un array uint8: fem la suma en int per evitar overflow.
        A = int(articulation.a.astype(int).sum())
        diameter = int(gt.pseudo_diameter(graph)[0])
    finally:
        graph.set_directed(was_directed)
    return V, A, diameter


def evaluate(
    puzzle: Puzzle, graph: gt.Graph, solution_length: int
) -> tuple[float, dict]:
    """
    Avalua un puzzle a partir del seu graf i la longitud de la solució òptima.
    Retorna (score 0-5, desglossament de mètriques).

    El graf NO es modifica.
    """
    del puzzle  # signatura per simetria; les mètriques actuals no el necessiten
    L = solution_length
    V, A, diameter = _graph_metrics(graph)
    R = L / diameter if diameter > 0 else 0.0

    Ln = _normalize_length(L)
    Vn = _normalize_states(V)
    An = _normalize_articulation(A)
    Rn = _normalize_ratio(R)

    score = 5.0 * (
        WEIGHTS["L"] * Ln
        + WEIGHTS["V"] * Vn
        + WEIGHTS["A"] * An
        + WEIGHTS["R"] * Rn
    )

    metrics = {
        "L": L, "V": V, "A": A, "diameter": diameter, "R": round(R, 3),
        "L_n": round(Ln, 3), "V_n": round(Vn, 3),
        "A_n": round(An, 3), "R_n": round(Rn, 3),
        "score": round(score, 3),
    }
    return score, metrics


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

    # solve() modifica el graf afegint un node "win" — fem una còpia
    # per no embrutar el graf abans d'evaluar-lo.
    g_for_solve = gt.Graph(g, prune=False)
    moves = solve(g_for_solve, puzzle, "", export=False)

    score, metrics = evaluate(puzzle, g, len(moves))

    print(f"\nScore: {score:.2f} / 5.0")
    print("Desglossament:")
    for k in ("L", "V", "A", "diameter", "R", "L_n", "V_n", "A_n", "R_n"):
        print(f"  {k:<10} = {metrics[k]}")


if __name__ == "__main__":
    main()
