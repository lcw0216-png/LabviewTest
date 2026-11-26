import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
d = Doc()
R = "root"
rows = d.ctl(R, 1, "Rows", "array{int32}", "[7,7]")
cols = d.ctl(R, 1, "Cols", "array{int32}", "[3,4]")
stones = d.ctl(R, 1, "Stones", "array{int32}", "[1,2]")
renju = d.ctl(R, 1, "Renju", "bool", "true")
nundo = d.ctl(R, 1, "Undo Count", "int32", "0")
d.label(R, 1, "테스트: 순서대로 착수 후 무르기")


def to_stone(p, dep, n):
    e, b_, w = [d.const(p, dep, STONE, v) for v in (EMPTY, BLACK, WHITE)]
    return d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 1)), b_,
                 d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 2)), w, e))


def lb(lu, ld, i, L, it):
    r, c, s, rj = i
    m = d.bnd(lu, ld, d.const(lu, ld, MOVE, "[0,0,0]"), [("Row", r), ("Col", c), ("Stone", to_stone(lu, ld, s))])
    o = d.call(lu, ld, "Game_Place_Stone.vi", [("Board State", L[0]), ("Move", m), ("Renju", rj),
                                               ("error in", d.noerr(lu, ld))],
               ["Board State out", "Placed?", "Win?", "Win Line", "Forbidden Reason", "Draw?", "error out"])
    return [(o["Placed?"], "index"), (o["Win?"], "index"), (o["Forbidden Reason"], "index")], [o["Board State out"]], None


outs, fin = d.loop("For Loop", R, 1, [(rows, "index"), (cols, "index"), (stones, "index"), (renju, None)],
                   [d.const(R, 1, BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]")], lb)
u = d.call(R, 1, "Game_Undo.vi", [("Board State", fin[0]), ("Count", nundo), ("error in", d.noerr(R, 1))],
           ["Board State out", "Undone", "error out"])
g, h, last = d.unb(R, 1, u["Board State out"], ["Grid", "Move History", "Last Move"])
d.ind(R, 1, "Placed", "array{bool}", "[]", outs[0])
d.ind(R, 1, "Win", "array{bool}", "[]", outs[1])
d.ind(R, 1, "Reason", "array{" + FORB + "}", "[]", outs[2])
d.ind(R, 1, "History Size", "int32", "0", d.size(R, 1, h))
d.ind(R, 1, "Last Move", MOVE, "[0,0,0]", last)
d.ind(R, 1, "Undone", "int32", "0", u["Undone"])
d.ind(R, 1, "Cell 7,3", STONE, "0", d.idx2(R, 1, g, d.i32(R, 1, 7), d.i32(R, 1, 3)))
d.ind(R, 1, "error out", ERR_T, "[false,0,]", u["error out"])
print(d.write(f"{OUT}/Test_Game.xml", "Test_Game.vi", "Game_Place_Stone / Game_Undo 테스트."))
