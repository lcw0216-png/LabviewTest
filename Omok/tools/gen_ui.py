import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
GEO = "UI_Board_Geometry.vi"
WOOD, BLACKC, WHITEC, EDGE, RED, GRAY = 14463836, 0, 16777215, 4210752, 16724016, 8421504


def geometry():
    d = Doc()

    def body(fu, dep, ins):
        d.label(fu, dep, "바둑판 기하: 원점 30 px, 칸 38 px, 전체 592 px")
        return [d.i32(fu, dep, 30), d.i32(fu, dep, 38), d.i32(fu, dep, 592)]
    subvi(d, [], [("Origin", "int32", "30", 3), ("Cell", "int32", "38", 2), ("Size", "int32", "592", 1)], body)
    return d.write(f"{OUT}/UI_Board_Geometry.xml", "UI_Board_Geometry.vi",
                   "바둑판 그리기와 좌표 변환이 같이 쓰는 상수. X = Origin + Col*Cell, Y = Origin + Row*Cell.")


def geo(d, p, dep):
    g = d.call(p, dep, GEO, [("error in", d.noerr(p, dep))], ["Origin", "Cell", "Size", "error out"])
    return g["Origin"], g["Cell"], g["Size"]


def pixel_to_grid():
    d = Doc()

    def body(fu, dep, ins):
        coords = ins[0]
        x, y = d.unb(fu, dep, coords, ["X", "Y"])
        o, c, _ = geo(d, fu, dep)

        def axis(v):
            f = d.div(fu, dep, d.sub(fu, dep, v, o), c)
            n = d.node(fu, dep, "Round To Nearest", [("number", f)], ["nearest integer value"])["nearest integer value"]
            k = d.node(fu, dep, "To Long Integer", [("number", n)], ["32bit integer"])["32bit integer"]
            center = d.add(fu, dep, o, d.mul(fu, dep, k, c))
            dist = d.node(fu, dep, "Absolute Value", [("x", d.sub(fu, dep, v, center))], ["abs(x)"])["abs(x)"]
            near = d.le(fu, dep, dist, d.mul(fu, dep, c, d.dbl(fu, dep, 0.45)))
            inr = d.inrange(fu, dep, k, d.i32(fu, dep, 0), d.i32(fu, dep, 14))
            return k, d.and_(fu, dep, near, inr)
        col, vc = axis(x)
        row, vr = axis(y)
        d.label(fu, dep, "가장 가까운 교차점, 0.45칸 이내만 유효")
        valid = d.and_(fu, dep, vc, vr)
        m1 = d.i32(fu, dep, -1)
        return [d.sel(fu, dep, valid, row, m1), d.sel(fu, dep, valid, col, m1), valid]
    subvi(d, [("Coords", "cluster{int32.X,int32.Y}", "[0,0]", 11, "required")],
          [("Row", "int32", "-1", 3), ("Col", "int32", "-1", 2), ("Valid", "bool", "false", 1)], body)
    return d.write(f"{OUT}/UI_Pixel_To_Grid.xml", "UI_Pixel_To_Grid.vi",
                   "Picture의 마우스 좌표(X,Y)를 바둑판 칸(Row,Col)으로 바꾼다. 교차점에서 0.45칸 이내이고 0~14 범위일 때만 Valid.")


