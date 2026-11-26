import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
d = Doc()
R = "root"
rows = d.ctl(R, 1, "Rows", "array{int32}", "[7,7,7,7]")
cols = d.ctl(R, 1, "Cols", "array{int32}", "[3,4,5,6]")
stones = d.ctl(R, 1, "Stones", "array{int32}", "[1,1,1,1]")
ais = d.ctl(R, 1, "AI Stone", "int32", "2")
diff = d.ctl(R, 1, "Difficulty", DIFF, "1")
renju = d.ctl(R, 1, "Renju", "bool", "true")
d.label(R, 1, "테스트: 정수 배열로 Grid를 만들고 AI 착수 계산")


def to_stone(p, dep, n):
    e, b_, w = [d.const(p, dep, STONE, v) for v in (EMPTY, BLACK, WHITE)]
    return d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 1)), b_,
                 d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 2)), w, e))


def lb(lu, ld, i, L, it):
    r, c, s = i
    return [], [d.rep2(lu, ld, L[0], r, c, to_stone(lu, ld, s))], None


_, fin = d.loop("For Loop", R, 1, [(rows, "index"), (cols, "index"), (stones, "index")],
                [d.const(R, 1, GRID, EMPTY_GRID)], lb)
o = d.call(R, 1, "AI_Calculate_Move.vi", [("Grid", fin[0]), ("AI Stone", to_stone(R, 1, ais)), ("Difficulty", diff),
                                          ("Renju", renju), ("error in", d.noerr(R, 1))],
           ["Move", "Score", "Valid", "error out"])
r, c = d.unb(R, 1, o["Move"], ["Row", "Col"])
d.ind(R, 1, "Row", "int32", "0", r)
d.ind(R, 1, "Col", "int32", "0", c)
d.ind(R, 1, "Score", "double", "0", o["Score"])
d.ind(R, 1, "Valid", "bool", "false", o["Valid"])
d.ind(R, 1, "error out", ERR_T, "[false,0,]", o["error out"])
print(d.write(f"{OUT}/Test_AI.xml", "Test_AI.vi", "AI_Calculate_Move 테스트."))
