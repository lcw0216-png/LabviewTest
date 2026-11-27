import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
OUT = sys.argv[1]
d = Doc()
R = "root"
phase = d.ctl(R, 1, "Phase", "bool", "true")
run = d.ctl(R, 1, "Running", "bool", "true")
png = d.ctl(R, 1, "PNG Path", "path", "")
d.label(R, 1, "테스트: 가짜 데이터로 메인 화면 렌더 -> PNG")
chs = d.call(R, 1, "Ch_Defaults.vi", [("error in", d.noerr(R, 1))], ["Channels", "error out"])


def lb(lu, ld, i, L, it):
    ch = i[0]

    def inner(u2, d2, k, L2, j):
        x = d.add(u2, d2, d.mul(u2, d2, j, d.dbl(u2, d2, 0.0628)), d.mul(u2, d2, k[0], d.dbl(u2, d2, 0.4)))
        s = d.node(u2, d2, "Sine", [("x", x)], ["sin(x)"])["sin(x)"]
        return [(d.add(u2, d2, d.mul(u2, d2, s, d.dbl(u2, d2, 30)), d.dbl(u2, d2, 50)), "index")], [], None
    row, _ = d.loop("For Loop", lu, ld, [(it, None)], [], inner, maxin=d.i32(lu, ld, 200))
    v = d.mul(lu, ld, it, d.dbl(lu, ld, 0.8))
    return [(row[0], "index"), (d.bnd(lu, ld, ch, [("Value", v)]), "index")], [], None


o, _ = d.loop("For Loop", R, 1, [(chs["Channels"], "index")], [], lb)
r = d.call(R, 1, "UI_Render_Main.vi", [("Channels", o[1]), ("Data", o[0]), ("dt", d.dbl(R, 1, 0.001)), ("Running", run),
                                       ("Logging", d.b(R, 1, True)), ("Hover Button", d.i32(R, 1, 1)), ("Phase", phase),
                                       ("Status", d.const(R, 1, "string", esc("측정 중 · 1000 Hz · 100 샘플/채널 · 저장 중"))),
                                       ("error in", chs["error out"])], ["Picture", "error out"])
pm = d.call(R, 1, "Picture to Pixmap.vi", [("picture", r["Picture"]), ("rect", d.const(R, 1, RECT16, "[0,0,1600,940]")),
                                           ("depth", d.i32(R, 1, 24))], ["new picture", "image data"])
w = d.call(R, 1, "Write PNG File.vi", [("error in (no error)", r["error out"]), ("path to PNG file", png),
                                       ("image data", pm["image data"])], ["error out", "path"])
d.ind(R, 1, "error out", ERR_T, "[false,0,]", w["error out"])
print(d.write(f"{OUT}/Test_Render.xml", "Test_Render.vi", "UI_Render_Main 테스트 (PNG 경로 필수)."))