def draw_board():
    d = Doc()

    def body(fu, dep, ins):
        bs, hover, winline = ins
        grid, hist, last = d.unb(fu, dep, bs, ["Grid", "Move History", "Last Move"])
        o, c, size = geo(d, fu, dep)
        rect = d.bnd(fu, dep, d.const(fu, dep, RECT16, "[0,0,0,0]"), [("right", size), ("bottom", size)])
        pic = d.call(fu, dep, "Draw Rectangle.vi", [("rect", rect), ("fill?(F)", d.b(fu, dep, True)),
                                                     ("color(black)", d.const(fu, dep, "uint32", str(WOOD)))],
                     ["new picture"])["new picture"]
        d.label(fu, dep, "1) 나무 배경  2) 격자선 15x15")
        far = d.add(fu, dep, o, d.mul(fu, dep, c, d.i32(fu, dep, 14)))

        def pt(p, dp, x, y):
            return d.bnd(p, dp, d.const(p, dp, POINT16, "[0,0]"), [("x", x), ("y", y)])

        def ctr(p, dp, x, y):
            return d.bnd(p, dp, d.const(p, dp, CENTER16, "[0,0]"), [("horizontal", x), ("vertical", y)])

        def xy(p, dp, oo, cc, r, cl):
            return d.add(p, dp, oo, d.mul(p, dp, cl, cc)), d.add(p, dp, oo, d.mul(p, dp, r, cc))

        def lines(lu, ld, i, L, it):
            oo, cc, ff = i
            pp = d.add(lu, ld, oo, d.mul(lu, ld, it, cc))
            p1 = d.call(lu, ld, "Move Pen.vi", [("picture", L[0]), ("new position", pt(lu, ld, oo, pp))], ["new picture"])
            p2 = d.call(lu, ld, "Draw Line.vi", [("picture", p1["new picture"]), ("end point", pt(lu, ld, ff, pp))],
                        ["new picture"])
            p3 = d.call(lu, ld, "Move Pen.vi", [("picture", p2["new picture"]), ("new position", pt(lu, ld, pp, oo))],
                        ["new picture"])
            p4 = d.call(lu, ld, "Draw Line.vi", [("picture", p3["new picture"]), ("end point", pt(lu, ld, pp, ff))],
                        ["new picture"])
            return [], [p4["new picture"]], None
        _, fin = d.loop("For Loop", fu, dep, [(o, None), (c, None), (far, None)], [pic], lines,
                        maxin=d.i32(fu, dep, 15))
        pic = fin[0]

        stars = d.const(fu, dep, "array{cluster{int32.r,int32.c}}",
                        "[[3,3],[3,7],[3,11],[7,3],[7,7],[7,11],[11,3],[11,7],[11,11]]", name="Star Points")
        d.label(fu, dep, "3) 화점 9개  4) 돌(히스토리 순회)")

        def starf(lu, ld, i, L, it):
            oo, cc, s = i
            r, cl = d.unb(lu, ld, s, ["r", "c"])
            x, y = xy(lu, ld, oo, cc, r, cl)
            p = d.call(lu, ld, "Draw Circle by Radius.vi",
                       [("picture", L[0]), ("pixel center", ctr(lu, ld, x, y)), ("radius", d.const(lu, ld, "int16", "4")),
                        ("fill?(F)", d.b(lu, ld, True))], ["new picture"])
            return [], [p["new picture"]], None
        _, fin = d.loop("For Loop", fu, dep, [(o, None), (c, None), (stars, "index")], [pic], starf)
        pic = fin[0]

        def stonef(lu, ld, i, L, it):
            oo, cc, m = i
            r, cl, st = d.unb(lu, ld, m, ["Row", "Col", "Stone"])
            x, y = xy(lu, ld, oo, cc, r, cl)
            center = ctr(lu, ld, x, y)
            isb = d.eq(lu, ld, st, d.const(lu, ld, STONE, BLACK))
            col_ = d.sel(lu, ld, isb, d.const(lu, ld, "uint32", str(BLACKC)), d.const(lu, ld, "uint32", str(WHITEC)))
            rad = d.const(lu, ld, "int16", "17")
            p1 = d.call(lu, ld, "Draw Circle by Radius.vi",
                        [("picture", L[0]), ("pixel center", center), ("radius", rad), ("fill?(F)", d.b(lu, ld, True)),
                         ("color(black)", col_)], ["new picture"])
            p2 = d.call(lu, ld, "Draw Circle by Radius.vi",
                        [("picture", p1["new picture"]), ("pixel center", center), ("radius", rad),
                         ("fill?(F)", d.b(lu, ld, False)), ("color(black)", d.const(lu, ld, "uint32", str(EDGE)))],
                        ["new picture"])
            return [], [p2["new picture"]], None
        _, fin = d.loop("For Loop", fu, dep, [(o, None), (c, None), (hist, "index")], [pic], stonef)
        pic = fin[0]

        # 5) last move marker
        lr, lc, ls = d.unb(fu, dep, last, ["Row", "Col", "Stone"])
        has_last = d.and_(fu, dep, d.ge(fu, dep, lr, d.i32(fu, dep, 0)),
                          d.ne(fu, dep, ls, d.const(fu, dep, STONE, EMPTY)))

        def mark(f2, d2, j):
            x, y = xy(f2, d2, j[1], j[2], j[3], j[4])
            p = d.call(f2, d2, "Draw Circle by Radius.vi",
                       [("picture", j[0]), ("pixel center", ctr(f2, d2, x, y)), ("radius", d.const(f2, d2, "int16", "5")),
                        ("fill?(F)", d.b(f2, d2, True)), ("color(black)", d.const(f2, d2, "uint32", str(RED)))],
                       ["new picture"])
            return [p["new picture"]]
        pic = d.case(fu, dep, has_last, [pic, o, c, lr, lc], 1,
                     [("True", "마지막 착수 빨간 점", mark), ("False", None, lambda f2, d2, j: [j[0]])])[0]

        # 6) hover preview (only on an empty cell)
        hr, hc = d.unb(fu, dep, hover, ["Row", "Col"])
        cell = d.idx2(fu, dep, grid, hr, hc)
        has_hover = d.and_(fu, dep, d.ge(fu, dep, hr, d.i32(fu, dep, 0)),
                           d.eq(fu, dep, cell, d.const(fu, dep, STONE, EMPTY)))

        def hov(f2, d2, j):
            x, y = xy(f2, d2, j[1], j[2], j[3], j[4])
            p = d.call(f2, d2, "Draw Circle by Radius.vi",
                       [("picture", j[0]), ("pixel center", ctr(f2, d2, x, y)), ("radius", d.const(f2, d2, "int16", "17")),
                        ("fill?(F)", d.b(f2, d2, False)), ("color(black)", d.const(f2, d2, "uint32", str(GRAY)))],
                       ["new picture"])
            return [p["new picture"]]
        pic = d.case(fu, dep, has_hover, [pic, o, c, hr, hc], 1,
                     [("True", "호버 미리보기(회색 테두리)", hov), ("False", None, lambda f2, d2, j: [j[0]])])[0]

        # 7) win line
        n = d.size(fu, dep, winline)
        has_win = d.ge(fu, dep, n, d.i32(fu, dep, 2))

        def wl(f2, d2, j):
            p0, oo, cc, line, nn = j
            a = d.idx1(f2, d2, line, d.i32(f2, d2, 0))
            z = d.idx1(f2, d2, line, d.sub(f2, d2, nn, d.i32(f2, d2, 1)))
            ar, ac = d.unb(f2, d2, a, ["Row", "Col"])
            zr, zc = d.unb(f2, d2, z, ["Row", "Col"])
            ax, ay = xy(f2, d2, oo, cc, ar, ac)
            zx, zy = xy(f2, d2, oo, cc, zr, zc)
            p1 = d.call(f2, d2, "Move Pen.vi", [("picture", p0), ("new position", pt(f2, d2, ax, ay))], ["new picture"])
            p2 = d.call(f2, d2, "Draw Line.vi", [("picture", p1["new picture"]), ("end point", pt(f2, d2, zx, zy)),
                                                 ("color(black)", d.const(f2, d2, "uint32", str(RED))),
                                                 ("pen", d.const(f2, d2, PEN, "[5,0]"))], ["new picture"])
            return [p2["new picture"]]
        pic = d.case(fu, dep, has_win, [pic, o, c, winline, n], 1,
                     [("True", "승리 5목 라인", wl), ("False", None, lambda f2, d2, j: [j[0]])])[0]
        return [pic]

    subvi(d, [("Board State", BOARD_STATE, "[" + EMPTY_GRID + ",[],[-1,-1,0]]", 11, "required"),
              ("Hover", MOVE, "[-1,-1,0]", 10, "recommended"),
              ("Win Line", MOVES, "[]", 9, "recommended")],
          [("Picture", "picture", "", 3)], body)
    return d.write(f"{OUT}/UI_Draw_Board.xml", "UI_Draw_Board.vi",
                   "Board State를 2D Picture로 그린다: 나무 배경, 격자선 15x15, 화점 9개, 흑/백 돌(히스토리 순회), "
                   "마지막 착수 빨간 점, 호버 미리보기(회색 테두리), 승리 5목 라인(빨간 굵은 선).")


for f in (geometry, pixel_to_grid, draw_board):
    print(f.__name__, f())
