import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
MSG = "uint16{New Game,Click,Hover,Undo,Request AI,AI Move Ready,Exit}"
GMSG = "cluster{" + MSG + ".Msg," + MOVE + ".Move,uint32.Game ID}"
AIREQ = "cluster{" + GRID + ".Grid," + STONE + ".AI Stone," + DIFF + ".Difficulty,bool.Renju,uint32.Game ID,bool.Stop}"
GSTAT = "uint16{Idle,Player Turn,AI Thinking,Game Over}"
SIDE = "uint16{Black (First),White (Second)}"
EMPTY_BS = "[" + EMPTY_GRID + ",[],[-1,-1,0]]"
NOMOVE = "[-1,-1,0]"
IDLE, PTURN, AITH, OVER = "0", "1", "2", "3"

d = Doc()
R = "root"


def s(p, dep, text):
    return d.const(p, dep, "string", esc(text))


def gmsg(p, dep, msg, move=None, gid=None):
    pairs = [("Msg", d.const(p, dep, MSG, msg))]
    if move is not None:
        pairs.append(("Move", move))
    if gid is not None:
        pairs.append(("Game ID", gid))
    return d.bnd(p, dep, d.const(p, dep, GMSG, "[0," + NOMOVE + ",0]"), pairs)


def enq(p, dep, q, el):
    return d.node(p, dep, "Enqueue Element", [("queue", q), ("element", el), ("error in (no error)", d.noerr(p, dep))],
                  ["queue out", "timed out?", "error out"])["error out"]


def stat(p, dep, v):
    return d.const(p, dep, GSTAT, v)


# ------------------------------------------------------------------ setup
d.label(R, 1, "오목 Player vs AI: UI 이벤트 / 게임 / AI 3루프 QMH")
pn = d.node(R, 1, "Property Node", [("error in (no error)", d.noerr(R, 1)),
                                    ("Draw Area Size", d.const(R, 1, "cluster{int32.Width,int32.Height}", "[592,592]"))],
            ["error out"], fields="write+Draw Area Size", link="Board", type="{LV.Picture}")
gq0 = d.node(R, 1, "Obtain Queue", [("element data type", d.const(R, 1, GMSG, "[0," + NOMOVE + ",0]")),
                                    ("error in (no error)", pn["error out"])],
             ["queue out", "created new?", "error out"])
aq0 = d.node(R, 1, "Obtain Queue", [("element data type", d.const(R, 1, AIREQ, "[" + EMPTY_GRID + ",2,1,true,0,false]")),
                                    ("error in (no error)", gq0["error out"])],
             ["queue out", "created new?", "error out"])
first = d.node(R, 1, "Enqueue Element", [("queue", gq0["queue out"]), ("element", gmsg(R, 1, "0")),
                                         ("error in (no error)", aq0["error out"])],
               ["queue out", "timed out?", "error out"])
d.label(R, 1, "시작하자마자 새 게임 메시지")
GQ, AQ = first["queue out"], aq0["queue out"]


# ------------------------------------------------------------------ UI event loop
def mouse_move(p, dep):
    m = d.node(p, dep, "Property Node", [("error in (no error)", d.noerr(p, dep))], ["Mouse", "error out"],
               fields="read+Mouse", link="Board", type="{LV.Picture}")
    pos = d.unb(p, dep, m["Mouse"], ["Mouse Position"])[0]
    g = d.call(p, dep, "UI_Pixel_To_Grid.vi", [("Coords", pos), ("error in", m["error out"])],
               ["Row", "Col", "Valid", "error out"])
    return d.bnd(p, dep, d.const(p, dep, MOVE, NOMOVE), [("Row", g["Row"]), ("Col", g["Col"])])


