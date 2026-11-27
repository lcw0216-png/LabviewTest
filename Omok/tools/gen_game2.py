"""v2 game controller SubVIs working on the Context cluster (Player vs AI and Player vs Player)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
GREEN, ORANGE, RED_T = 0x27AE60, 0xE67E22, 0xE74C3C
IDLE, PTURN, AITH, OVER = "0", "1", "2", "3"
NOMOVE = "[-1,-1,0]"
CTXIN = ("Context", CTX, CTX0, "r0", "required")
CTXOUT = ("Context out", CTX, CTX0, "r4")


def s(d, p, dep, text):
    return d.const(p, dep, "string", esc(text))


def stat(d, p, dep, v):
    return d.const(p, dep, GSTAT, v)


def setting(d, p, dep, sets, i):
    return d.idx1(p, dep, sets, d.i32(p, dep, i))


def is_pvp(d, p, dep, sets):
    return d.eq(p, dep, setting(d, p, dep, sets, 0), d.i32(p, dep, 1))


def parity_stone(d, p, dep, hist):
    _, r = qr(d, p, dep, d.size(p, dep, hist), d.i32(p, dep, 2))
    return d.sel(p, dep, d.eq(p, dep, r, d.i32(p, dep, 0)), d.const(p, dep, STONE, BLACK), d.const(p, dep, STONE, WHITE))


def turn_text(d, p, dep, stone):
    return d.sel(p, dep, d.eq(p, dep, stone, d.const(p, dep, STONE, BLACK)), s(d, p, dep, "흑 차례"), s(d, p, dep, "백 차례"))


def guarded(d, fu, dep, cond, ctx, extra_ins, nouts, fn, label_t, label_f, false_extra):
    """Run fn only when cond; otherwise pass Context through (+ false_extra(p,dep) outputs)."""
    def no(f2, d2, j):
        return [j[0]] + false_extra(f2, d2)
    return d.case(fu, dep, cond, [ctx] + extra_ins, nouts, [("True", label_t, fn), ("False", label_f, no)])


# ---------------------------------------------------------------- Game_Start
def start():
    d = Doc()

    def body(fu, dep, ins):
        ctx, reset = ins
        sets, gid, s1, s2, dr = d.unb(fu, dep, ctx, ["Settings", "Game ID", "Score 1", "Score 2", "Draws"])
        pvp = is_pvp(d, fu, dep, sets)
        pblack = d.or_(fu, dep, pvp, d.eq(fu, dep, setting(d, fu, dep, sets, 1), d.i32(fu, dep, 0)))
        pst = d.sel(fu, dep, pblack, d.const(fu, dep, STONE, BLACK), d.const(fu, dep, STONE, WHITE))
        ai_first = d.not_(fu, dep, pblack)
        d.label(fu, dep, "플레이어가 백(AI 대전)이면 AI가 먼저")
        st = d.sel(fu, dep, ai_first, stat(d, fu, dep, AITH), stat(d, fu, dep, PTURN))
        txt = d.sel(fu, dep, pvp, s(d, fu, dep, "흑 차례"),
                    d.sel(fu, dep, ai_first, s(d, fu, dep, "AI 생각 중..."), s(d, fu, dep, "당신 차례 (흑)")))
        z = d.i32(fu, dep, 0)
        out = d.bnd(fu, dep, ctx, [
            ("Screen", d.const(fu, dep, SCREEN, "1")), ("Board", d.const(fu, dep, BOARD_STATE, EMPTY_BS)),
            ("Status", st), ("Game ID", d.node(fu, dep, "Increment", [("x", gid)], ["x+1"])["x+1"]),
            ("Player Stone", pst), ("Hover", d.const(fu, dep, MOVE, NOMOVE)), ("Hover Button", d.i32(fu, dep, -1)),
            ("Win Line", d.const(fu, dep, MOVES, "[]")),
            ("Score 1", d.sel(fu, dep, reset, z, s1)), ("Score 2", d.sel(fu, dep, reset, z, s2)),
            ("Draws", d.sel(fu, dep, reset, z, dr)),
            ("Status Text", txt), ("Status Color", u32(d, fu, dep, INK))])
        return [out, ai_first]

    subvi(d, [CTXIN, ("Reset Scores", "bool", "false", "r5", "recommended")],
          [CTXOUT, ("Need AI", "bool", "false", "r6")], body)
    return d.write(f"{OUT}/Game_Start.xml", "Game_Start.vi",
                   "새 판 시작: 바둑판 초기화, Game ID 증가, 게임 화면으로 전환. Reset Scores면 점수도 0.\\0A"
                   "Need AI = AI 대전에서 플레이어가 백이라 AI가 먼저 둘 때 True.")


# ---------------------------------------------------------------- Game_Board_Click
def board_click():
    d = Doc()

    def body(fu, dep, ins):
        ctx, row, col = ins
        st = d.unb(fu, dep, ctx, ["Status"])[0]
        turn_ok = d.eq(fu, dep, st, stat(d, fu, dep, PTURN))
        d.label(fu, dep, "내 차례일 때만 착수")

        def yes(f, dp, j):
            c, r_, c_ = j
            sets, bs, pst, wl, s1, s2, dr = d.unb(f, dp, c, ["Settings", "Board", "Player Stone", "Win Line",
                                                              "Score 1", "Score 2", "Draws"])
            pvp = is_pvp(d, f, dp, sets)
            renju = d.eq(f, dp, setting(d, f, dp, sets, 3), d.i32(f, dp, 1))
            hist = d.unb(f, dp, bs, ["Move History"])[0]
            stone = d.sel(f, dp, pvp, parity_stone(d, f, dp, hist), pst)
            mv = d.bnd(f, dp, d.const(f, dp, MOVE, NOMOVE), [("Row", r_), ("Col", c_), ("Stone", stone)])
            p = d.call(f, dp, "Game_Place_Stone.vi", [("Board State", bs), ("Move", mv), ("Renju", renju),
                                                      ("error in", d.noerr(f, dp))],
                       ["Board State out", "Placed?", "Win?", "Win Line", "Forbidden Reason", "Draw?", "error out"])
            placed, win, draw = p["Placed?"], p["Win?"], p["Draw?"]
            over = d.or_(f, dp, win, draw)
            cont = d.and_(f, dp, placed, d.not_(f, dp, over))
            need_ai = d.and_(f, dp, cont, d.not_(f, dp, pvp))
            isb = d.eq(f, dp, stone, d.const(f, dp, STONE, BLACK))
            one = d.i32(f, dp, 1)
            s1w = d.and_(f, dp, win, d.or_(f, dp, d.not_(f, dp, pvp), isb))
            s2w = d.and_(f, dp, win, d.and_(f, dp, pvp, d.not_(f, dp, isb)))
            d.label(f, dp, "점수: AI대전=플레이어/AI, 2인=흑/백")
            st2 = d.sel(f, dp, over, stat(d, f, dp, OVER),
                        d.sel(f, dp, placed, d.sel(f, dp, pvp, stat(d, f, dp, PTURN), stat(d, f, dp, AITH)),
                              stat(d, f, dp, PTURN)))
            fr = p["Forbidden Reason"]
            ftxt = d.sel(f, dp, d.eq(f, dp, fr, d.const(f, dp, FORB, "1")), s(d, f, dp, "금수 자리 (3-3)"),
                         d.sel(f, dp, d.eq(f, dp, fr, d.const(f, dp, FORB, "2")), s(d, f, dp, "금수 자리 (4-4)"),
                               d.sel(f, dp, d.eq(f, dp, fr, d.const(f, dp, FORB, "3")), s(d, f, dp, "금수 자리 (장목)"),
                                     s(d, f, dp, "둘 수 없는 자리입니다"))))
            wtxt = d.sel(f, dp, pvp, d.sel(f, dp, isb, s(d, f, dp, "흑 승리!"), s(d, f, dp, "백 승리!")),
                         s(d, f, dp, "승리! 축하합니다"))
            ctxt = d.sel(f, dp, pvp, turn_text(d, f, dp, opp_stone(d, f, dp, stone)), s(d, f, dp, "AI 생각 중..."))
            txt = d.sel(f, dp, win, wtxt, d.sel(f, dp, draw, s(d, f, dp, "무승부"), d.sel(f, dp, placed, ctxt, ftxt)))
            col_ = d.sel(f, dp, win, u32(d, f, dp, GREEN), d.sel(f, dp, placed, u32(d, f, dp, INK), u32(d, f, dp, ORANGE)))
            out = d.bnd(f, dp, c, [
                ("Board", p["Board State out"]), ("Status", st2), ("Hover", d.const(f, dp, MOVE, NOMOVE)),
                ("Win Line", d.sel(f, dp, win, p["Win Line"], wl)),
                ("Score 1", d.sel(f, dp, s1w, d.add(f, dp, s1, one), s1)),
                ("Score 2", d.sel(f, dp, s2w, d.add(f, dp, s2, one), s2)),
                ("Draws", d.sel(f, dp, draw, d.add(f, dp, dr, one), dr)),
                ("Status Text", txt), ("Status Color", col_)])
            return [out, need_ai]
        return guarded(d, fu, dep, turn_ok, ctx, [row, col], 2, yes, "착수", "무시",
                       lambda f2, d2: [d.b(f2, d2, False)])

    subvi(d, [CTXIN, ("Row", "int32", "-1", "r5", "required"), ("Col", "int32", "-1", "r7", "required")],
          [CTXOUT, ("Need AI", "bool", "false", "r6")], body)
    return d.write(f"{OUT}/Game_Board_Click.xml", "Game_Board_Click.vi",
                   "바둑판 (Row,Col) 클릭 처리. 2인 플레이는 수순(짝/홀)으로 흑/백 결정, AI 대전은 Player Stone.\\0A"
                   "승/무/금수/차례 문구와 점수를 갱신하고, AI 대전에서 게임이 계속되면 Need AI = True.")


# ---------------------------------------------------------------- Game_Undo_Move
def undo_move():
    d = Doc()

    def body(fu, dep, ins):
        ctx = ins[0]
        scr, st = d.unb(fu, dep, ctx, ["Screen", "Status"])
        ok = d.and_(fu, dep, d.eq(fu, dep, scr, d.const(fu, dep, SCREEN, "1")),
                    d.or_(fu, dep, d.eq(fu, dep, st, stat(d, fu, dep, PTURN)), d.eq(fu, dep, st, stat(d, fu, dep, OVER))))
        d.label(fu, dep, "AI 생각 중에는 무르기 안 함")

        def yes(f, dp, j):
            c = j[0]
            sets, bs, pst, gid = d.unb(f, dp, c, ["Settings", "Board", "Player Stone", "Game ID"])
            pvp = is_pvp(d, f, dp, sets)
            hist, last = d.unb(f, dp, bs, ["Move History", "Last Move"])
            n = d.size(f, dp, hist)
            lst = d.unb(f, dp, last, ["Stone"])[0]
            one, two, zero = d.i32(f, dp, 1), d.i32(f, dp, 2), d.i32(f, dp, 0)
            cnt = d.sel(f, dp, d.eq(f, dp, lst, pst), one, two)
            keep = d.sel(f, dp, d.eq(f, dp, pst, d.const(f, dp, STONE, WHITE)), one, zero)
            avail = d.max_(f, dp, d.sub(f, dp, n, keep), zero)
            cnt = d.node(f, dp, "Max & Min", [("x", cnt), ("y", avail)], ["max(x\\2Cy)", "min(x\\2Cy)"])["min(x\\2Cy)"]
            cnt = d.sel(f, dp, pvp, one, cnt)
            d.label(f, dp, "2인: 1수, AI대전: 내 마지막 수까지")
            u = d.call(f, dp, "Game_Undo.vi", [("Board State", bs), ("Count", cnt), ("error in", d.noerr(f, dp))],
                       ["Board State out", "Undone", "error out"])
            h2 = d.unb(f, dp, u["Board State out"], ["Move History"])[0]
            txt = d.sel(f, dp, pvp, turn_text(d, f, dp, parity_stone(d, f, dp, h2)), s(d, f, dp, "무르기: 당신 차례"))
            out = d.bnd(f, dp, c, [("Board", u["Board State out"]), ("Status", stat(d, f, dp, PTURN)),
                                   ("Game ID", d.node(f, dp, "Increment", [("x", gid)], ["x+1"])["x+1"]),
                                   ("Win Line", d.const(f, dp, MOVES, "[]")), ("Status Text", txt),
                                   ("Status Color", u32(d, f, dp, INK))])
            return [out]
        return guarded(d, fu, dep, ok, ctx, [], 1, yes, "무르기", "무시", lambda f2, d2: [])

    subvi(d, [CTXIN], [CTXOUT], body)
    return d.write(f"{OUT}/Game_Undo_Move.xml", "Game_Undo_Move.vi",
                   "무르기 버튼: 2인 플레이는 1수, AI 대전은 플레이어 차례가 되도록 1~2수(AI 흑 첫 수는 유지).\\0A"
                   "Game ID를 올려 계산 중이던 AI 결과를 버린다.")


# ---------------------------------------------------------------- Game_AI_Move
def ai_move():
    d = Doc()

    def body(fu, dep, ins):
        ctx, mv, mgid = ins
        st, gid = d.unb(fu, dep, ctx, ["Status", "Game ID"])
        cur = d.and_(fu, dep, d.eq(fu, dep, mgid, gid), d.eq(fu, dep, st, stat(d, fu, dep, AITH)))
        d.label(fu, dep, "Game ID가 다르면 지난 판 결과: 버림")

        def yes(f, dp, j):
            c, m = j
            sets, bs, wl, s2, dr = d.unb(f, dp, c, ["Settings", "Board", "Win Line", "Score 2", "Draws"])
            renju = d.eq(f, dp, setting(d, f, dp, sets, 3), d.i32(f, dp, 1))
            p = d.call(f, dp, "Game_Place_Stone.vi", [("Board State", bs), ("Move", m), ("Renju", renju),
                                                      ("error in", d.noerr(f, dp))],
                       ["Board State out", "Placed?", "Win?", "Win Line", "Forbidden Reason", "Draw?", "error out"])
            win, draw = p["Win?"], p["Draw?"]
            over = d.or_(f, dp, win, draw)
            one = d.i32(f, dp, 1)
            txt = d.sel(f, dp, win, s(d, f, dp, "AI 승리... 다시 도전!"),
                        d.sel(f, dp, draw, s(d, f, dp, "무승부"), s(d, f, dp, "당신 차례")))
            col_ = d.sel(f, dp, win, u32(d, f, dp, RED_T), u32(d, f, dp, INK))
            out = d.bnd(f, dp, c, [("Board", p["Board State out"]),
                                   ("Status", d.sel(f, dp, over, stat(d, f, dp, OVER), stat(d, f, dp, PTURN))),
                                   ("Win Line", d.sel(f, dp, win, p["Win Line"], wl)),
                                   ("Score 2", d.sel(f, dp, win, d.add(f, dp, s2, one), s2)),
                                   ("Draws", d.sel(f, dp, draw, d.add(f, dp, dr, one), dr)),
                                   ("Status Text", txt), ("Status Color", col_)])
            return [out]
        return guarded(d, fu, dep, cur, ctx, [mv], 1, yes, "AI 착수", "버림", lambda f2, d2: [])

    subvi(d, [CTXIN, ("Move", MOVE, NOMOVE, "r5", "required"), ("Game ID", "uint32", "0", "r7", "required")],
          [CTXOUT], body)
    return d.write(f"{OUT}/Game_AI_Move.xml", "Game_AI_Move.vi",
                   "AI 착수 결과 반영. Game ID가 현재 판과 같고 AI 차례일 때만 둔다. AI 승리면 Score 2 증가.")


# ---------------------------------------------------------------- Game_Click
def click():
    d = Doc()

    def body(fu, dep, ins):
        ctx, x, y = ins
        scr, sets = d.unb(fu, dep, ctx, ["Screen", "Settings"])
        on_settings = d.eq(fu, dep, scr, d.const(fu, dep, SCREEN, "0"))
        d.label(fu, dep, "화면별 클릭 처리")

        def settings(f, dp, j):
            c, xx, yy, ss = j
            pvp = is_pvp(d, f, dp, ss)
            dims = d.node(f, dp, "Build Array", [("element", d.b(f, dp, False)), ("element", pvp), ("element", pvp)],
                          ["appended array"])["appended array"]
            specs = d.call(f, dp, "UI_Settings_Layout.vi", [("error in", d.noerr(f, dp))], ["Specs", "error out"])["Specs"]
            h = d.call(f, dp, "UI_Hit_Test.vi", [("X", xx), ("Y", yy), ("Specs", specs), ("Dim Groups", dims),
                                                ("error in", d.noerr(f, dp))], ["Index", "Group", "Value", "error out"])
            is_start = d.eq(f, dp, h["Group"], d.i32(f, dp, 4))

            def go(f2, d2, k):
                g = d.call(f2, d2, "Game_Start.vi", [("Context", k[0]), ("Reset Scores", d.b(f2, d2, True)),
                                                     ("error in", d.noerr(f2, d2))], ["Context out", "Need AI", "error out"])
                return [g["Context out"], g["Need AI"]]

            def pick(f2, d2, k):
                c2, ss2, g_, v_ = k
                ns = d.node(f2, d2, "Replace Array Subset", [("array", ss2), ("index", g_), ("new element/subarray", v_)],
                            ["output array"])["output array"]
                return [d.bnd(f2, d2, c2, [("Settings", ns)]), d.b(f2, d2, False)]
            d.label(f, dp, "Group 0~3: 선택 변경, 4: 게임 시작")
            return d.case(f, dp, is_start, [c, ss, h["Group"], h["Value"]], 2,
                          [("True", "게임 시작", go), ("False", "설정 선택", pick)])

        def game(f, dp, j):
            c, xx, yy, ss = j
            specs = d.call(f, dp, "UI_Game_Layout.vi", [("error in", d.noerr(f, dp))], ["Specs", "error out"])["Specs"]
            h = d.call(f, dp, "UI_Hit_Test.vi", [("X", xx), ("Y", yy), ("Specs", specs), ("error in", d.noerr(f, dp))],
                       ["Index", "Group", "Value", "error out"])
            is_btn = d.eq(f, dp, h["Group"], d.i32(f, dp, 5))

            def btn(f2, d2, k):
                c2, v = k[0], k[3]

                def undo(f3, d3, q):
                    u = d.call(f3, d3, "Game_Undo_Move.vi", [("Context", q[0]), ("error in", d.noerr(f3, d3))],
                               ["Context out", "error out"])
                    return [u["Context out"], d.b(f3, d3, False)]

                def other(f3, d3, q):
                    def new(f4, d4, w):
                        g = d.call(f4, d4, "Game_Start.vi", [("Context", w[0]), ("Reset Scores", d.b(f4, d4, False)),
                                                             ("error in", d.noerr(f4, d4))],
                                   ["Context out", "Need AI", "error out"])
                        return [g["Context out"], g["Need AI"]]

                    def back(f4, d4, w):
                        gid = d.unb(f4, d4, w[0], ["Game ID"])[0]
                        o = d.bnd(f4, d4, w[0], [("Screen", d.const(f4, d4, SCREEN, "0")), ("Status", stat(d, f4, d4, IDLE)),
                                                 ("Hover Button", d.i32(f4, d4, -1)),
                                                 ("Game ID", d.node(f4, d4, "Increment", [("x", gid)], ["x+1"])["x+1"])])
                        return [o, d.b(f4, d4, False)]
                    return d.case(f3, d3, d.eq(f3, d3, q[1], d.i32(f3, d3, 1)), [q[0]], 2,
                                  [("True", "새 게임", new), ("False", "설정 화면으로", back)])
                return d.case(f2, d2, d.eq(f2, d2, v, d.i32(f2, d2, 0)), [c2, v], 2,
                              [("True", "무르기", undo), ("False", "새 게임 / 설정", other)])

            def board(f2, d2, k):
                c2, xx2, yy2 = k[0], k[1], k[2]
                pt = d.bnd(f2, d2, d.const(f2, d2, "cluster{int32.X,int32.Y}", "[0,0]"), [("X", xx2), ("Y", yy2)])
                g = d.call(f2, d2, "UI_Pixel_To_Grid.vi", [("Coords", pt), ("error in", d.noerr(f2, d2))],
                           ["Row", "Col", "Valid", "error out"])

                def place(f3, d3, q):
                    b = d.call(f3, d3, "Game_Board_Click.vi", [("Context", q[0]), ("Row", q[1]), ("Col", q[2]),
                                                               ("error in", d.noerr(f3, d3))],
                               ["Context out", "Need AI", "error out"])
                    return [b["Context out"], b["Need AI"]]
                return d.case(f2, d2, g["Valid"], [c2, g["Row"], g["Col"]], 2,
                              [("True", "바둑판 착수", place), ("False", "빈 곳", lambda f3, d3, q: [q[0], d.b(f3, d3, False)])])
            d.label(f, dp, "버튼(Group 5) 아니면 바둑판")
            return d.case(f, dp, is_btn, [c, xx, yy, h["Value"]], 2,
                          [("True", "버튼", btn), ("False", "바둑판", board)])
        return d.case(fu, dep, on_settings, [ctx, x, y, sets], 2,
                      [("True", "설정 화면", settings), ("False", "게임 화면", game)])

    subvi(d, [CTXIN, ("X", "int32", "0", "r5", "required"), ("Y", "int32", "0", "r7", "required")],
          [CTXOUT, ("Need AI", "bool", "false", "r6")], body)
    return d.write(f"{OUT}/Game_Click.xml", "Game_Click.vi",
                   "마우스 클릭 (X,Y) 처리. 설정 화면: 모드/선공/난이도/규칙 선택, 게임 시작.\\0A"
                   "게임 화면: 무르기/새 게임/설정 버튼, 그 외는 바둑판 착수. Need AI = AI에게 계산 요청 필요.")


# ---------------------------------------------------------------- Game_Hover
def hover():
    d = Doc()

    def body(fu, dep, ins):
        ctx, x, y = ins
        scr, sets, st, hv, hb = d.unb(fu, dep, ctx, ["Screen", "Settings", "Status", "Hover", "Hover Button"])
        on_settings = d.eq(fu, dep, scr, d.const(fu, dep, SCREEN, "0"))
        d.label(fu, dep, "버튼 위 / 바둑판 칸 위 표시")

        def settings(f, dp, j):
            c, xx, yy, ss, st_ = j
            pvp = is_pvp(d, f, dp, ss)
            dims = d.node(f, dp, "Build Array", [("element", d.b(f, dp, False)), ("element", pvp), ("element", pvp)],
                          ["appended array"])["appended array"]
            specs = d.call(f, dp, "UI_Settings_Layout.vi", [("error in", d.noerr(f, dp))], ["Specs", "error out"])["Specs"]
            h = d.call(f, dp, "UI_Hit_Test.vi", [("X", xx), ("Y", yy), ("Specs", specs), ("Dim Groups", dims),
                                                ("error in", d.noerr(f, dp))], ["Index", "Group", "Value", "error out"])
            return [h["Index"], d.const(f, dp, MOVE, NOMOVE)]

        def game(f, dp, j):
            c, xx, yy, ss, st_ = j
            specs = d.call(f, dp, "UI_Game_Layout.vi", [("error in", d.noerr(f, dp))], ["Specs", "error out"])["Specs"]
            h = d.call(f, dp, "UI_Hit_Test.vi", [("X", xx), ("Y", yy), ("Specs", specs), ("error in", d.noerr(f, dp))],
                       ["Index", "Group", "Value", "error out"])
            pt = d.bnd(f, dp, d.const(f, dp, "cluster{int32.X,int32.Y}", "[0,0]"), [("X", xx), ("Y", yy)])
            g = d.call(f, dp, "UI_Pixel_To_Grid.vi", [("Coords", pt), ("error in", d.noerr(f, dp))],
                       ["Row", "Col", "Valid", "error out"])
            show = d.and_(f, dp, g["Valid"], d.eq(f, dp, st_, stat(d, f, dp, PTURN)))
            m = d.bnd(f, dp, d.const(f, dp, MOVE, NOMOVE), [("Row", g["Row"]), ("Col", g["Col"])])
            return [h["Index"], d.sel(f, dp, show, m, d.const(f, dp, MOVE, NOMOVE))]
        o = d.case(fu, dep, on_settings, [ctx, x, y, sets, st], 2,
                   [("True", "설정 화면", settings), ("False", "게임 화면", game)])
        nb, nh = o
        r0, c0 = d.unb(fu, dep, hv, ["Row", "Col"])
        r1, c1 = d.unb(fu, dep, nh, ["Row", "Col"])
        changed = d.or_(fu, dep, d.ne(fu, dep, nb, hb), d.or_(fu, dep, d.ne(fu, dep, r0, r1), d.ne(fu, dep, c0, c1)))
        return [d.bnd(fu, dep, ctx, [("Hover Button", nb), ("Hover", nh)]), changed]

    subvi(d, [CTXIN, ("X", "int32", "0", "r5", "required"), ("Y", "int32", "0", "r7", "required")],
          [CTXOUT, ("Changed", "bool", "false", "r6")], body)
    return d.write(f"{OUT}/Game_Hover.xml", "Game_Hover.vi",
                   "마우스 이동 (X,Y): 버튼 강조(Hover Button)와 바둑판 미리보기(Hover)를 갱신. Changed = 다시 그릴 필요.")


if __name__ == "__main__":
    for fn in (start, board_click, undo_move, ai_move, click, hover):
        print(fn.__name__, fn())
