"""Omok_Main v2: one full-window Picture (settings screen + game screen), 3-loop QMH."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
MSG = "uint16{Redraw,Click,Hover,AI Move Ready,Exit}"
PT = "cluster{int32.X,int32.Y}"
GMSG = "cluster{" + MSG + ".Msg," + MOVE + ".Move,uint32.Game ID," + PT + ".Point}"
GMSG0 = "[0,[-1,-1,0],0,[0,0]]"
AIREQ = "cluster{" + GRID + ".Grid," + STONE + ".AI Stone," + DIFF + ".Difficulty,bool.Renju,uint32.Game ID,bool.Stop}"
AIREQ0 = "[" + EMPTY_GRID + ",2,1,true,0,false]"

d = Doc()
R = "root"


def gmsg(p, dep, msg, **kw):
    pairs = [("Msg", d.const(p, dep, MSG, msg))] + list(kw.items())
    return d.bnd(p, dep, d.const(p, dep, GMSG, GMSG0), [(k.replace("_", " "), v) for k, v in pairs])


def enq(p, dep, q, el, err=None):
    return d.node(p, dep, "Enqueue Element", [("queue", q), ("element", el),
                                              ("error in (no error)", err or d.noerr(p, dep))],
                  ["queue out", "timed out?", "error out"])


# ------------------------------------------------------------------ window setup
d.label(R, 1, "오목: 한 장의 Picture에 설정/게임 화면")
pn = d.node(R, 1, "Property Node", [("error in (no error)", d.noerr(R, 1)),
                                    ("Label.Visible", d.b(R, 1, False)),
                                    ("Position\\3ALeft", d.i32(R, 1, 0)), ("Position\\3ATop", d.i32(R, 1, 0)),
                                    ("Draw Area Size", d.const(R, 1, "cluster{int32.Width,int32.Height}", f"[{W},{H}]"))],
            ["error out"], fields="write+Label.Visible,write+Position\\3ALeft,write+Position\\3ATop,write+Draw Area Size",
            link="Board", type="{LV.Picture}")
win = d.node(R, 1, "Property Node", [("error in (no error)", pn["error out"]),
                                     ("Front Panel Window\\3AShow Scroll Bars", d.b(R, 1, False)),
                                     ("Front Panel Window\\3AShow Menu Bar", d.b(R, 1, False)),
                                     ("Front Panel Window\\3ATitle", d.const(R, 1, "string", esc("오목"))),
                                     ("Front Panel Window\\3APanel Bounds",
                                      d.const(R, 1, "cluster{int32.Left,int32.Top,int32.Right,int32.Bottom}",
                                              f"[200,60,{200 + W},{60 + H}]"))],
             ["error out"],
             fields="write+Front Panel Window\\3AShow Scroll Bars,write+Front Panel Window\\3AShow Menu Bar,"
                    "write+Front Panel Window\\3ATitle,write+Front Panel Window\\3APanel Bounds",
             type="{LV.VI}")
d.label(R, 1, "창 크기 = 화면 크기, 스크롤바/메뉴 숨김")
gq0 = d.node(R, 1, "Obtain Queue", [("element data type", d.const(R, 1, GMSG, GMSG0)),
                                    ("error in (no error)", win["error out"])], ["queue out", "created new?", "error out"])
aq0 = d.node(R, 1, "Obtain Queue", [("element data type", d.const(R, 1, AIREQ, AIREQ0)),
                                    ("error in (no error)", gq0["error out"])], ["queue out", "created new?", "error out"])
first = enq(R, 1, gq0["queue out"], gmsg(R, 1, "0"), aq0["error out"])
GQ, AQ = first["queue out"], aq0["queue out"]


# ------------------------------------------------------------------ UI event loop (producer)
def mouse_point(p, dep):
    m = d.node(p, dep, "Property Node", [("error in (no error)", d.noerr(p, dep))], ["Mouse", "error out"],
               fields="read+Mouse", link="Board", type="{LV.Picture}")
    return d.unb(p, dep, m["Mouse"], ["Mouse Position"])[0]


def ui_loop(lu, ld, i, L, it):
    q = i[0]

    def mouse(msg):
        def fn(fu, fd, j):
            e = enq(fu, fd, j[0], gmsg(fu, fd, msg, Point=mouse_point(fu, fd)))
            return [d.b(fu, fd, False), e["error out"]]
        return fn

    def close(fu, fd, j):
        e = enq(fu, fd, j[0], gmsg(fu, fd, "4"))
        d.label(fu, fd, "창 닫기 = 종료")
        return [d.b(fu, fd, True), e["error out"]]
    o = d.event(lu, ld, [q], 2, [
        (' "Board"\\3A Mouse Down ', "", mouse("1")),
        (' "Board"\\3A Mouse Move ', "", mouse("2")),
        (' Panel Close? ', "", close),
    ])
    return [(o[1], None)], [], o[0]


ui_out, _ = d.loop("While Loop", R, 1, [(GQ, None)], [], ui_loop, label="UI 이벤트 루프 (Producer)")


# ------------------------------------------------------------------ game loop (consumer)
def game_loop(lu, ld, i, L, it):
    gq, aq = i
    ctx = L[0]
    dq = d.node(lu, ld, "Dequeue Element", [("queue", gq), ("error in (no error)", d.noerr(lu, ld))],
                ["queue out", "element", "timed out?", "error out"])
    msg, mv, mgid, pt = d.unb(lu, ld, dq["element"], ["Msg", "Move", "Game ID", "Point"])
    x, y = d.unb(lu, ld, pt, ["X", "Y"])
    d.label(lu, ld, "메시지 처리: Context 하나를 Shift Register로")
    F = lambda p, dp: d.b(p, dp, False)
    T = lambda p, dp: d.b(p, dp, True)

    def redraw(f, dp, j):
        return [j[0], F(f, dp), T(f, dp), F(f, dp)]

    def click(f, dp, j):
        c = d.call(f, dp, "Game_Click.vi", [("Context", j[0]), ("X", j[3]), ("Y", j[4]), ("error in", d.noerr(f, dp))],
                   ["Context out", "Need AI", "error out"])
        return [c["Context out"], c["Need AI"], T(f, dp), F(f, dp)]

    def hover(f, dp, j):
        h = d.call(f, dp, "Game_Hover.vi", [("Context", j[0]), ("X", j[3]), ("Y", j[4]), ("error in", d.noerr(f, dp))],
                   ["Context out", "Changed", "error out"])
        return [h["Context out"], F(f, dp), h["Changed"], F(f, dp)]

    def aimove(f, dp, j):
        a = d.call(f, dp, "Game_AI_Move.vi", [("Context", j[0]), ("Move", j[1]), ("Game ID", j[2]),
                                              ("error in", d.noerr(f, dp))], ["Context out", "error out"])
        return [a["Context out"], F(f, dp), T(f, dp), F(f, dp)]

    def exit_(f, dp, j):
        el = d.bnd(f, dp, d.const(f, dp, AIREQ, AIREQ0), [("Stop", T(f, dp))])
        enq(f, dp, j[5], el)
        d.label(f, dp, "AI 루프에 종료 요청")
        return [j[0], F(f, dp), F(f, dp), T(f, dp)]
    o = d.case(lu, ld, msg, [ctx, mv, mgid, x, y, aq], 4, [
        ('"Redraw"', "다시 그리기", redraw),
        ('"Click"', "클릭", click),
        ('"Hover"', "마우스 이동", hover),
        ('"AI Move Ready"', "AI 결과", aimove),
        ('"Exit"', "종료", exit_),
    ])
    nctx, need_ai, draw, stop = o

    def send_ai(f, dp, j):
        g, a, df, rj, gid = ai_inputs(d, f, dp, j[0])
        el = d.bnd(f, dp, d.const(f, dp, AIREQ, AIREQ0), [("Grid", g), ("AI Stone", a), ("Difficulty", df),
                                                          ("Renju", rj), ("Game ID", gid)])
        enq(f, dp, j[1], el)
        return []
    d.case(lu, ld, need_ai, [nctx, aq], 0, [("True", "AI에 계산 요청", send_ai), ("False", None, lambda f, dp, j: [])])

    def paint(f, dp, j):
        r = d.call(f, dp, "UI_Render.vi", [("Context", j[0]), ("error in", d.noerr(f, dp))], ["Picture", "error out"])
        d.ind(f, dp, "Board", "picture", "", r["Picture"])
        return []
    d.case(lu, ld, draw, [nctx], 0, [("True", "화면 갱신", paint), ("False", "변화 없음", lambda f, dp, j: [])])
    return [(aq, None), (dq["error out"], None)], [nctx], stop


game_out, _ = d.loop("While Loop", R, 1, [(GQ, None), (AQ, None)], [d.const(R, 1, CTX, CTX0)], game_loop,
                     label="게임 루프 (Consumer)")


# ------------------------------------------------------------------ AI worker loop
def ai_loop(lu, ld, i, L, it):
    aq, gq = i
    dq = d.node(lu, ld, "Dequeue Element", [("queue", aq), ("error in (no error)", d.noerr(lu, ld))],
                ["queue out", "element", "timed out?", "error out"])
    g, ai, df, rj, gid, stop = d.unb(lu, ld, dq["element"], ["Grid", "AI Stone", "Difficulty", "Renju", "Game ID", "Stop"])
    d.label(lu, ld, "AI 작업자: 계산 후 게임 큐로 회신")

    def work(f, fd, j):
        g_, ai_, df_, rj_, gid_, q_, e_ = j
        c = d.call(f, fd, "AI_Calculate_Move.vi", [("Grid", g_), ("AI Stone", ai_), ("Difficulty", df_),
                                                   ("Renju", rj_), ("error in", e_)],
                   ["Move", "Score", "Valid", "error out"])
        e = enq(f, fd, q_, gmsg(f, fd, "3", Move=c["Move"], Game_ID=gid_), c["error out"])
        return [e["error out"]]
    o = d.case(lu, ld, stop, [g, ai, df, rj, gid, gq, dq["error out"]], 1,
               [("False", "계산", work), ("True", "종료", lambda f, fd, j: [j[6]])])
    return [(gq, None), (o[0], None)], [], stop


ai_out, _ = d.loop("While Loop", R, 1, [(AQ, None), (GQ, None)], [], ai_loop, label="AI 작업 루프")

r1 = d.node(R, 1, "Release Queue", [("queue", game_out[0]), ("error in (no error)", ui_out[0])],
            ["queue name", "remaining elements", "error out"])
r2 = d.node(R, 1, "Release Queue", [("queue", ai_out[0]), ("error in (no error)", r1["error out"])],
            ["queue name", "remaining elements", "error out"])
d.label(R, 1, "세 루프가 끝난 뒤 큐 해제")
print(d.write(f"{OUT}/Omok_Main.xml", "Omok_Main.vi",
              "오목 메인 VI (v2). 창 전체가 Picture 하나: 설정 화면(모드/선공/난이도/규칙/게임 시작) -> 게임 화면.\\0A"
              "UI 이벤트 루프(마우스) -> 게임 큐 -> 게임 루프(Context Shift Register, Game_Click/Hover/AI_Move, UI_Render)"
              " -> AI 큐 -> AI 작업 루프 -> 게임 큐. 사람 vs AI / 2인 플레이."))
