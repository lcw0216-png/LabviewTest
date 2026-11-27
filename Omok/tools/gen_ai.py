import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
DIRS = "[[0,1],[1,0],[1,1],[1,-1]]"
CD = "Rule_Count_Direction.vi"


# ---------------------------------------------------------------- AI_Get_Candidates
def get_candidates():
    d = Doc()

    def body(fu, dep, ins):
        grid = ins[0]
        n225 = d.i32(fu, dep, 225)
        d.label(fu, dep, "빈 칸 중 반경 2 안에 돌이 있는 칸만 후보")

        def lb(lu, ld, i, L, it):
            g = i[0]
            r, c = qr(d, lu, ld, it, d.i32(lu, ld, 15))
            empty = d.const(lu, ld, STONE, EMPTY)
            here_empty = d.eq(lu, ld, d.idx2(lu, ld, g, r, c), empty)

            def nb(nu, nd, j, L2, k):
                gg, rr, cc = j
                a, b_ = qr(d, nu, nd, k, d.i32(nu, nd, 5))
                two = d.i32(nu, nd, 2)
                nr = d.add(nu, nd, rr, d.sub(nu, nd, a, two))
                nc = d.add(nu, nd, cc, d.sub(nu, nd, b_, two))
                cell = d.idx2(nu, nd, gg, nr, nc)
                hit = d.ne(nu, nd, cell, d.const(nu, nd, STONE, EMPTY))
                return [], [d.or_(nu, nd, L2[0], hit)], None
            _, fin = d.loop("For Loop", lu, ld, [(g, None), (r, None), (c, None)], [d.b(lu, ld, False)], nb,
                            maxin=d.i32(lu, ld, 25))
            d.label(lu, ld, "5x5 이웃 검사(범위 밖 Index는 Empty)")
            cand = d.and_(lu, ld, here_empty, fin[0])
            return [(r, "index", cand), (c, "index", cand)], [], None
        outs, _ = d.loop("For Loop", fu, dep, [(grid, None)], [], lb, maxin=n225)
        n = d.size(fu, dep, outs[0])
        none = d.eq(fu, dep, n, d.i32(fu, dep, 0))
        seven = d.const(fu, dep, "array{int32}", "[7]")
        d.label(fu, dep, "빈 보드면 천원(7,7)")
        rows = d.sel(fu, dep, none, seven, outs[0])
        cols = d.sel(fu, dep, none, seven, outs[1])
        return [rows, cols, d.size(fu, dep, rows)]

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required")],
          [("Rows", "array{int32}", "[]", 3), ("Cols", "array{int32}", "[]", 2), ("Count", "int32", "0", 1)], body)
    return d.write(f"{OUT}/AI_Get_Candidates.xml", "AI_Get_Candidates.vi",
                   "후보 수 생성: 빈 칸 중 반경 2(5x5) 안에 돌이 하나라도 있는 칸. 빈 보드면 (7,7) 하나.")


