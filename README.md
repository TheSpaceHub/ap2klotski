# Klotski! Entrega AP2 (Primavera 2026)

Guia ràpida per al corrector. Codi propi a `src/`, puzzles generats
a `puzzles/`.

## Entorn

```sh
pixi install
pixi shell
```

## Eines pròpies (`src/`)

| Fitxer | Ús |
|---|---|
| `download.py` | `python src/download.py [ID]` (sense ID llista els 100 millors; amb ID el desa a `puzzles/`) |
| `graph.py` | `python src/graph.py puzzles/<f>.json` construeix el graf d'estats i el desa en `.graphml` |
| `solve.py` | `python src/solve.py puzzles/<f>.json` escriu `<f>.sol.json` amb la seqüència `[[piece, "N\|E\|S\|W"], ...]` |
| `eval.py` | `python src/eval.py puzzles/<f>.json` retorna una nota de 0 a 5 |
| `generate.py` | `python src/generate.py [--out puzzles/nou.json]` |
| `rate.py` | `python src/rate.py <ID> <0..5>` (requereix `token.txt`) |

Fitxers originals no modificats: `play.py`, `image.py`, `movie.py`,
`3D_view.py`, `puzzle.py`, `logic.py`.

## Decisions clau

- `graph.py`: simulació sobre matriu (`build_state_matrix`,
  `is_valid_move`) i DFS complet. Les arestes guarden les
  propietats `piece` i `dir`.
- `solve.py`: graf no-dirigit, camí més curt fins a un node
  objectiu, reconstrucció de moviments via les propietats.
- `eval.py`: `score = 5·(0.4·Ln + 0.2·Vn + 0.2·An + 0.2·Rn)`, on
  `L` és la longitud òptima, `V` el `log10` de vèrtexs, `A` els
  punts d'articulació (mesura de fases) i `R = L/diàmetre`. Caps
  de normalització: `LENGTH_CAP=50`, `LOG_STATES_CAP=5`,
  `ARTICULATION_CAP=5`.
- `generate.py`: peça objectiu 2×2 a l'atzar, farciment amb
  poliominós de mida <=4, validació de canonicalització i BFS amb
  `MAX_DEPTH=100` exigint `MIN_MOVES=10`. Reintenta fins a trobar
  un puzzle vàlid.
- `download.py` i `rate.py`: `urllib.request`, token llegit de
  `token.txt`, SSL relaxat per certificats de macOS.

## Puzzles a `puzzles/`

- `nou_puzzle_01.json`: generat amb `generate.py`.
- `0093825c…json`, `2608f1dc…json`: descarregats del repositori.

## Notes

- `token.txt` s'inclou a l'entrega.
- La carpeta `.pixi/` (1.3 GB) **no** s'inclou al ZIP.
