import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
d = Doc()
R = "root"
scr = d.ctl(R, 1, "Screen", SCREEN, "0")
sets = d.ctl(R, 1, "Settings", "array{int32}", "[0,0,1,1]")
hb = d.ctl(R, 1, "Hover Button", "int32", "-1")
rows = d.ctl(R, 1, "Rows", "array{int32}", "[7,7]")
cols = d.ctl(R, 1, "Cols", "array{int32}", "[7,8]")
stones = d.ctl(R, 1, "Stones", "array{int32}", "[1,2]")
st = d.ctl(R, 1, "Status", GSTAT, "1")
txt = d.ctl(R, 1, "Status Text", "string", "")
png = d.ctl(R, 1, "PNG Path", "path", "")
d.label(R, 1, "테스트: Context를 만들어 화면 렌더")


def to_stone(p, dep, n):
    e, b_, w = [d.const(p, dep, STONE, v) for v in (EMPTY, BLACK, WHITE)]
    return d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 1)), b_,
                 d.sel(p, dep, d.eq(p, dep, n, d.i32(p, dep, 2)), w, e))


def lb(lu, ld, i, L, it):
    r, c, s = i
    stn = to_stone(lu, ld, s)
    m = d.bnd(lu, ld, d.const(lu, ld, MOVE, "[0,0,0]"), [("Row", r), ("Col", c), ("Stone", stn)])
    return [(m, "index")], [d.rep2(lu, ld, L[0], r, c, stn)], None


outs, fin = d.loop("For Loop", R, 1, [(rows, "index"), (cols, "index"), (stones, "index")],
                   [d.const(R, 1, GRID, EMPTY_GRID)], lb)
hist = outs[0]
last = d.idx1(R, 1, hist, d.sub(R, 1, d.size(R, 1, hist), d.i32(R, 1, 1)))
bs = d.bnd(R, 1, d.const(R, 1, BOARD_STATE, EMPTY_BS), [("Grid", fin[0]), ("Move History", hist), ("Last Move", last)])
ctx = d.bnd(R, 1, d.const(R, 1, CTX, CTX0), [("Screen", scr), ("Settings", sets), ("Board", bs), ("Status", st),
                                              ("Hover Button", hb), ("Status Text", txt),
                                              ("Score 1", d.i32(R, 1, 2)), ("Score 2", d.i32(R, 1, 1)),
                                              ("Status Color", u32(d, R, 1, INK))])
r = d.call(R, 1, "UI_Render.vi", [("Context", ctx), ("error in", d.noerr(R, 1))], ["Picture", "error out"])
pm = d.call(R, 1, "Picture to Pixmap.vi", [("picture", r["Picture"]), ("rect", d.const(R, 1, RECT16, f"[0,0,{W},{H}]")),
                                           ("depth", d.i32(R, 1, 24))], ["new picture", "image data"])
w = d.call(R, 1, "Write PNG File.vi", [("error in (no error)", r["error out"]), ("path to PNG file", png),
                                       ("image data", pm["image data"])], ["error out", "path"])
d.ind(R, 1, "error out", ERR_T, "[false,0,]", w["error out"])
print(d.write(f"{OUT}/Test_Render.xml", "Test_Render.vi", "UI_Render 테스트: 화면을 PNG로 저장."))