# ---------------------------------------------------------------- AI_Evaluate_Point
def evaluate_point():
    d = Doc()

    def body(fu, dep, ins):
        grid, move = ins
        dirs = d.const(fu, dep, "array{" + DIR + "}", DIRS, name="Directions")
        t2 = d.const(fu, dep, "array{double}", "[0,10,100,1000,10000]", name="Open Both")
        t1 = d.const(fu, dep, "array{double}", "[0,1,10,100,1000]", name="Open One")
        d.label(fu, dep, "Move 칸에 Stone을 둔다고 가정한 패턴 점수 합")

        def lb(lu, ld, i, L, it):
            g, mv, a2, a1, dirc = i
            f = d.call(lu, ld, CD, [("Grid", g), ("Move", mv), ("Direction", dirc), ("error in", d.noerr(lu, ld))],
                       ["Count", "Open End", "error out"])
            dr, dc = d.unb(lu, ld, dirc, ["dR", "dC"])
            ndir = d.bnd(lu, ld, dirc, [("dR", d.neg(lu, ld, dr)), ("dC", d.neg(lu, ld, dc))])
            b = d.call(lu, ld, CD, [("Grid", g), ("Move", mv), ("Direction", ndir), ("error in", d.noerr(lu, ld))],
                       ["Count", "Open End", "error out"])
            one, zero = d.i32(lu, ld, 1), d.i32(lu, ld, 0)
            length = d.add(lu, ld, d.add(lu, ld, f["Count"], b["Count"]), one)
            opens = d.add(lu, ld, d.sel(lu, ld, f["Open End"], one, zero), d.sel(lu, ld, b["Open End"], one, zero))
            v2 = d.idx1(lu, ld, a2, length)
            v1 = d.idx1(lu, ld, a1, length)
            z = d.dbl(lu, ld, 0)
            s = d.sel(lu, ld, d.eq(lu, ld, opens, d.i32(lu, ld, 2)), v2,
                      d.sel(lu, ld, d.eq(lu, ld, opens, one), v1, z))
            s = d.sel(lu, ld, d.ge(lu, ld, length, d.i32(lu, ld, 5)), d.dbl(lu, ld, 100000), s)
            d.label(lu, ld, "5목 100000, 열린4 10000, 닫힌4/열린3 1000 ...")
            return [], [d.add(lu, ld, L[0], s)], None
        _, fin = d.loop("For Loop", fu, dep, [(grid, None), (move, None), (t2, None), (t1, None), (dirs, "index")],
                        [d.dbl(fu, dep, 0)], lb)
        return [fin[0]]

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required"), ("Move", MOVE, "[7,7,1]", 10, "required")],
          [("Score", "double", "0", 3)], body)
    return d.write(f"{OUT}/AI_Evaluate_Point.xml", "AI_Evaluate_Point.vi",
                   "한 칸 평가: Move.Stone을 (Row,Col)에 둔다고 가정하고 4방향 연속 길이와 열린 끝 수로 점수를 합산.\\0A"
                   "5목=100000, 열린4=10000, 닫힌4=1000, 열린3=1000, 닫힌3=100, 열린2=100, 닫힌2=10, 막힌 쪽 0.")


# ---------------------------------------------------------------- AI_Score_Candidates
def score_candidates():
    d = Doc()

    def body(fu, dep, ins):
        grid, ai, w, noise, renju = ins
        cands = d.call(fu, dep, "AI_Get_Candidates.vi", [("Grid", grid), ("error in", d.noerr(fu, dep))],
                       ["Rows", "Cols", "Count", "error out"])
        opp = opp_stone(d, fu, dep, ai)
        d.label(fu, dep, "공격 + 가중치*수비 + 중앙 보너스 + 잡음")

        def lb(lu, ld, i, L, it):
            g, a, o, ww, nz, rj, r, c = i
            base = d.const(lu, ld, MOVE, "[0,0,0]")
            ma = d.bnd(lu, ld, base, [("Row", r), ("Col", c), ("Stone", a)])
            mo = d.bnd(lu, ld, base, [("Row", r), ("Col", c), ("Stone", o)])
            att = d.call(lu, ld, "AI_Evaluate_Point.vi", [("Grid", g), ("Move", ma), ("error in", d.noerr(lu, ld))],
                         ["Score", "error out"])["Score"]
            dfn = d.call(lu, ld, "AI_Evaluate_Point.vi", [("Grid", g), ("Move", mo), ("error in", d.noerr(lu, ld))],
                         ["Score", "error out"])["Score"]
            seven = d.i32(lu, ld, 7)
            ar = d.node(lu, ld, "Absolute Value", [("x", d.sub(lu, ld, r, seven))], ["abs(x)"])["abs(x)"]
            ac = d.node(lu, ld, "Absolute Value", [("x", d.sub(lu, ld, c, seven))], ["abs(x)"])["abs(x)"]
            center = d.mul(lu, ld, d.sub(lu, ld, d.i32(lu, ld, 14), d.add(lu, ld, ar, ac)), d.dbl(lu, ld, 0.5))
            rnd = d.node(lu, ld, "Random Number (0-1)", [], ["number\\3A 0 to 1"])["number\\3A 0 to 1"]
            s = d.add(lu, ld, d.add(lu, ld, att, d.mul(lu, ld, ww, dfn)),
                      d.add(lu, ld, center, d.mul(lu, ld, nz, rnd)))
            fb = d.call(lu, ld, "Rule_Check_Forbidden.vi", [("Grid", g), ("Move", ma), ("Renju", rj),
                                                            ("error in", d.noerr(lu, ld))],
                        ["Forbidden?", "Reason", "error out"])
            s = d.sel(lu, ld, fb["Forbidden?"], d.dbl(lu, ld, -1e9), s)
            d.label(lu, ld, "렌주 금수 칸은 -1e9")
            e = d.bnd(lu, ld, d.const(lu, ld, SC, "[0,0,0]"), [("Score", s), ("Row", r), ("Col", c)])
            return [(e, "index")], [], None
        outs, _ = d.loop("For Loop", fu, dep, [(grid, None), (ai, None), (opp, None), (w, None), (noise, None),
                                                (renju, None), (cands["Rows"], "index"), (cands["Cols"], "index")],
                         [], lb)
        srt = d.node(fu, dep, "Sort 1D Array", [("array", outs[0])], ["sorted array"])["sorted array"]
        rev = d.node(fu, dep, "Reverse 1D Array", [("array", srt)], ["reversed array"])["reversed array"]
        d.label(fu, dep, "점수 내림차순")
        return [rev, d.size(fu, dep, rev)]

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required"),
              ("AI Stone", STONE, WHITE, 10, "required"),
              ("Defense Weight", "double", "0.9", 9, "recommended"),
              ("Noise", "double", "0", "r9", "recommended"),
              ("Renju", "bool", "true", "r12", "recommended")],
          [("Ranked", SCS, "[]", 3), ("Count", "int32", "0", 2)], body)
    return d.write(f"{OUT}/AI_Score_Candidates.xml", "AI_Score_Candidates.vi",
                   "후보 칸마다 공격 점수 + Defense Weight*수비 점수 + 중앙 보너스 + Noise*난수를 계산해 내림차순 정렬.\\0A"
                   "렌주룰에서 AI가 흑이면 금수 칸은 -1e9로 밀어낸다.")


