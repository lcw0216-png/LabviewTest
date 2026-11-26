import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]


def place_stone():
    d = Doc()

    def body(fu, dep, ins):
        bs, move, renju = ins
        grid, hist = d.unb(fu, dep, bs, ["Grid", "Move History"])
        r, c, st = d.unb(fu, dep, move, ["Row", "Col", "Stone"])
        lo, hi = d.i32(fu, dep, 0), d.i32(fu, dep, 14)
        inr = d.and_(fu, dep, d.inrange(fu, dep, r, lo, hi), d.inrange(fu, dep, c, lo, hi))
        empty = d.and_(fu, dep, inr, d.eq(fu, dep, d.idx2(fu, dep, grid, r, c), d.const(fu, dep, STONE, EMPTY)))
        fb = d.call(fu, dep, "Rule_Check_Forbidden.vi", [("Grid", grid), ("Move", move), ("Renju", renju),
                                                         ("error in", d.noerr(fu, dep))],
                    ["Forbidden?", "Reason", "error out"])
        ok = d.and_(fu, dep, empty, d.not_(fu, dep, fb["Forbidden?"]))
        d.label(fu, dep, "보드 안 빈 칸이고 금수가 아니면 착수")

        def yes(f2, d2, j):
            b, g, h, m, rr, cc, s, rj = j
            g2 = d.rep2(f2, d2, g, rr, cc, s)
            h2 = d.node(f2, d2, "Build Array", [("array", h), ("element", m)], ["appended array"],
                        concat="true")["appended array"]
            b2 = d.bnd(f2, d2, b, [("Grid", g2), ("Move History", h2), ("Last Move", m)])
            exact = d.and_(f2, d2, rj, d.eq(f2, d2, s, d.const(f2, d2, STONE, BLACK)))
            w = d.call(f2, d2, "Rule_Check_Win.vi", [("Grid", g2), ("Last Move", m), ("Exact Five", exact),
                                                     ("error in", d.noerr(f2, d2))],
                       ["Win?", "Win Line", "Run Length", "error out"])
            full = d.ge(f2, d2, d.size(f2, d2, h2), d.i32(f2, d2, 225))
            draw = d.and_(f2, d2, full, d.not_(f2, d2, w["Win?"]))
            d.label(f2, d2, "렌주룰 흑은 정확히 5목만 승리")
            return [b2, d.b(f2, d2, True), w["Win?"], w["Win Line"], draw]

        def no(f2, d2, j):
            return [j[0], d.b(f2, d2, False), d.b(f2, d2, False), d.const(f2, d2, MOVES, "[]"), d.b(f2, d2, False)]
        o = d.case(fu, dep, ok, [bs, grid, hist, move, r, c, st, renju], 5,
                   [("True", "착수", yes), ("False", "착수 불가", no)])
        reason = d.sel(fu, dep, empty, fb["Reason"], d.const(fu, dep, FORB, "0"))
        return o[:4] + [reason, o[4]]

    subvi(d, [("Board State", BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]", "r0", "required"),
              ("Move", MOVE, "[7,7,1]", "r5", "required"),
              ("Renju", "bool", "true", "r7", "recommended")],
          [("Board State out", BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]", "r4"),
           ("Placed?", "bool", "false", "r6"), ("Win?", "bool", "false", "r8"), ("Win Line", MOVES, "[]", "r10"),
           ("Forbidden Reason", FORB, "0", "r14"), ("Draw?", "bool", "false", "r3")], body)
    return d.write(f"{OUT}/Game_Place_Stone.xml", "Game_Place_Stone.vi",
                   "착수 처리: 범위/빈 칸/렌주 금수 검사 후 Grid, Move History, Last Move 갱신, 승리/무승부 판정.\\0A"
                   "Placed?=False면 Board State는 그대로, Forbidden Reason에 금수 사유.")


def undo():
    d = Doc()
    NOMOVE = "[-1,-1,0]"

    def body(fu, dep, ins):
        bs, cnt = ins
        d.label(fu, dep, "Count 수만큼 마지막 착수를 되돌린다")

        def lb(lu, ld, i, L, it):
            b, n_done = L
            g, h = d.unb(lu, ld, b, ["Grid", "Move History"])
            n = d.size(lu, ld, h)
            has = d.gt(lu, ld, n, d.i32(lu, ld, 0))

            def yes(f2, d2, j):
                bb, gg, hh, nn, k = j
                li = d.sub(f2, d2, nn, d.i32(f2, d2, 1))
                r, c = d.unb(f2, d2, d.idx1(f2, d2, hh, li), ["Row", "Col"])
                g2 = d.rep2(f2, d2, gg, r, c, d.const(f2, d2, STONE, EMPTY))
                h2 = d.node(f2, d2, "Delete From Array", [("array", hh), ("length", d.i32(f2, d2, 1)), ("index", li)],
                            ["array w/ subset deleted", "deleted portion"])["array w/ subset deleted"]
                return [d.bnd(f2, d2, bb, [("Grid", g2), ("Move History", h2)]), d.add(f2, d2, k, d.i32(f2, d2, 1))]
            o = d.case(lu, ld, has, [b, g, h, n, n_done], 2,
                       [("True", "하나 되돌림", yes), ("False", "기록 없음", lambda f2, d2, j: [j[0], j[4]])])
            return [], o, None
        _, fin = d.loop("For Loop", fu, dep, [], [bs, d.i32(fu, dep, 0)], lb, maxin=cnt)
        h = d.unb(fu, dep, fin[0], ["Move History"])[0]
        n = d.size(fu, dep, h)
        last = d.sel(fu, dep, d.gt(fu, dep, n, d.i32(fu, dep, 0)), d.idx1(fu, dep, h, d.sub(fu, dep, n, d.i32(fu, dep, 1))),
                     d.const(fu, dep, MOVE, NOMOVE))
        d.label(fu, dep, "Last Move 재설정(기록 없으면 -1,-1)")
        return [d.bnd(fu, dep, fin[0], [("Last Move", last)]), fin[1]]

    subvi(d, [("Board State", BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]", "r0", "required"),
              ("Count", "int32", "2", "r5", "recommended")],
          [("Board State out", BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]", "r4"),
           ("Undone", "int32", "0", "r6")], body)
    return d.write(f"{OUT}/Game_Undo.xml", "Game_Undo.vi",
                   "무르기: Move History 끝에서 Count개를 지우고 Grid 칸을 비운다(기본 2 = 플레이어+AI 한 수씩).\\0A"
                   "Undone = 실제로 되돌린 수.")


for f in (place_stone, undo):
    print(f.__name__, f())
