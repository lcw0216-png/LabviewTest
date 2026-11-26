import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
DIRS = "[[0,1],[1,0],[1,1],[1,-1]]"


# ---------------------------------------------------------------- Rule_Count_Direction
def count_direction():
    d = Doc()

    def body(fu, dep, ins):
        grid, move, dirc = ins
        row, col, stone = d.unb(fu, dep, move, ["Row", "Col", "Stone"])
        dr, dc = d.unb(fu, dep, dirc, ["dR", "dC"])
        r0 = d.add(fu, dep, row, dr)
        c0 = d.add(fu, dep, col, dc)
        zero = d.i32(fu, dep, 0)
        d.label(fu, dep, "(Row,Col) 다음 칸부터 같은 돌이 끝날 때까지 전진")

        def lb(lu, ld, i, L, it):
            g, ddr, ddc, st_ = i
            r, c, n = L
            lo, hi = d.i32(lu, ld, 0), d.i32(lu, ld, 14)
            inr = d.and_(lu, ld, d.inrange(lu, ld, r, lo, hi), d.inrange(lu, ld, c, lo, hi))
            cell = d.idx2(lu, ld, g, r, c)
            same = d.and_(lu, ld, inr, d.eq(lu, ld, cell, st_))
            empty = d.const(lu, ld, STONE, EMPTY)
            openend = d.and_(lu, ld, inr, d.eq(lu, ld, cell, empty))
            one = d.i32(lu, ld, 1)
            r2 = d.sel(lu, ld, same, d.add(lu, ld, r, ddr), r)
            c2 = d.sel(lu, ld, same, d.add(lu, ld, c, ddc), c)
            n2 = d.sel(lu, ld, same, d.add(lu, ld, n, one), n)
            stop = d.not_(lu, ld, same)
            return [(openend, None)], [r2, c2, n2], stop
        outs, fin = d.loop("While Loop", fu, dep, [(grid, None), (dr, None), (dc, None), (stone, None)],
                           [r0, c0, zero], lb)
        return [fin[2], outs[0]]

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required"),
              ("Move", MOVE, "[7,7,1]", 10, "required"),
              ("Direction", DIR, "[0,1]", 9, "required")],
          [("Count", "int32", "0", 3), ("Open End", "bool", "false", 2)], body)
    return d.write(f"{OUT}/Rule_Count_Direction.xml", "Rule_Count_Direction.vi",
                   "Move 위치에서 Direction(dR,dC) 방향으로 같은 색 돌이 몇 개 연속되는지 센다(시작 칸 제외).\\0A"
                   "Open End = 연속이 끝난 다음 칸이 보드 안의 빈 칸이면 True.")


