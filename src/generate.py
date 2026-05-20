"""
Generador de puzzles de peces lliscants.

Estratègia:
  1. Col·loca una peça objectiu 2x2 a l'atzar (diferent de la posició final).
  2. Omple la resta del tauler amb peces petites (1x1, 1x2, 2x1).
  3. Construeix un Puzzle (que valida la canonicalització).
  4. Fa un BFS curt des de l'estat inicial fins a trobar un estat-objectiu;
     descarta el puzzle si no és assolible o si la solució mínima és massa curta.
  5. Si no és vàlid, ho torna a intentar.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import random
import sys
from collections import deque
from functools import lru_cache
from pathlib import Path

from puzzle import Coord, Piece, Puzzle, State
from graph import build_state_matrix, create_base_matrix, generate_graph, is_valid_move


# Configuració per defecte
DEFAULT_W = 4
DEFAULT_H = 5
DEFAULT_MAX_ATTEMPTS = 500
# Si omplim el tauler del tot, la peça objectiu no es pot moure i res és soluble.
# Deixem unes quantes cel·les buides per donar marge als moviments.
DEFAULT_EMPTY_CELLS = 4
FILL_RETRIES = 400  # Intents per col·locar peces fins a la densitat objectiu

# Filtres de qualitat
DEFAULT_MIN_MOVES = 10   # Rebutja puzzles que es resolen en menys passos
DEFAULT_MAX_DEPTH = 100  # Tall superior del BFS per no quedar atrapat

# Mida màxima de poliominó (la spec permet fins a 4).
MAX_POLY_SIZE = 4

# La peça 2x2 es reserva per la peça objectiu, no s'utilitza com a filler.
TARGET_SHAPE: tuple[Coord, ...] = ((0, 0), (0, 1), (1, 0), (1, 1))

# Vectors de moviment (dx, dy) en l'ordre N, S, E, W
MOVE_DELTAS: list[tuple[int, int]] = [(0, -1), (0, 1), (1, 0), (-1, 0)]


def _normalize(cells: set[Coord]) -> tuple[Coord, ...]:
    """Trasllada el conjunt a min_x = min_y = 0 i ordena lexicogràficament."""
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    return tuple(sorted((x - min_x, y - min_y) for x, y in cells))


@lru_cache(maxsize=None)
def all_polyominoes(n: int) -> tuple[tuple[Coord, ...], ...]:
    """
    Tots els poliominós fixos (rotacions i miralls comptats per separat)
    de mida n, en forma canònica normalitzada.

    Fixed polyominoes: 1, 2, 6, 19, ... per n = 1, 2, 3, 4, ...
    """
    if n <= 0:
        return ()
    if n == 1:
        return (((0, 0),),)

    seen: set[tuple[Coord, ...]] = set()
    for shape in all_polyominoes(n - 1):
        cells = set(shape)
        for x, y in shape:
            for dx, dy in MOVE_DELTAS:
                cell = (x + dx, y + dy)
                if cell in cells:
                    continue
                seen.add(_normalize(cells | {cell}))
    return tuple(seen)


def filler_shapes(max_size: int = MAX_POLY_SIZE) -> list[tuple[Coord, ...]]:
    """
    Totes les formes disponibles per omplir el tauler: poliominós fins a
    `max_size` cel·les, excloent la peça objectiu (2x2).
    """
    shapes: list[tuple[Coord, ...]] = []
    for n in range(1, max_size + 1):
        for shape in all_polyominoes(n):
            if shape != TARGET_SHAPE:
                shapes.append(shape)
    return shapes


def _shape_bbox(shape: tuple[Coord, ...]) -> tuple[int, int]:
    """Mida del rectangle envolvent de la forma (max_x + 1, max_y + 1)."""
    max_x = max(x for x, _ in shape)
    max_y = max(y for _, y in shape)
    return max_x + 1, max_y + 1


def goal_position(W: int, H: int) -> Coord:
    """Posició final de la peça objectiu 2x2: centrada a la fila inferior."""
    return (W // 2 - 1, H - 2)


def can_place(
    board: list[list[int]],
    shape: list[Coord],
    px: int,
    py: int,
    W: int,
    H: int,
) -> bool:
    """Cert si la peça hi entra sense sortir ni solapar-se."""
    for rx, ry in shape:
        nx, ny = px + rx, py + ry
        if nx < 0 or nx >= W or ny < 0 or ny >= H:
            return False
        if board[ny][nx] != -1:
            return False
    return True


def random_layout(W: int, H: int, empty_cells: int = DEFAULT_EMPTY_CELLS) -> Puzzle | None:
    """
    Construeix un Puzzle aleatori (canònic, vàlid estructuralment).
    Retorna None si no s'ha pogut formar res coherent.
    """
    # 0. El tauler ha de ser prou gran per acollir la peça 2x2 i el seu goal.
    target_shape = list(TARGET_SHAPE)
    gx_max, gy_max = W - 2, H - 2
    if gx_max < 0 or gy_max < 0:
        return None

    goal = goal_position(W, H)
    if not (0 <= goal[0] <= gx_max and 0 <= goal[1] <= gy_max):
        return None

    # 1. Col·loca la peça objectiu a una posició diferent de la del goal.
    board = [[-1] * W for _ in range(H)]
    for _ in range(50):
        gx = random.randint(0, gx_max)
        gy = random.randint(0, gy_max)
        if (gx, gy) != goal:
            break
    else:
        return None

    for rx, ry in target_shape:
        board[gy + ry][gx + rx] = 0

    # entries: llista de (Piece, posició_inicial, és_objectiu).
    entries: list[tuple[Piece, Coord, bool]] = [
        (Piece.normalized(target_shape), (gx, gy), True),
    ]

    # 2. Omple la resta del tauler amb tota la varietat de poliominós ≤ 4.
    #    Pre-calculem el bbox per restringir random a posicions que entren al tauler.
    shapes = filler_shapes()
    bboxes = [_shape_bbox(s) for s in shapes]

    empty = W * H - len(target_shape)
    for _ in range(FILL_RETRIES):
        if empty <= empty_cells:
            break
        idx = random.randrange(len(shapes))
        shape = shapes[idx]
        bw, bh = bboxes[idx]
        # Saltem formes que ni tan sols hi caben (per a taulers petits)
        if bw > W or bh > H:
            continue
        if empty - len(shape) < empty_cells:
            continue  # No volem passar-nos de llarg
        px = random.randint(0, W - bw)
        py = random.randint(0, H - bh)
        if not can_place(board, list(shape), px, py, W, H):
            continue
        piece_id = len(entries)
        for rx, ry in shape:
            board[py + ry][px + rx] = piece_id
        entries.append((Piece(*shape), (px, py), False))
        empty -= len(shape)

    # 3. Ordena canònicament per (forma, posició) i construeix el Puzzle.
    entries.sort(key=lambda e: (e[0], e[1]))
    pieces = tuple(e[0] for e in entries)
    start = State(tuple(e[1] for e in entries))
    goals = tuple(sorted((i, goal) for i, e in enumerate(entries) if e[2]))

    try:
        return Puzzle(
            W=W, H=H, walls=(), pieces=pieces, start=start, goals=goals,
        )
    except ValueError:
        return None


def is_trivial(puzzle: Puzzle) -> bool:
    """Cert si l'estat inicial ja satisfà tots els objectius."""
    return all(puzzle.start.positions[i] == pos for i, pos in puzzle.goals)