def ui_loop(lu, ld, i, L, it):
    q = i[0]

    def mouse(msg, lab):
        def fn(fu, fd, j):
            mv = mouse_move(fu, fd)
            return [d.b(fu, fd, False), enq(fu, fd, j[0], gmsg(fu, fd, msg, mv))]
        return fn

    def button(ctl, msg, stop):
        def fn(fu, fd, j):
            if ctl:
                d.ctl(fu, fd, ctl, "bool", "false", style="latched")
            return [d.b(fu, fd, stop), enq(fu, fd, j[0], gmsg(fu, fd, msg))]
        return fn
    o = d.event(lu, ld, [q], 2, [
        (' "Board"\\3A Mouse Down ', "", mouse("1", "클릭")),
        (' "Board"\\3A Mouse Move ', "", mouse("2", "호버")),
        (' "New Game"\\3A Value Change ', "", button("New Game", "0", False)),
        (' "Undo"\\3A Value Change ', "", button("Undo", "3", False)),
        (' "Exit"\\3A Value Change ', "", button("Exit", "6", True)),
        (' Panel Close? ', "", button(None, "6", True)),
    ])
    return [(o[1], None)], [], o[0]


ui_out, _ = d.loop("While Loop", R, 1, [(GQ, None)], [], ui_loop, label="UI 이벤트 루프 (Producer)")