# ---------------------------------------------------------------- AI_Calculate_Move
def calculate_move():
    d = Doc()
    SCV = "AI_Score_Candidates.vi"

    def score(p, dep, g, st, w, nz, rj):
        o = d.call(p, dep, SCV, [("Grid", g), ("AI Stone", st), ("Defense Weight", w), ("Noise", nz),
                                 ("Renju", rj), ("error in", d.noerr(p, dep))], ["Ranked", "Count", "error out"])
        return o["Ranked"], o["Count"]

    def body(fu, dep, ins):
        grid, ai, diff, renju = ins
        easy = d.eq(fu, dep, diff, d.const(fu, dep, DIFF, "0"))
        master = d.eq(fu, dep, diff, d.const(fu, dep, DIFF, "3"))
        hard = d.or_(fu, dep, d.eq(fu, dep, diff, d.const(fu, dep, DIFF, "2")), master)
        topk = d.sel(fu, dep, master, d.i32(fu, dep, 12), d.i32(fu, dep, 6))
        w = d.sel(fu, dep, easy, d.dbl(fu, dep, 0.6), d.dbl(fu, dep, 0.9))
        nz = d.sel(fu, dep, easy, d.dbl(fu, dep, 400), d.dbl(fu, dep, 2))
        d.label(fu, dep, "Easy: 수비0.6+큰 잡음, 그 외 수비0.9")
        ranked, cnt = score(fu, dep, grid, ai, w, nz, renju)
        opp = opp_stone(d, fu, dep, ai)

        def greedy(f2, d2, j):
            return [d.idx1(f2, d2, j[0], d.i32(f2, d2, 0))]

        def look(f2, d2, j):
            rk, g, a, o, rj, n, kk = j
            la = d.call(f2, d2, "AI_Lookahead.vi", [("Ranked", rk), ("Grid", g), ("AI Stone", a), ("Renju", rj), ("Top K", kk),
                                                     ("error in", d.noerr(f2, d2))], ["Best", "error out"])
            return [la["Best"]]
        best = d.case(fu, dep, hard, [ranked, grid, ai, opp, renju, cnt, topk], 1,
                      [("True", "Hard / Master", look), ("False", "Easy / Normal", greedy)])[0]
        s, r, c = d.unb(fu, dep, best, ["Score", "Row", "Col"])
        mv = d.bnd(fu, dep, d.const(fu, dep, MOVE, "[-1,-1,0]"), [("Row", r), ("Col", c), ("Stone", ai)])
        valid = d.gt(fu, dep, cnt, d.i32(fu, dep, 0))
        return [mv, s, valid]

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required"),
              ("AI Stone", STONE, WHITE, 10, "required"),
              ("Difficulty", DIFF, "1", 9, "recommended"),
              ("Renju", "bool", "true", "r9", "recommended")],
          [("Move", MOVE, "[-1,-1,0]", 3), ("Score", "double", "0", 2), ("Valid", "bool", "false", 1)], body)
    return d.write(f"{OUT}/AI_Calculate_Move.xml", "AI_Calculate_Move.vi",
                   "AI 착수 결정. Easy=탐욕+큰 잡음, Normal=탐욕(공격+0.9*수비), Hard=상위 6후보, Master=상위 12후보에 상대 최선 응수를 빼는 2수 탐색.\\0A"
                   "Valid=False면 둘 곳이 없음(무승부).")