def shortest_solution(puzzle: Puzzle, max_depth: int = DEFAULT_MAX_DEPTH) -> int | None:
    """
    BFS d'un sol pas des de l'estat inicial fins al primer estat que satisfà
    els objectius. Retorna la distància mínima en moviments, o None si el goal
    no és assolible (o cau més enllà de max_depth).

    Reutilitza les primitives de moviment de graph.py però sense construir
    el gt.Graph complet — molt més barat quan només volem saber la distància.
    """
    W, H = puzzle.W, puzzle.H
    pieces = [p.get_coords() for p in puzzle.get_pieces()]
    walls = puzzle.get_walls()
    goals = puzzle.goals
    base_matrix = create_base_matrix(W, H, walls)

    start = tuple(puzzle.start.positions)
    if all(start[i] == pos for i, pos in goals):
        return 0

    visited: set[tuple[Coord, ...]] = {start}
    frontier: deque[tuple[tuple[Coord, ...], int]] = deque([(start, 0)])

    while frontier:
        current, depth = frontier.popleft()
        if depth >= max_depth:
            continue

        mat = build_state_matrix(current, base_matrix, pieces, W)
        for piece_id, (px, py) in enumerate(current):
            shape = pieces[piece_id]
            for dx, dy in MOVE_DELTAS:
                if not is_valid_move(piece_id, px, py, dx, dy, shape, mat, W, H):
                    continue
                new_positions = list(current)
                new_positions[piece_id] = (px + dx, py + dy)
                new_state = tuple(new_positions)
                if new_state in visited:
                    continue
                if all(new_state[i] == pos for i, pos in goals):
                    return depth + 1
                visited.add(new_state)
                frontier.append((new_state, depth + 1))

    return None


def _try_one_candidate(
    W: int, H: int,
    min_moves: int, max_depth: int,
    max_attempts: int,
) -> tuple[Puzzle, int] | None:
    """Genera un puzzle vàlid i no trivial. Retorna (puzzle, distancia) o None."""
    for _ in range(max_attempts):
        puzzle = random_layout(W, H)
        if puzzle is None or is_trivial(puzzle):
            continue
        depth = shortest_solution(puzzle, max_depth=max_depth)
        if depth is None or depth < min_moves:
            continue
        return puzzle, depth
    return None