# ------------------------------------------------------------------ game loop
def game_loop(lu, ld, i, L, it):
    gq, aq = i
    bs, st, gid, pst, rj, hov, wl, pw, aw, dr, txt = L
    dq = d.node(lu, ld, "Dequeue Element", [("queue", gq), ("error in (no error)", d.noerr(lu, ld))],
                ["queue out", "element", "timed out?", "error out"])
    msg, mv, mgid = d.unb(lu, ld, dq["element"], ["Msg", "Move", "Game ID"])
    diff = d.ctl(lu, ld, "Difficulty", DIFF, "1")
    d.label(lu, ld, "메시지 처리 (Consumer)")

    def ai_req(p, dep, q, g, stone, df, r, gi):
        el = d.bnd(p, dep, d.const(p, dep, AIREQ, "[" + EMPTY_GRID + ",2,1,true,0,false]"),
                   [("Grid", g), ("AI Stone", stone), ("Difficulty", df), ("Renju", r), ("Game ID", gi)])
        return enq(p, dep, q, el)

    def maybe_ai(p, dep, cond, q, g, stone, df, r, gi):
        def yes(f2, d2, j):
            ai_req(f2, d2, *j)
            return []
        d.case(p, dep, cond, [q, g, stone, df, r, gi], 0,
               [("True", "AI 요청", yes), ("False", "요청 없음", lambda f2, d2, j: [])])

    ins = [bs, st, gid, pst, rj, hov, wl, pw, aw, dr, txt, aq, mv, mgid, diff]
    # frames get: 0 bs,1 st,2 gid,3 pst,4 rj,5 hov,6 wl,7 pw,8 aw,9 dr,10 txt,11 aq,12 mv,13 mgid,14 diff
    # frames return 11 SR values + stop

    def passthru(f, dep, j, stop=False):
        return j[:11] + [d.b(f, dep, stop)]

    def f_new(f, dep, j):
        side = d.ctl(f, dep, "Player Side", SIDE, "0")
        rj2 = d.ctl(f, dep, "Renju", "bool", "true")
        pblack = d.eq(f, dep, side, d.const(f, dep, SIDE, "0"))
        B, W = d.const(f, dep, STONE, BLACK), d.const(f, dep, STONE, WHITE)
        pst2 = d.sel(f, dep, pblack, B, W)
        ai = d.sel(f, dep, pblack, W, B)
        gid2 = d.node(f, dep, "Increment", [("x", j[2])], ["x+1"])["x+1"]
        bs0 = d.const(f, dep, BOARD_STATE, EMPTY_BS)
        g0 = d.unb(f, dep, bs0, ["Grid"])[0]
        maybe_ai(f, dep, d.not_(f, dep, pblack), j[11], g0, ai, j[14], rj2, gid2)
        d.label(f, dep, "플레이어가 백이면 AI(흑)가 먼저 둔다")
        st2 = d.sel(f, dep, pblack, stat(f, dep, PTURN), stat(f, dep, AITH))
        t2 = d.sel(f, dep, pblack, s(f, dep, "새 게임: 당신 차례 (흑)"), s(f, dep, "새 게임: AI 생각 중..."))
        return [bs0, st2, gid2, pst2, rj2, d.const(f, dep, MOVE, NOMOVE), d.const(f, dep, MOVES, "[]"),
                j[7], j[8], j[9], t2, d.b(f, dep, False)]

    def place(f, dep, j, mvx):
        return d.call(f, dep, "Game_Place_Stone.vi", [("Board State", j[0]), ("Move", mvx), ("Renju", j[4]),
                                                      ("error in", d.noerr(f, dep))],
                      ["Board State out", "Placed?", "Win?", "Win Line", "Forbidden Reason", "Draw?", "error out"])

    def f_click(f, dep, j):
        turn = d.eq(f, dep, j[1], stat(f, dep, PTURN))

        def yes(f2, d2, k):
            mvx = d.bnd(f2, d2, k[12], [("Stone", k[3])])
            p = place(f2, d2, k, mvx)
            placed, win, draw = p["Placed?"], p["Win?"], p["Draw?"]
            over = d.or_(f2, d2, win, draw)
            cont = d.and_(f2, d2, placed, d.not_(f2, d2, over))
            ai = opp_stone(d, f2, d2, k[3])
            g2 = d.unb(f2, d2, p["Board State out"], ["Grid"])[0]
            maybe_ai(f2, d2, cont, k[11], g2, ai, k[14], k[4], k[2])
            d.label(f2, d2, "착수 성공 -> 승/무 판정, 아니면 AI 요청")
            one = d.i32(f2, d2, 1)
            pw2 = d.sel(f2, d2, win, d.add(f2, d2, k[7], one), k[7])
            dr2 = d.sel(f2, d2, draw, d.add(f2, d2, k[9], one), k[9])
            st2 = d.sel(f2, d2, over, stat(f2, d2, OVER), d.sel(f2, d2, placed, stat(f2, d2, AITH), k[1]))
            fr = p["Forbidden Reason"]
            ftxt = d.sel(f2, d2, d.eq(f2, d2, fr, d.const(f2, d2, FORB, "1")), s(f2, d2, "금수 (3-3) 자리입니다"),
                         d.sel(f2, d2, d.eq(f2, d2, fr, d.const(f2, d2, FORB, "2")), s(f2, d2, "금수 (4-4) 자리입니다"),
                               d.sel(f2, d2, d.eq(f2, d2, fr, d.const(f2, d2, FORB, "3")),
                                     s(f2, d2, "금수 (장목) 자리입니다"), s(f2, d2, "둘 수 없는 자리입니다"))))
            t2 = d.sel(f2, d2, win, s(f2, d2, "승리! 플레이어 승"),
                       d.sel(f2, d2, draw, s(f2, d2, "무승부"),
                             d.sel(f2, d2, placed, s(f2, d2, "AI 생각 중..."), ftxt)))
            wl2 = d.sel(f2, d2, win, p["Win Line"], k[6])
            return [p["Board State out"], st2, k[2], k[3], k[4], d.const(f2, d2, MOVE, NOMOVE), wl2,
                    pw2, k[8], dr2, t2]
        o = d.case(f, dep, turn, j, 11, [("True", "플레이어 차례", yes),
                                         ("False", "무시", lambda f2, d2, k: k[:11])])
        return o + [d.b(f, dep, False)]

    def f_hover(f, dep, j):
        turn = d.eq(f, dep, j[1], stat(f, dep, PTURN))
        h = d.sel(f, dep, turn, j[12], d.const(f, dep, MOVE, NOMOVE))
        return j[:5] + [h] + j[6:11] + [d.b(f, dep, False)]

    def f_undo(f, dep, j):
        ok = d.or_(f, dep, d.eq(f, dep, j[1], stat(f, dep, PTURN)), d.eq(f, dep, j[1], stat(f, dep, OVER)))

        def yes(f2, d2, k):
            hist, last = d.unb(f2, d2, k[0], ["Move History", "Last Move"])
            n = d.size(f2, d2, hist)
            lst = d.unb(f2, d2, last, ["Stone"])[0]
            one, two, zero = d.i32(f2, d2, 1), d.i32(f2, d2, 2), d.i32(f2, d2, 0)
            cnt = d.sel(f2, d2, d.eq(f2, d2, lst, k[3]), one, two)
            keep = d.sel(f2, d2, d.eq(f2, d2, k[3], d.const(f2, d2, STONE, WHITE)), one, zero)
            avail = d.max_(f2, d2, d.sub(f2, d2, n, keep), zero)
            cnt = d.node(f2, d2, "Max & Min", [("x", cnt), ("y", avail)], ["max(x\\2Cy)", "min(x\\2Cy)"])["min(x\\2Cy)"]
            d.label(f2, d2, "내 마지막 수까지 무르기, AI 흑 첫 수는 유지")
            u = d.call(f2, d2, "Game_Undo.vi", [("Board State", k[0]), ("Count", cnt), ("error in", d.noerr(f2, d2))],
                       ["Board State out", "Undone", "error out"])
            gid2 = d.node(f2, d2, "Increment", [("x", k[2])], ["x+1"])["x+1"]
            return [u["Board State out"], stat(f2, d2, PTURN), gid2, k[3], k[4], k[5], d.const(f2, d2, MOVES, "[]"),
                    k[7], k[8], k[9], s(f2, d2, "무르기: 당신 차례")]
        o = d.case(f, dep, ok, j, 11, [("True", "무르기", yes), ("False", "AI 생각 중이면 무시", lambda f2, d2, k: k[:11])])
        return o + [d.b(f, dep, False)]

    def f_aimove(f, dep, j):
        cur = d.and_(f, dep, d.eq(f, dep, j[13], j[2]), d.eq(f, dep, j[1], stat(f, dep, AITH)))
        d.label(f, dep, "Game ID가 다르면 지난 판의 결과: 버림")

        def yes(f2, d2, k):
            p = place(f2, d2, k, k[12])
            win, draw = p["Win?"], p["Draw?"]
            over = d.or_(f2, d2, win, draw)
            one = d.i32(f2, d2, 1)
            aw2 = d.sel(f2, d2, win, d.add(f2, d2, k[8], one), k[8])
            dr2 = d.sel(f2, d2, draw, d.add(f2, d2, k[9], one), k[9])
            st2 = d.sel(f2, d2, over, stat(f2, d2, OVER), stat(f2, d2, PTURN))
            t2 = d.sel(f2, d2, win, s(f2, d2, "패배... AI 승"),
                       d.sel(f2, d2, draw, s(f2, d2, "무승부"), s(f2, d2, "당신 차례")))
            wl2 = d.sel(f2, d2, win, p["Win Line"], k[6])
            return [p["Board State out"], st2, k[2], k[3], k[4], k[5], wl2, k[7], aw2, dr2, t2]
        o = d.case(f, dep, cur, j, 11, [("True", "AI 착수", yes), ("False", "버림", lambda f2, d2, k: k[:11])])
        return o + [d.b(f, dep, False)]

    def f_exit(f, dep, j):
        el = d.bnd(f, dep, d.const(f, dep, AIREQ, "[" + EMPTY_GRID + ",2,1,true,0,false]"), [("Stop", d.b(f, dep, True))])
        enq(f, dep, j[11], el)
        d.label(f, dep, "AI 루프에 종료 요청")
        return j[:11] + [d.b(f, dep, True)]

    o = d.case(lu, ld, msg, ins, 12, [
        ('"New Game"', "새 게임", f_new),
        ('"Click"', "클릭 착수", f_click),
        ('"Hover"', "호버", f_hover),
        ('"Undo"', "무르기", f_undo),
        ('"Request AI"', "사용 안 함", passthru),
        ('"AI Move Ready"', "AI 결과", f_aimove),
        ('"Exit"', "종료", f_exit),
    ])
    bs2, st2, gid2, pst2, rj2, hov2, wl2, pw2, aw2, dr2, txt2, stop = o
    pic = d.call(lu, ld, "UI_Draw_Board.vi", [("Board State", bs2), ("Hover", hov2), ("Win Line", wl2),
                                              ("error in", d.noerr(lu, ld))], ["Picture", "error out"])
    d.ind(lu, ld, "Board", "picture", "", pic["Picture"])
    d.ind(lu, ld, "Status", "string", "", txt2)
    d.ind(lu, ld, "Player Wins", "int32", "0", pw2)
    d.ind(lu, ld, "AI Wins", "int32", "0", aw2)
    d.ind(lu, ld, "Draws", "int32", "0", dr2)
    h = d.unb(lu, ld, bs2, ["Move History"])[0]
    d.ind(lu, ld, "Moves", "int32", "0", d.size(lu, ld, h))
    d.ind(lu, ld, "AI Thinking", "bool", "false", d.eq(lu, ld, st2, stat(lu, ld, AITH)))
    d.label(lu, ld, "매 메시지마다 바둑판 다시 그리기")
    return [(aq, None), (dq["error out"], None)], [bs2, st2, gid2, pst2, rj2, hov2, wl2, pw2, aw2, dr2, txt2], stop


