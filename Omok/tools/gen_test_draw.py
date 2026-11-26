import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
d = Doc()
R = "root"
rows = d.ctl(R, 1, "Rows", "array{int32}", "[7,7,8,6,7]", conIdx=11, conn="required")
cols = d.ctl(R, 1, "Cols", "array{int32}", "[7,8,7,6,9]")
stones = d.ctl(R, 1, "Stones", "array{int32}", "[1,2,1,2,1]")
hr = d.ctl(R, 1, "Hover Row", "int32", "9")
hc = d.ctl(R, 1, "Hover Col", "int32", "9")
sw = d.ctl(R, 1, "Win Line From First 5", "bool", "false")
d.label(R, 1, "테스트: 정수 배열로 Board State를 만들어 그리기")


def to_stone(p, dep, n):
    e, b_, w = [d.const(p, dep, STONE, v) for v in (EMPTY, BLACK, WHITE)]
    return d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 1)), b_,
                 d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 2)), w, e))


def lb(lu, ld, i, L, it):
    r, c, s = i
    st = to_stone(lu, ld, s)
    m = d.bnd(lu, ld, d.const(lu, ld, MOVE, "[0,0,0]"), [("Row", r), ("Col", c), ("Stone", st)])
    return [(m, "index")], [d.rep2(lu, ld, L[0], r, c, st)], None


outs, fin = d.loop("For Loop", R, 1, [(rows, "index"), (cols, "index"), (stones, "index")],
                   [d.const(R, 1, GRID, EMPTY_GRID)], lb)
hist = outs[0]
n = d.size(R, 1, hist)
last = d.idx1(R, 1, hist, d.sub(R, 1, n, d.i32(R, 1, 1)))
bs = d.bnd(R, 1, d.const(R, 1, BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]"),
           [("Grid", fin[0]), ("Move History", hist), ("Last Move", last)])
hov = d.bnd(R, 1, d.const(R, 1, MOVE, "[-1,-1,0]"), [("Row", hr), ("Col", hc)])
five = d.node(R, 1, "Array Subset", [("array", hist), ("index", d.i32(R, 1, 0)), ("length", d.i32(R, 1, 5))],
              ["subarray"])["subarray"]
wl = d.sel(R, 1, sw, five, d.const(R, 1, MOVES, "[]"))
dr = d.call(R, 1, "UI_Draw_Board.vi", [("Board State", bs), ("Hover", hov), ("Win Line", wl),
                                        ("error in", d.noerr(R, 1))], ["Picture", "error out"])
png = d.ctl(R, 1, "PNG Path", "path", "")
d.label(R, 1, "확인용: 그림을 PNG 파일로 저장")
pm = d.call(R, 1, "Picture to Pixmap.vi", [("picture", dr["Picture"]), ("rect", d.const(R, 1, RECT16, "[0,0,592,592]")),
                                            ("depth", d.i32(R, 1, 24))], ["new picture", "image data"])
ok = d.node(R, 1, "Empty String/Path?", [("string/path", png)], ["empty?"])["empty?"]
def wr(f2, d2, j):
    w = d.call(f2, d2, "Write PNG File.vi", [("error in (no error)", j[0]), ("path to PNG file", j[1]),
                                            ("image data", j[2])], ["error out", "path"])
    return [w["error out"]]
e2 = d.case(R, 1, ok, [dr["error out"], png, pm["image data"]], 1,
            [("False", "PNG 저장", wr), ("True", "경로 없음: 저장 안 함", lambda f2, d2, j: [j[0]])])[0]
d.ind(R, 1, "error out", ERR_T, "[false,0,]", e2)
print(d.write(f"{OUT}/Test_Draw.xml", "Test_Draw.vi", "UI_Draw_Board 테스트: 정수 배열로 돌을 놓고 Picture에 그린다."))
