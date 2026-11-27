import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
d = Doc()
R = "root"
xs = d.ctl(R, 1, "Click X", "array{int32}", "[296]")
ys = d.ctl(R, 1, "Click Y", "array{int32}", "[635]")
png = d.ctl(R, 1, "PNG Path", "path", "")
d.label(R, 1, "테스트: 클릭 좌표를 차례로 넣어 게임 진행")


def lb(lu, ld, i, L, it):
    x, y = i
    c = d.call(lu, ld, "Game_Click.vi", [("Context", L[0]), ("X", x), ("Y", y), ("error in", d.noerr(lu, ld))],
               ["Context out", "Need AI", "error out"])

    def ai(f, dp, j):
        g, a, df, rj, gid = ai_inputs(d, f, dp, j[0])
        m = d.call(f, dp, "AI_Calculate_Move.vi", [("Grid", g), ("AI Stone", a), ("Difficulty", df), ("Renju", rj),
                                                   ("error in", d.noerr(f, dp))], ["Move", "Score", "Valid", "error out"])
        o = d.call(f, dp, "Game_AI_Move.vi", [("Context", j[0]), ("Move", m["Move"]), ("Game ID", gid),
                                              ("error in", d.noerr(f, dp))], ["Context out", "error out"])
        return [o["Context out"]]
    nc = d.case(lu, ld, c["Need AI"], [c["Context out"]], 1, [("True", "AI 응수", ai), ("False", None, lambda f, dp, j: [j[0]])])[0]
    return [], [nc], None


_, fin = d.loop("For Loop", R, 1, [(xs, "index"), (ys, "index")], [d.const(R, 1, CTX, CTX0)], lb)
ctx = fin[0]
scr, sets, bs, st, s1, s2, dr, txt = d.unb(R, 1, ctx, ["Screen", "Settings", "Board", "Status", "Score 1", "Score 2",
                                                        "Draws", "Status Text"])
hist = d.unb(R, 1, bs, ["Move History"])[0]
d.ind(R, 1, "Screen", SCREEN, "0", scr)
d.ind(R, 1, "Settings", "array{int32}", "[]", sets)
d.ind(R, 1, "Status", GSTAT, "0", st)
d.ind(R, 1, "Status Text", "string", "", txt)
d.ind(R, 1, "Moves", "int32", "0", d.size(R, 1, hist))
d.ind(R, 1, "History", MOVES, "[]", hist)
d.ind(R, 1, "Score 1", "int32", "0", s1)
d.ind(R, 1, "Score 2", "int32", "0", s2)
d.ind(R, 1, "Draws", "int32", "0", dr)
r = d.call(R, 1, "UI_Render.vi", [("Context", ctx), ("error in", d.noerr(R, 1))], ["Picture", "error out"])
pm = d.call(R, 1, "Picture to Pixmap.vi", [("picture", r["Picture"]), ("rect", d.const(R, 1, RECT16, f"[0,0,{W},{H}]")),
                                           ("depth", d.i32(R, 1, 24))], ["new picture", "image data"])
empty = d.node(R, 1, "Empty String/Path?", [("string/path", png)], ["empty?"])["empty?"]


def wr(f2, d2, j):
    w = d.call(f2, d2, "Write PNG File.vi", [("error in (no error)", j[0]), ("path to PNG file", j[1]),
                                            ("image data", j[2])], ["error out", "path"])
    return [w["error out"]]


e2 = d.case(R, 1, empty, [r["error out"], png, pm["image data"]], 1,
            [("False", "PNG 저장", wr), ("True", "경로 없음", lambda f2, d2, j: [j[0]])])[0]
d.ind(R, 1, "error out", ERR_T, "[false,0,]", e2)
print(d.write(f"{OUT}/Test_Flow.xml", "Test_Flow.vi", "Game_Click 흐름 테스트: 클릭 좌표 배열로 설정→게임 진행, 결과 화면 PNG 저장."))