def lookahead():
    d = Doc()
    SCV = "AI_Score_Candidates.vi"

    def body(fu, dep, ins):
        rk, g, a, rj, topk = ins
        o = opp_stone(d, fu, dep, a)
        n = d.size(fu, dep, rk)
        k = d.node(fu, dep, "Max & Min", [("x", n), ("y", topk)],
                   ["max(x\\2Cy)", "min(x\\2Cy)"])["min(x\\2Cy)"]
        top = d.node(fu, dep, "Array Subset", [("array", rk), ("index", d.i32(fu, dep, 0)), ("length", k)],
                     ["subarray"])["subarray"]
        d.label(fu, dep, "상위 K수마다 상대 최선 응수 점수를 뺀다")

        def lb(lu, ld, i, L, it):
            gg, aa, oo, rr, e = i
            bv, be = L
            s, r, c = d.unb(lu, ld, e, ["Score", "Row", "Col"])
            g2 = d.rep2(lu, ld, gg, r, c, aa)
            orank = d.call(lu, ld, SCV, [("Grid", g2), ("AI Stone", oo), ("Defense Weight", d.dbl(lu, ld, 0.9)),
                                         ("Noise", d.dbl(lu, ld, 0)), ("Renju", rr), ("error in", d.noerr(lu, ld))],
                           ["Ranked", "Count", "error out"])["Ranked"]
            ob = d.unb(lu, ld, d.idx1(lu, ld, orank, d.i32(lu, ld, 0)), ["Score"])[0]
            v = d.sub(lu, ld, s, d.mul(lu, ld, ob, d.dbl(lu, ld, 0.8)))
            v = d.sel(lu, ld, d.ge(lu, ld, s, d.dbl(lu, ld, 100000)), d.dbl(lu, ld, 1e7), v)
            d.label(lu, ld, "내 5목이면 즉시 선택")
            better = d.gt(lu, ld, v, bv)
            return [], [d.sel(lu, ld, better, v, bv), d.sel(lu, ld, better, e, be)], None
        _, fin = d.loop("For Loop", fu, dep, [(g, None), (a, None), (o, None), (rj, None), (top, "index")],
                        [d.dbl(fu, dep, -1e12), d.idx1(fu, dep, rk, d.i32(fu, dep, 0))], lb)
        return [fin[1], fin[0]]

    subvi(d, [("Ranked", SCS, "[]", 11, "required"),
              ("Grid", GRID, EMPTY_GRID, 10, "required"),
              ("AI Stone", STONE, WHITE, 9, "required"),
              ("Renju", "bool", "true", "r9", "recommended"),
              ("Top K", "int32", "6", "r1", "recommended")],
          [("Best", SC, "[0,0,0]", 3), ("Value", "double", "0", 2)], body)
    return d.write(f"{OUT}/AI_Lookahead.xml", "AI_Lookahead.vi",
                   "Hard/Master 2수 탐색: Ranked 상위 K수(Hard 6, Master 12)를 각각 가상 착수 후 상대의 최선 응수 점수*0.8을 뺀 값이 최대인 수.\\0A"
                   "내 수가 5목(>=100000)이면 즉시 그 수.")


for f in (get_candidates, evaluate_point, score_candidates, lookahead, calculate_move):
    print(f.__name__, f())
