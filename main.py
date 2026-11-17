import os
import sys
from collections import Counter

import chess
import chess.polyglot


def ruta_recurso(relativa):
    """Devuelve la ruta absoluta de un recurso, dentro o fuera de PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativa)


# ============================================================
# CONSTANTES
# ============================================================

MATE = 100_000
INF = 1_000_000

# El rey vale 0 porque nunca se captura; su posición se evalúa con las PST.
VALOR_PIEZA = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Tablas de casillas indexadas con a1 = 0 desde el punto de vista de las blancas.
# Para las negras se espeja la casilla con chess.square_mirror().

PST_PEON = [
     0,   0,   0,   0,   0,   0,   0,   0,
     0,   0,   0,   0,   0,   0,   0,   0,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  80,  80,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]

PST_CABALLO = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -30, -10,  10,  15,  15,  10, -10, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
]

PST_ALFIL = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
]

PST_TORRE = [
     0,   5,   0,   0,   0,   0,   5,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0,
]

PST_DAMA = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,   5,   5,   5,   0, -10,
    -5,   0,   5,   5,   5,   5,   0,  -5,
     0,   0,   5,   5,   5,   5,   0,  -5,
   -10,   5,   5,   5,   5,   5,   0, -10,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
]

PST_REY_MEDIO = [
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -10, -20, -20, -20, -20, -20, -20, -10,
    20,  20,   0,   0,   0,   0,  20,  20,
    20,  30,  10,   0,   0,  10,  30,  20,
]

PST_REY_FINAL = [
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
    chess.PAWN: PST_PEON,
    chess.KNIGHT: PST_CABALLO,
    chess.BISHOP: PST_ALFIL,
    chess.ROOK: PST_TORRE,
    chess.QUEEN: PST_DAMA,
}

# Verifica al importar que ninguna tabla quedó mal armada (8 filas de 8).
for _tabla in (*PST.values(), PST_REY_MEDIO, PST_REY_FINAL):
    if len(_tabla) != 64:
        raise ValueError(f"Tabla PST con {len(_tabla)} entradas, se esperaban 64")

# Indexado por fila relativa al bando del peón.
BONO_PEON_PASADO = [0, 5, 10, 20, 35, 60, 100, 0]
PENALIZACION_PEON_DOBLADO = -10
PENALIZACION_PEON_AISLADO = -15
BONO_PAR_ALFILES = 30
BONO_ESCUDO_REY = 10


# ============================================================
# AYUDANTES
# ============================================================

def valor_pst(tipo_pieza, color, casilla, final):
    """Devuelve el valor posicional de la pieza desde la perspectiva de su dueño."""
    if tipo_pieza == chess.KING:
        tabla = PST_REY_FINAL if final else PST_REY_MEDIO
    else:
        tabla = PST[tipo_pieza]
    if color == chess.WHITE:
        return tabla[casilla]
    return tabla[chess.square_mirror(casilla)]


def es_final(tablero):
    """Indica si queda poco material no peón; el umbral de 2000 equivale a dos torres y una menor."""
    total = 0
    for pieza in tablero.piece_map().values():
        if pieza.piece_type not in (chess.PAWN, chess.KING):
            total += VALOR_PIEZA[pieza.piece_type]
    return total < 2000


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluar_blancas(tablero):
    """Evalúa la posición siempre desde la perspectiva de las blancas."""
    # Si hay jaque mate, perdió el bando que tiene el turno.
    if tablero.is_checkmate():
        return -MATE if tablero.turn == chess.WHITE else MATE
    if tablero.is_stalemate() or tablero.is_insufficient_material():
        return 0

    final = es_final(tablero)
    puntaje = 0

    for casilla, pieza in tablero.piece_map().items():
        signo = 1 if pieza.color == chess.WHITE else -1
        puntaje += signo * VALOR_PIEZA[pieza.piece_type]
        puntaje += signo * valor_pst(pieza.piece_type, pieza.color, casilla, final)

    puntaje += evaluar_peones(tablero)

    for color, signo in ((chess.WHITE, 1), (chess.BLACK, -1)):
        if len(tablero.pieces(chess.BISHOP, color)) >= 2:
            puntaje += signo * BONO_PAR_ALFILES

    # En el final el escudo de peones pierde importancia.
    if not final:
        puntaje += escudo_del_rey(tablero, chess.WHITE)
        puntaje -= escudo_del_rey(tablero, chess.BLACK)

    return puntaje


def evaluar_peones(tablero):
    """Suma peones pasados y resta doblados y aislados, desde las blancas."""
    puntaje = 0
    for color, signo in ((chess.WHITE, 1), (chess.BLACK, -1)):
        propios = tablero.pieces(chess.PAWN, color)
        rivales = tablero.pieces(chess.PAWN, not color)
        conteo = Counter(chess.square_file(casilla) for casilla in propios)

        for casilla in propios:
            col = chess.square_file(casilla)
            fila = chess.square_rank(casilla)

            if conteo[col] > 1:
                puntaje += signo * PENALIZACION_PEON_DOBLADO

            if not any(c in conteo for c in (col - 1, col + 1)):
                puntaje += signo * PENALIZACION_PEON_AISLADO

            fila_relativa = fila if color == chess.WHITE else 7 - fila
            filas_adelante = range(fila + 1, 8) if color == chess.WHITE else range(0, fila)

            # Un peón es pasado si ningún rival lo bloquea en su columna ni en las vecinas.
            pasado = True
            for col_vecina in (col - 1, col, col + 1):
                if not 0 <= col_vecina <= 7:
                    continue
                for fila_vecina in filas_adelante:
                    if chess.square(col_vecina, fila_vecina) in rivales:
                        pasado = False
                        break
                if not pasado:
                    break
            if pasado:
                puntaje += signo * BONO_PEON_PASADO[fila_relativa]

    return puntaje


def escudo_del_rey(tablero, color):
    """Bonifica los peones propios situados justo delante del rey."""
    casilla_rey = tablero.king(color)
    if casilla_rey is None:
        return 0
    col_rey = chess.square_file(casilla_rey)
    fila_rey = chess.square_rank(casilla_rey)
    fila_escudo = fila_rey + 1 if color == chess.WHITE else fila_rey - 1
    if not 0 <= fila_escudo <= 7:
        return 0

    peon = chess.Piece(chess.PAWN, color)
    bonificacion = 0
    for desplazamiento in (-1, 0, 1):
        col = col_rey + desplazamiento
        if 0 <= col <= 7 and tablero.piece_at(chess.square(col, fila_escudo)) == peon:
            bonificacion += BONO_ESCUDO_REY
    return bonificacion


def evaluar_lado_a_mover(tablero):
    """Devuelve el puntaje desde el lado a mover, la única forma que ve negamax."""
    bruto = evaluar_blancas(tablero)
    return bruto if tablero.turn == chess.WHITE else -bruto


# ============================================================
# ORDEN DE MOVIMIENTOS
# ============================================================

def ordenar_movimientos(tablero, movimientos=None):
    """Ordena capturas y promociones primero, con MVV-LVA (víctima valiosa, atacante barato)."""
    if movimientos is None:
        movimientos = tablero.legal_moves

    def clave(movimiento):
        puntaje = 0
        if tablero.is_capture(movimiento):
            victima = tablero.piece_at(movimiento.to_square)
            atacante = tablero.piece_at(movimiento.from_square)
            if victima and atacante:
                puntaje += 1000 + 10 * VALOR_PIEZA[victima.piece_type] - VALOR_PIEZA[atacante.piece_type]
            else:
                # Captura al paso: no hay pieza en la casilla destino.
                puntaje += 1000 + 10 * VALOR_PIEZA[chess.PAWN]
        if movimiento.promotion:
            puntaje += 900 + VALOR_PIEZA.get(movimiento.promotion, 0)
        return -puntaje

    return sorted(movimientos, key=clave)


# ============================================================
# BÚSQUEDA
# ============================================================

def busqueda_quiescente(tablero, alfa, beta):
    """Busca solo capturas al llegar a profundidad 0 para evitar el efecto horizonte."""
    estatico = evaluar_lado_a_mover(tablero)
    if estatico >= beta:
        return beta
    if estatico > alfa:
        alfa = estatico

    capturas = [m for m in tablero.legal_moves if tablero.is_capture(m)]
    for movimiento in ordenar_movimientos(tablero, capturas):
        tablero.push(movimiento)
        puntaje = -busqueda_quiescente(tablero, -beta, -alfa)
        tablero.pop()
        if puntaje >= beta:
            return beta
        if puntaje > alfa:
            alfa = puntaje
    return alfa


def negamax(tablero, profundidad, alfa, beta, distancia_raiz):
    """Devuelve (puntaje, mejor_movimiento) desde el lado a mover."""
    # Sumar la distancia a la raíz hace preferir los mates más cercanos.
    if tablero.is_checkmate():
        return -MATE + distancia_raiz, None
    if tablero.is_stalemate() or tablero.is_insufficient_material():
        return 0, None

    if profundidad == 0:
        return busqueda_quiescente(tablero, alfa, beta), None

    mejor_puntaje = -INF
    mejor_movimiento = None

    for movimiento in ordenar_movimientos(tablero):
        tablero.push(movimiento)
        puntaje, _ = negamax(tablero, profundidad - 1, -beta, -alfa, distancia_raiz + 1)
        # El puntaje del hijo viene desde el rival, por eso se niega una sola vez.
        puntaje = -puntaje
        tablero.pop()

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_movimiento = movimiento
        if puntaje > alfa:
            alfa = puntaje
        if alfa >= beta:
            break

    return mejor_puntaje, mejor_movimiento


def leer_movimiento_de_libro(tablero, ruta_libro):
    """Devuelve un movimiento del libro Polyglot, o None si no hay."""
    try:
        with chess.polyglot.open_reader(ruta_libro) as lector:

            entrada = lector.weighted_choice(tablero)
            if entrada:
                return entrada.move
    except FileNotFoundError:
        # Sin libro disponible, el motor calcula normalmente.
        pass
    except IndexError:
        # La posición no figura en el libro.
        pass
    return None


def buscar_raiz(tablero, profundidad):
    """Búsqueda de nivel superior. Devuelve (puntaje, mejor_movimiento) desde el lado a mover."""
    if not any(tablero.legal_moves):
        return (0, None) if not tablero.is_check() else (-MATE, None)

    # El libro no aporta evaluación, por eso el puntaje devuelto es 0.
    movimiento_libro = leer_movimiento_de_libro(tablero, ruta_recurso("openings.bin"))
    if movimiento_libro and movimiento_libro in tablero.legal_moves:
        return 0, movimiento_libro

    mejor_puntaje = -INF
    mejor_movimiento = None
    alfa, beta = -INF, INF

    for movimiento in ordenar_movimientos(tablero):
        tablero.push(movimiento)
        puntaje, _ = negamax(tablero, profundidad - 1, -beta, -alfa, 1)
        puntaje = -puntaje
        tablero.pop()

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_movimiento = movimiento
        if puntaje > alfa:
            alfa = puntaje

    # Si todos los puntajes quedaron en el piso, se devuelve igualmente un movimiento legal.
    if mejor_movimiento is None:
        legales = list(tablero.legal_moves)
        if legales:
            mejor_movimiento = legales[0]

    return mejor_puntaje, mejor_movimiento


# ============================================================
# BUCLE UCI
# ============================================================

def procesar_position(tablero, partes):
    """Aplica un comando position; si el FEN es inválido, deja el tablero intacto."""
    indice_moves = partes.index("moves") if "moves" in partes else len(partes)

    if "fen" in partes:
        campos = partes[partes.index("fen") + 1: indice_moves]
        if len(campos) < 6:
            return
        try:
            tablero.set_fen(" ".join(campos[:6]))
        except ValueError:
            return
    else:
        tablero.reset()

    for movimiento_uci in partes[indice_moves + 1:]:
        try:
            tablero.push(chess.Move.from_uci(movimiento_uci))
        except ValueError:
            # Un movimiento ilegal corta la lista; se conserva lo aplicado hasta ahí.
            break


def bucle_uci():
    """Lee comandos UCI por entrada estándar y responde por salida estándar."""
    tablero = chess.Board()

    for linea_cruda in sys.stdin:
        linea = linea_cruda.strip()
        if not linea:
            continue

        if linea == "uci":
            print("id name ColdFish v4")
            print("id author Koda")
            print("uciok")

        elif linea == "isready":
            print("readyok")

        elif linea == "ucinewgame":
            tablero.reset()

        elif linea.startswith("position"):
            procesar_position(tablero, linea.split())

        elif linea.startswith("go"):
            partes = linea.split()
            profundidad = 3
            if "depth" in partes:
                try:
                    profundidad = int(partes[partes.index("depth") + 1])
                except (IndexError, ValueError):
                    pass
            # Se limita a 1-6 para mantener tiempos de respuesta razonables.
            profundidad = max(1, min(profundidad, 6))

            _, mejor = buscar_raiz(tablero, profundidad)
            print(f"bestmove {mejor.uci()}" if mejor else "bestmove 0000")

        elif linea == "quit":
            break

        sys.stdout.flush()


if __name__ == "__main__":
    bucle_uci()