game_out, _ = d.loop("While Loop", R, 1, [(GQ, None), (AQ, None)],
                     [d.const(R, 1, BOARD_STATE, EMPTY_BS), stat(R, 1, IDLE), d.const(R, 1, "uint32", "0"),
                      d.const(R, 1, STONE, BLACK), d.b(R, 1, True), d.const(R, 1, MOVE, NOMOVE),
                      d.const(R, 1, MOVES, "[]"), d.i32(R, 1, 0), d.i32(R, 1, 0), d.i32(R, 1, 0), s(R, 1, "")],
                     game_loop, label="게임 루프 (Consumer)")


# ------------------------------------------------------------------ AI worker loop
def tick_after(p, dep, err):
    st = d.unb(p, dep, err, ["status"])[0]

    def fr(f, fd, j):
        t = d.node(f, fd, "Tick Count (ms)", [], ["millisecond timer value"])["millisecond timer value"]
        return [t, j[0]]
    o = d.case(p, dep, st, [err], 2, [("False", "No Error", fr), ("True", "Error", fr)])
    return o[0], o[1]


def ai_loop(lu, ld, i, L, it):
    aq, gq = i
    dq = d.node(lu, ld, "Dequeue Element", [("queue", aq), ("error in (no error)", d.noerr(lu, ld))],
                ["queue out", "element", "timed out?", "error out"])
    g, ai, df, rj, gid, stop = d.unb(lu, ld, dq["element"], ["Grid", "AI Stone", "Difficulty", "Renju", "Game ID", "Stop"])
    d.label(lu, ld, "AI 작업자: 요청을 받아 계산 후 게임 루프로 회신")

    def work(f, fd, j):
        g_, ai_, df_, rj_, gid_, q_, e_ = j
        t0, e1 = tick_after(f, fd, e_)
        c = d.call(f, fd, "AI_Calculate_Move.vi", [("Grid", g_), ("AI Stone", ai_), ("Difficulty", df_),
                                                   ("Renju", rj_), ("error in", e1)],
                   ["Move", "Score", "Valid", "error out"])
        t1, e2 = tick_after(f, fd, c["error out"])
        d.ind(f, fd, "AI Time (ms)", "uint32", "0", d.sub(f, fd, t1, t0))
        enq(f, fd, q_, gmsg(f, fd, "5", c["Move"], gid_))
        return [e2]
    o = d.case(lu, ld, stop, [g, ai, df, rj, gid, gq, dq["error out"]], 1,
               [("False", "계산", work), ("True", "종료", lambda f, fd, j: [j[6]])])
    return [(gq, None), (o[0], None)], [], stop


ai_out, _ = d.loop("While Loop", R, 1, [(AQ, None), (GQ, None)], [], ai_loop, label="AI 작업 루프")

# ------------------------------------------------------------------ shutdown
r1 = d.node(R, 1, "Release Queue", [("queue", game_out[0]), ("error in (no error)", ui_out[0])],
            ["queue name", "remaining elements", "error out"])
r2 = d.node(R, 1, "Release Queue", [("queue", ai_out[0]), ("error in (no error)", r1["error out"])],
            ["queue name", "remaining elements", "error out"])
d.label(R, 1, "세 루프가 모두 끝난 뒤 큐 해제")
d.ind(R, 1, "error out", ERR_T, "[false,0,]", r2["error out"])
print(d.write(f"{OUT}/Omok_Main.xml", "Omok_Main.vi",
              "오목 Player vs AI 메인 VI. UI 이벤트 루프(Producer) -> 게임 큐 -> 게임 루프(Consumer, 상태는 Shift Register) "
              "-> AI 큐 -> AI 작업 루프 -> 게임 큐(AI Move Ready). Game ID로 지난 판/무르기 이전의 AI 결과를 버린다."))
