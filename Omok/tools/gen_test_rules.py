import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
d = Doc()
R = "root"
rows = d.ctl(R, 1, "Rows", "array{int32}", "[]", conIdx=11, conn="required")
cols = d.ctl(R, 1, "Cols", "array{int32}", "[]")
stones = d.ctl(R, 1, "Stones", "array{int32}", "[]")
mr = d.ctl(R, 1, "Move Row", "int32", "7")
mc = d.ctl(R, 1, "Move Col", "int32", "7")
ms = d.ctl(R, 1, "Move Stone", "int32", "1")
ex = d.ctl(R, 1, "Exact Five", "bool", "false")
rj = d.ctl(R, 1, "Renju", "bool", "true")
d.label(R, 1, "테스트: 정수 배열로 보드를 만들고 Rule VI 호출")


def to_stone(p, dep, n):
    e, b_, w = [d.const(p, dep, STONE, v) for v in (EMPTY, BLACK, WHITE)]
    return d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 1)), b_,
                 d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 2)), w, e))


def lb(lu, ld, i, L, it):
    r, c, s = i
    return [], [d.rep2(lu, ld, L[0], r, c, to_stone(lu, ld, s))], None


_, fin = d.loop("For Loop", R, 1, [(rows, "index"), (cols, "index"), (stones, "index")],
                [d.const(R, 1, GRID, EMPTY_GRID)], lb)
grid = fin[0]
mv = d.bnd(R, 1, d.const(R, 1, MOVE, "[0,0,0]"), [("Row", mr), ("Col", mc), ("Stone", to_stone(R, 1, ms))])
grid2 = d.rep2(R, 1, grid, mr, mc, to_stone(R, 1, ms))
w = d.call(R, 1, "Rule_Check_Win.vi", [("Grid", grid2), ("Last Move", mv), ("Exact Five", ex),
                                         ("error in", d.noerr(R, 1))],
           ["Win?", "Win Line", "Run Length", "error out"])
f = d.call(R, 1, "Rule_Check_Forbidden.vi", [("Grid", grid), ("Move", mv), ("Renju", rj),
                                               ("error in", w["error out"])],
           ["Forbidden?", "Reason", "error out"])
d.ind(R, 1, "Win?", "bool", "false", w["Win?"])
d.ind(R, 1, "Win Line", MOVES, "[]", w["Win Line"])
d.ind(R, 1, "Run Length", "int32", "0", w["Run Length"])
d.ind(R, 1, "Forbidden?", "bool", "false", f["Forbidden?"])
d.ind(R, 1, "Reason", FORB, "0", f["Reason"])
d.ind(R, 1, "error out", ERR_T, "[false,0,]", f["error out"])
print(d.write(f"{OUT}/Test_Rules.xml", "Test_Rules.vi",
              "Rule_Check_Win / Rule_Check_Forbidden 테스트. Rows/Cols/Stones(1=흑,2=백)로 보드를 만들고 "
              "Move를 놓았을 때의 승리와 금수를 출력한다."))
