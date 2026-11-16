"""
ColdFish v4 — a working Python chess engine (UCI).
Requires: pip install python-chess

Test:
    echo -e "uci\nisready\nposition startpos moves e2e4 e7e5\ngo depth 4\nquit" | python coldfish.py

Design invariants (do not break these):
  1. eval_stm(board) returns score from SIDE-TO-MOVE's POV. Always.
  2. negamax does exactly ONE negation: score = -negamax(...).
  3. Mate is -MATE + ply when the side to move is mated.
  4. Move ordering = captures first (MVV-LVA), then promotions, then quiet.
  5. Quiescence resolves captures so depth-0 doesn't hang pieces.
"""

import sys
import chess
import chess.polyglot
import os

def resource_path(relative):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# ============================================================
# CONSTANTS
# ============================================================



MATE = 100_000
INF  = 1_000_000

VAL = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   0,      # king not counted in material
}

# --- Piece-Square Tables (Sunfish-style, white POV) ---
# Authored from white's perspective: rank1 = first row, a1 = index 0.
# For black we mirror the square with chess.square_mirror().

PST_PAWN = [
     0,   0,   0,   0,   0,   0,   0,   0,
     0,  0,  0,  0,  0,  0,  0,   0,   0,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  80,  80,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]

PST_KNIGHT = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -30,  -10,  10,  15,  15,  10, -10, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
]

PST_BISHOP = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
]

PST_ROOK = [
    -20,   5,   0,   0,   0,   0,  5,   -20,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0,
]

PST_QUEEN = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,   5,   5,   5,   0, -10,
    -5,   0,   5,   5,   5,   5,   0,  -5,
     0,   0,   5,   5,   5,   5,   0,  -5,
   -10,   5,   5,   5,   5,   5,   0, -10,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
]

PST_KING_MID = [
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -10, -20, -20, -20, -20, -20, -20, -10,
    20,  20,   0,   0,   0,   0,  20,  20,
    20,  30,  10,   0,   0,  10,  30,  20,
]

PST_KING_END = [
   -50, -40, -30, -20, -20, -30, -40, -50,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -50, -30, -30, -30, -30, -30, -30, -50,
]

PST = {
    chess.PAWN:   PST_PAWN,
    chess.KNIGHT: PST_KNIGHT,
    chess.BISHOP: PST_BISHOP,
    chess.ROOK:   PST_ROOK,
    chess.QUEEN:  PST_QUEEN,
}

PASSED_PAWN_BONUS = [0, 5, 10, 20, 35, 60, 100, 0]   # by relative rank
DOUBLED_PAWN_PENALTY   = -10
ISOLATED_PAWN_PENALTY  = -15
BISHOP_PAIR_BONUS      = 30
KING_SHIELD_BONUS      = 10

# ============================================================
# HELPERS
# ============================================================


def pst_value(piece_type, color, square):
    """Return PST bonus from the piece owner's perspective."""
    if piece_type == chess.KING:
        # simple taper: endgame table if few material left
        pass  # handled below with phase
    table = PST[piece_type]
    if color == chess.WHITE:
        return table[square]
    else:
        return table[chess.square_mirror(square)]


def pst_value_king(color, square, endgame):
    table = PST_KING_END if endgame else PST_KING_MID
    if color == chess.WHITE:
        return table[square]
    else:
        return table[chess.square_mirror(square)]


def is_endgame(board):
    """Rough: endgame when total non-pawn material is low."""
    total = 0
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.piece_type not in (chess.PAWN, chess.KING):
            total += VAL[p.piece_type]
    return total < 2000  # ~ two rooks + minor; tune as needed


# ============================================================
# EVALUATION (always WHITE-relative)
# ============================================================

def evaluate_white(board):
    if board.is_checkmate():
        return -MATE if board.turn == chess.WHITE else MATE
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    endgame = is_endgame(board)
    score = 0

    # --- Material + PST ---
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if not p:
            continue
        sign = 1 if p.color == chess.WHITE else -1
        score += sign * VAL[p.piece_type]
        if p.piece_type == chess.KING:
            score += sign * pst_value_king(p.color, sq, endgame)
        else:
            score += sign * pst_value(p.piece_type, p.color, sq)

    # --- Pawn structure ---
    score += eval_pawns(board)

    # --- Bishop pair ---
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        if len(board.pieces(chess.BISHOP, color)) >= 2:
            score += sign * BISHOP_PAIR_BONUS

    # --- King shield (only meaningful in middlegame) ---
    if not endgame:
        score += king_shield(board, chess.WHITE)
        score -= king_shield(board, chess.BLACK)

    return score


def eval_pawns(board):
    """White-relative: passed, doubled, isolated."""
    from collections import Counter
    score = 0
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        own = board.pieces(chess.PAWN, color)
        enemy = board.pieces(chess.PAWN, not color)

        files = [chess.square_file(sq) for sq in own]
        counts = Counter(files)

        for sq in own:
            f = chess.square_file(sq)
            r = chess.square_rank(sq)

            if counts[f] > 1:
                score += sign * DOUBLED_PAWN_PENALTY

            if not any(ff in counts for ff in (f - 1, f + 1)):
                score += sign * ISOLATED_PAWN_PENALTY

            rel_r = r if color == chess.WHITE else 7 - r
            passed = True
            rng = range(r + 1, 8) if color == chess.WHITE else range(0, r)
            for ef in (f - 1, f, f + 1):
                if not (0 <= ef <= 7):
                    continue
                for er in rng:
                    if chess.square(ef, er) in enemy:
                        passed = False
                        break
                if not passed:
                    break
            if passed:
                score += sign * PASSED_PAWN_BONUS[rel_r]

    return score