# ---------------------------------------------------------------- Rule_Check_Win
def check_win():
    d = Doc()
    CD = "Rule_Count_Direction.vi"

    def body(fu, dep, ins):
        grid, move, exact = ins
        dirs = d.const(fu, dep, "array{" + DIR + "}", DIRS, name="Directions")
        empty_line = d.const(fu, dep, MOVES, "[]")
        d.label(fu, dep, "4방향: 가로, 세로, 대각선 2개")

        def lb(lu, ld, i, L, it):
            g, mv, ex, dirc = i
            win_l, line_l, best_l = L
            f = d.call(lu, ld, CD, [("Grid", g), ("Move", mv), ("Direction", dirc), ("error in", d.noerr(lu, ld))],
                       ["Count", "Open End", "error out"])
            dr, dc = d.unb(lu, ld, dirc, ["dR", "dC"])
            ndir = d.bnd(lu, ld, dirc, [("dR", d.neg(lu, ld, dr)), ("dC", d.neg(lu, ld, dc))])
            b = d.call(lu, ld, CD, [("Grid", g), ("Move", mv), ("Direction", ndir), ("error in", d.noerr(lu, ld))],
                       ["Count", "Open End", "error out"])
            length = d.add(lu, ld, d.add(lu, ld, f["Count"], b["Count"]), d.i32(lu, ld, 1))
            five = d.i32(lu, ld, 5)
            w = d.sel(lu, ld, ex, d.eq(lu, ld, length, five), d.ge(lu, ld, length, five))
            row, col = d.unb(lu, ld, mv, ["Row", "Col"])
            sr = d.sub(lu, ld, row, d.mul(lu, ld, b["Count"], dr))
            sc = d.sub(lu, ld, col, d.mul(lu, ld, b["Count"], dc))
            d.label(lu, ld, "길이 = 1 + 앞 + 뒤, 승리면 시작점부터 5칸 라인")

            def lb2(lu2, ld2, i2, L2, k):
                r = d.add(lu2, ld2, i2[0], d.mul(lu2, ld2, k, i2[2]))
                c = d.add(lu2, ld2, i2[1], d.mul(lu2, ld2, k, i2[3]))
                m = d.bnd(lu2, ld2, i2[4], [("Row", r), ("Col", c)])
                return [(m, "index")], [], None
            o5, _ = d.loop("For Loop", lu, ld, [(sr, None), (sc, None), (dr, None), (dc, None), (mv, None)], [],
                           lb2, maxin=five)
            newwin = d.and_(lu, ld, w, d.not_(lu, ld, win_l))
            line = d.sel(lu, ld, newwin, o5[0], line_l)
            return [], [d.or_(lu, ld, win_l, w), line, d.max_(lu, ld, best_l, length)], None
        _, fin = d.loop("For Loop", fu, dep, [(grid, None), (move, None), (exact, None), (dirs, "index")],
                        [d.b(fu, dep, False), empty_line, d.i32(fu, dep, 0)], lb)
        return fin

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required"),
              ("Last Move", MOVE, "[7,7,1]", 10, "required"),
              ("Exact Five", "bool", "false", 9, "recommended")],
          [("Win?", "bool", "false", 3), ("Win Line", MOVES, "[]", 2), ("Run Length", "int32", "0", 1)], body)
    return d.write(f"{OUT}/Rule_Check_Win.xml", "Rule_Check_Win.vi",
                   "마지막 착수 위치에서 4방향으로 연속 돌을 세어 5목 여부를 판정한다.\\0A"
                   "Exact Five=True(렌주룰 흑)이면 정확히 5개만 승리, False면 5개 이상 승리.\\0A"
                   "Win Line = 승리한 방향의 5칸 좌표, Run Length = 4방향 중 가장 긴 연속 수.")