def generate_random_puzzle(
    W: int = DEFAULT_W,
    H: int = DEFAULT_H,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_moves: int = DEFAULT_MIN_MOVES,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Puzzle:
    """
    Genera un puzzle aleatori, canònic i soluble amb almenys `min_moves`
    moviments en la solució òptima.
    """
    result = _try_one_candidate(W, H, min_moves, max_depth, max_attempts)
    if result is None:
        raise RuntimeError(
            f"No s'ha pogut generar un puzzle vàlid en {max_attempts} intents."
        )
    puzzle, depth = result
    print(f"Puzzle vàlid trobat (solució mínima: {depth} moviments).")
    return puzzle


def generate_batch(
    N: int, K: int, out_dir: str,
    W: int = DEFAULT_W,
    H: int = DEFAULT_H,
    min_moves: int = DEFAULT_MIN_MOVES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    attempts_per_candidate: int = 100,
) -> list[tuple[float, Puzzle, dict]]:
    """
    Genera N candidats solubles, construeix el graf complet de cada un,
    els puntua amb eval.evaluate i guarda els K millors a out_dir.

    Retorna la llista ordenada per score descendent.
    """
    # Importació tardana per evitar cicles d'importació amb eval.py.
    from eval import evaluate

    os.makedirs(out_dir, exist_ok=True)
    candidates: list[tuple[float, Puzzle, dict]] = []

    print(f"Generant {N} candidats (W={W}, H={H}, min_moves={min_moves})...")
    for i in range(1, N + 1):
        result = _try_one_candidate(
            W, H, min_moves, max_depth, attempts_per_candidate
        )
        if result is None:
            print(f"  [{i}/{N}] no s'ha trobat candidat soluble; saltat.")
            continue
        puzzle, depth = result

        # Construïm el graf complet (és la part cara) i puntuem.
        with contextlib.redirect_stdout(io.StringIO()):
            g = generate_graph(puzzle)
        score, metrics = evaluate(puzzle, g, depth)
        candidates.append((score, puzzle, metrics))
        print(
            f"  [{i}/{N}] L={metrics['L']:>3}  V={metrics['V']:>6}  "
            f"A={metrics['A']:>3}  R={metrics['R']:.2f}  → score={score:.2f}"
        )

    candidates.sort(key=lambda c: -c[0])
    top = candidates[:K]

    print(f"\nGuardant els {len(top)} millors a {out_dir}...")
    for rank, (score, puzzle, _metrics) in enumerate(top, start=1):
        h = puzzle.hash()[:8]
        fname = f"rank{rank:02d}-score-{score:.2f}-{h}.json"
        Path(out_dir, fname).write_text(puzzle.to_json(indent=2))
        print(f"  {fname}")

    return top


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generador de puzzles de peces lliscants."
    )
    p.add_argument(
        "output", nargs="?",
        help="Path de sortida (mode únic: un sol puzzle).",
    )
    p.add_argument("--batch", type=int, metavar="N",
                   help="Genera N candidats i guarda els millors (mode top-K).")
    p.add_argument("--keep", type=int, default=5, metavar="K",
                   help="Quants candidats conservar al mode batch (per defecte 5).")
    p.add_argument("--out-dir", metavar="DIR",
                   help="Directori on guardar els puzzles del mode batch.")
    p.add_argument("-W", type=int, default=DEFAULT_W,
                   help=f"Amplada del tauler (per defecte {DEFAULT_W}).")
    p.add_argument("-H", type=int, default=DEFAULT_H,
                   help=f"Alçada del tauler (per defecte {DEFAULT_H}).")
    p.add_argument("--min-moves", type=int, default=DEFAULT_MIN_MOVES,
                   help=f"Mínim de moviments en la solució òptima "
                        f"(per defecte {DEFAULT_MIN_MOVES}).")
    p.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
                   help=f"Profunditat màxima del BFS de verificació "
                        f"(per defecte {DEFAULT_MAX_DEPTH}).")
    p.add_argument("--seed", type=int,
                   help="Llavor del generador aleatori per reproduïbilitat.")
    return p


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.batch:
        if not args.out_dir:
            parser.error("--batch requereix --out-dir")
        generate_batch(
            N=args.batch, K=args.keep, out_dir=args.out_dir,
            W=args.W, H=args.H,
            min_moves=args.min_moves, max_depth=args.max_depth,
        )
        return

    if not args.output:
        parser.error("cal donar un path de sortida o usar --batch amb --out-dir")

    puzzle = generate_random_puzzle(
        W=args.W, H=args.H,
        min_moves=args.min_moves, max_depth=args.max_depth,
    )

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    Path(args.output).write_text(puzzle.to_json(indent=2))
    print(f"Puzzle generat correctament: {args.output}")


if __name__ == "__main__":
    main()