def king_shield(board, color):
    king_sq = board.king(color)
    if king_sq is None:
        return 0
    kf = chess.square_file(king_sq)
    kr = chess.square_rank(king_sq)
    shield_rank = kr + 1 if color == chess.WHITE else kr - 1
    if not (0 <= shield_rank <= 7):
        return 0
    bonus = 0
    for df in (-1, 0, 1):
        f = kf + df
        if 0 <= f <= 7:
            pawn = chess.Piece(chess.PAWN, color)
            if board.piece_at(chess.square(f, shield_rank)) == pawn:
                bonus += KING_SHIELD_BONUS
    return bonus


def eval_stm(board):
    """Score from side-to-move's POV — the ONLY form negamax sees."""
    raw = evaluate_white(board)
    return raw if board.turn == chess.WHITE else -raw


# ============================================================
# MOVE ORDERING (MVV-LVA + promotions)
# ============================================================

def order_moves(board, moves=None):
    if moves is None:
        moves = board.legal_moves

    def key(move):
        s = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                s += 1000 + 10 * VAL[victim.piece_type] - VAL[attacker.piece_type]
            else:
                s += 1000 + 10 * VAL[chess.PAWN]
        if move.promotion:
            s += 900 + VAL.get(move.promotion, 0)
        return -s

    return sorted(moves, key=key)


# ============================================================
# SEARCH
# ============================================================

def quiescence(board, alpha, beta, ply):
    """Captures-only search at depth 0 to avoid horizon effect."""
    stand = eval_stm(board)
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand

    captures = [m for m in board.legal_moves if board.is_capture(m)]
    for move in order_moves(board, captures):
        board.push(move)
        score = -quiescence(board, -beta, -alpha, ply + 1)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def negamax(board, depth, alpha, beta, ply):
    """Returns (score, best_move), score from STM POV."""
    if board.is_checkmate():
        return -MATE + ply, None
    if board.is_stalemate() or board.is_insufficient_material():
        return 0, None

    if depth == 0:
        return quiescence(board, alpha, beta, ply), None

    best_score = -INF
    best_move  = None

    for move in order_moves(board):
        board.push(move)
        score, _ = negamax(board, depth - 1, -beta, -alpha, ply + 1)
        score = -score                                   # ← ONE negation
        board.pop()

        if score > best_score:
            best_score = score
            best_move  = move
        if score > alpha:
            alpha = score
        if alpha >= beta:
            break

    return best_score, best_move




def get_book_move_from_bin(board, book_path="opening.bin"):
    """Busca un movimiento en un archivo .bin de Polyglot."""
    try:
        with chess.polyglot.open_reader(book_path) as reader:
            # weighted_choice selecciona un movimiento basado en su peso (frecuencia en partidas)
            # o puedes usar reader.find(board) si prefieres siempre el principal.
            
            entry = reader.weighted_choice(board)
            if entry:
                print(f"info string book move: {entry.move}", file=sys.stderr)  # ← agregar
                return entry.move
    except FileNotFoundError:
        # Si el archivo no existe o no se encuentra en la ruta, el motor sigue calculando normal
        pass
    except IndexError:
        # Se lanza IndexError si la posición actual no está en el libro de aperturas
        pass
    
    return None

def search_root(board, depth):
    """Top-level search. Returns (score, best_move), STM POV."""
    if not any(board.legal_moves):
        return (0, None) if not board.is_check() else (-MATE, None)

    # --- HOOK DE APERTURAS CON ARCHIVO .BIN ---
    # Reemplaza "openings.bin" por la ruta real de tu archivo .bin
    book_move = get_book_move_from_bin(board, resource_path("openings.bin"))
    if book_move and book_move in board.legal_moves:
        return 0, book_move
    # ------------------------------------------

    best_score = -INF
    best_move  = None
    alpha, beta = -INF, INF

    for move in order_moves(board):
        board.push(move)
        score, _ = negamax(board, depth - 1, -beta, -alpha, ply=1)
        score = -score
        board.pop()

        if score > best_score:
            best_score = score
            best_move  = move
        if score > alpha:
            alpha = score

    if best_move is None:
        legal = list(board.legal_moves)
        if legal:
            best_move = legal[0]

    return best_score, best_move

# ============================================================
# UCI LOOP
# ============================================================

def uci_loop():
    board = chess.Board()

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        if line == "uci":
            print("id name ColdFish v4")
            print("id author Juan")
            print("uciok")

        elif line == "isready":
            print("readyok")

        elif line == "ucinewgame":
            board.reset()

        elif line.startswith("position"):
            tokens = line.split()
            if "fen" in tokens:
                fi = tokens.index("fen")
                board.set_fen(" ".join(tokens[fi + 1: fi + 7]))
            else:
                board.reset()
            if "moves" in tokens:
                mi = tokens.index("moves") + 1
                for mv_str in tokens[mi:]:
                    try:
                        board.push(chess.Move.from_uci(mv_str))
                    except ValueError:
                        break

        elif line.startswith("go"):
            tokens = line.split()
            depth = 3
            if "depth" in tokens:
                try:
                    depth = int(tokens[tokens.index("depth") + 1])
                except (IndexError, ValueError):
                    pass
            depth = max(1, min(depth, 6))

            _, best = search_root(board, depth)
            print(f"bestmove {best.uci()}" if best else "bestmove 0000")

        elif line == "quit":
            break

        sys.stdout.flush()


if __name__ == "__main__":
    uci_loop()