# ---------------------------------------------------------------- Rule_Check_Forbidden
def check_forbidden():
    d = Doc()
    CD = "Rule_Count_Direction.vi"

    def body(fu, dep, ins):
        grid, move, renju = ins
        stone = d.unb(fu, dep, move, ["Stone"])[0]
        black = d.const(fu, dep, STONE, BLACK)
        active = d.and_(fu, dep, renju, d.eq(fu, dep, stone, black))
        d.label(fu, dep, "렌주룰 ON이고 흑일 때만 금수 판정")

        def off(fu2, dep2, j):
            return [d.b(fu2, dep2, False), d.const(fu2, dep2, FORB, "0")]

        def on(fu2, dep2, j):
            g, mv = j
            row, col = d.unb(fu2, dep2, mv, ["Row", "Col"])
            g2 = d.rep2(fu2, dep2, g, row, col, d.const(fu2, dep2, STONE, BLACK))
            dirs = d.const(fu2, dep2, "array{" + DIR + "}", DIRS, name="Directions")
            d.label(fu2, dep2, "흑을 가상 착수한 뒤 방향별 연속 수와 열린 끝 수 계산")

            def lb(lu, ld, i, L, it):
                gg, m, dirc = i
                five_l, over_l, four_l, three_l = L
                f = d.call(lu, ld, CD, [("Grid", gg), ("Move", m), ("Direction", dirc), ("error in", d.noerr(lu, ld))],
                           ["Count", "Open End", "error out"])
                dr, dc = d.unb(lu, ld, dirc, ["dR", "dC"])
                ndir = d.bnd(lu, ld, dirc, [("dR", d.neg(lu, ld, dr)), ("dC", d.neg(lu, ld, dc))])
                b = d.call(lu, ld, CD, [("Grid", gg), ("Move", m), ("Direction", ndir), ("error in", d.noerr(lu, ld))],
                           ["Count", "Open End", "error out"])
                one, zero = d.i32(lu, ld, 1), d.i32(lu, ld, 0)
                length = d.add(lu, ld, d.add(lu, ld, f["Count"], b["Count"]), one)
                opens = d.add(lu, ld, d.sel(lu, ld, f["Open End"], one, zero), d.sel(lu, ld, b["Open End"], one, zero))
                is5 = d.eq(lu, ld, length, d.i32(lu, ld, 5))
                is6 = d.ge(lu, ld, length, d.i32(lu, ld, 6))
                is4 = d.and_(lu, ld, d.eq(lu, ld, length, d.i32(lu, ld, 4)), d.ge(lu, ld, opens, one))
                is3 = d.and_(lu, ld, d.eq(lu, ld, length, d.i32(lu, ld, 3)), d.eq(lu, ld, opens, d.i32(lu, ld, 2)))
                d.label(lu, ld, "5=정확히 5, 장목>=6, 4=4+열린끝1이상, 열린3=3+양끝열림")
                return [], [d.or_(lu, ld, five_l, is5), d.or_(lu, ld, over_l, is6),
                            d.add(lu, ld, four_l, d.sel(lu, ld, is4, one, zero)),
                            d.add(lu, ld, three_l, d.sel(lu, ld, is3, one, zero))], None
            f0, z0 = d.b(fu2, dep2, False), d.i32(fu2, dep2, 0)
            _, fin = d.loop("For Loop", fu2, dep2, [(g2, None), (mv, None), (dirs, "index")],
                            [f0, d.b(fu2, dep2, False), z0, d.i32(fu2, dep2, 0)], lb)
            five, over, fours, threes = fin
            two = d.i32(fu2, dep2, 2)
            none_, d3, d4, ov = [d.const(fu2, dep2, FORB, v) for v in ("0", "1", "2", "3")]
            r1 = d.sel(fu2, dep2, d.ge(fu2, dep2, threes, two), d3, none_)
            r2 = d.sel(fu2, dep2, d.ge(fu2, dep2, fours, two), d4, r1)
            r3 = d.sel(fu2, dep2, over, ov, r2)
            reason = d.sel(fu2, dep2, five, d.const(fu2, dep2, FORB, "0"), r3)
            d.label(fu2, dep2, "우선순위: 정확히 5(허용) > 장목 > 4-4 > 3-3")
            forb = d.ne(fu2, dep2, reason, d.const(fu2, dep2, FORB, "0"))
            return [forb, reason]
        return d.case(fu, dep, active, [grid, move], 2,
                      [("True", "렌주룰 금수 판정", on), ("False", "판정 안 함", off)])

    subvi(d, [("Grid", GRID, EMPTY_GRID, 11, "required"),
              ("Move", MOVE, "[7,7,1]", 10, "required"),
              ("Renju", "bool", "true", 9, "recommended")],
          [("Forbidden?", "bool", "false", 3), ("Reason", FORB, "0", 2)], body)
    return d.write(f"{OUT}/Rule_Check_Forbidden.xml", "Rule_Check_Forbidden.vi",
                   "렌주룰 흑 금수 판정(3-3, 4-4, 장목). 흑을 가상 착수한 뒤 4방향 연속 수를 본다.\\0A"
                   "단순화: 연속된 돌만 판정(띈 3/띈 4 미포함), 거짓 금수 재귀 판정 없음. 정확히 5목이면 금수 아님.")


for f in (count_direction, check_win, check_forbidden):
    print(f.__name__, f())
