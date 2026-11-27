"""Canvas UI for the 128-channel monitor (PowerPoint-like flat design)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
import ui_common

OUT = sys.argv[1]
W2, H2 = 1600, 940
PPT, INKD, GRAY, LGRAY, PAGE, WHITE = 0xC43E1C, 0x262626, 0x605E5C, 0xD2D0CE, 0xF3F2F1, 0xFFFFFF
RED, PRED, DRED, BLUE, PBLUE, DBLUE, GREEN = 0xE81123, 0xFDE7E9, 0xA80000, 0x0078D4, 0xDEECF9, 0x004E8C, 0x107C10
PALETTE = [0x0078D4, 0xD83B01, 0x107C10, 0x5C2D91, 0xE81123, 0x008272, 0xB4009E, 0xFFB900, 0x00B7C3, 0x8764B8]
X0, Y0, TW, TH, GX, GY = 24, 120, 91, 54, 97, 60
GRAPH_CARD = (24, 612, 1576, 926)
PLOT = (96, 648, 1380, 896)


def spec(rect, fill, fill_sel, border, border_sel, text, tc, tcs, size, bold, group, value, radius):
    l, t, r, b = rect
    return (f"[[{l},{t},{r},{b}],{fill},{fill_sel},{border},{border_sel},{esc(text)},{tc},{tcs},{size},"
            f"{'true' if bold else 'false'},{group},{value},{radius}]")


def hbtn(x0, x1, text, g):
    return spec((x0, 12, x1, 52), WHITE, RED, WHITE, WHITE, text, PPT, WHITE, 15, True, g, 0, 8)


HEADER = [hbtn(800, 910, "설정", 0), hbtn(918, 1058, "▶ 측정 시작", 1), hbtn(1066, 1206, "■ 측정 정지", 2),
          hbtn(1214, 1364, "● 데이터 저장", 3), hbtn(1372, 1482, "그래프 창", 4), hbtn(1490, 1580, "종료", 5)]


def i16c(d, p, dep, v):
    return d.node(p, dep, "To Word Integer", [("number", v)], ["16bit integer"])["16bit integer"]


def rect16(d, p, dep, l, t, r, b):
    return d.bnd(p, dep, d.const(p, dep, RECT16, "[0,0,0,0]"),
                 [("left", i16c(d, p, dep, l)), ("top", i16c(d, p, dep, t)), ("right", i16c(d, p, dep, r)),
                  ("bottom", i16c(d, p, dep, b))])


def fixed(d, p, dep, v, prec):
    return d.node(p, dep, "Number To Fractional String", [("number", v), ("precision (6)", d.i32(p, dep, prec))],
                  ["F-format string"])["F-format string"]


def header_layout():
    d = Doc()

    def body(fu, dep, ins):
        d.label(fu, dep, "상단 버튼 배치표 (Group 0~5)")
        return [d.const(fu, dep, SPECS, "[" + ",".join(HEADER) + "]", name="Header Buttons")]
    subvi(d, [], [("Specs", SPECS, "[]", "r4")], body)
    return d.write(f"{OUT}/UI_Header_Layout.xml", "UI_Header_Layout.vi",
                   "상단 버튼: 0 설정, 1 측정 시작, 2 측정 정지, 3 데이터 저장(저장 중이면 빨강), 4 그래프 창, 5 종료.")


# ---------------------------------------------------------------- one tile
def draw_tile():
    d = Doc()

    def body(fu, dep, ins):
        pic, rect, ch, run, phase = ins
        nm, v, hi_l, lo_l, sv, gr, unit = d.unb(fu, dep, ch, ["Name", "Value", "High Limit", "Low Limit", "Save", "Graph", "Unit"])
        hi = d.and_(fu, dep, run, d.gt(fu, dep, v, hi_l))
        lo = d.and_(fu, dep, run, d.lt(fu, dep, v, lo_l))
        al = d.or_(fu, dep, hi, lo)
        on = d.and_(fu, dep, al, phase)
        d.label(fu, dep, "상한 초과=빨강, 하한 미만=파랑, Phase로 점멸")
        u = lambda c: u32(d, fu, dep, c)
        strong = d.sel(fu, dep, hi, u(RED), u(BLUE))
        pale = d.sel(fu, dep, hi, u(PRED), u(PBLUE))
        fill = d.sel(fu, dep, al, d.sel(fu, dep, phase, strong, pale), u(WHITE))
        border = d.sel(fu, dep, al, strong, u(LGRAY))
        vcol = d.sel(fu, dep, on, u(WHITE), d.sel(fu, dep, al, d.sel(fu, dep, hi, u(DRED), u(DBLUE)), u(INKD)))
        ncol = d.sel(fu, dep, on, u(WHITE), u(GRAY))
        p = rrect(d, fu, dep, pic, rect, fill, True, i16(d, fu, dep, 14))
        p = rrect(d, fu, dep, p, rect, border, False, i16(d, fu, dep, 14), d.const(fu, dep, "uint16", "1"))
        l, t, r, b = d.unb(fu, dep, rect, ["left", "top", "right", "bottom"])
        p = text_at(d, fu, dep, p, nm, i16c(d, fu, dep, d.add(fu, dep, l, i16(d, fu, dep, 8))),
                    i16c(d, fu, dep, d.add(fu, dep, t, i16(d, fu, dep, 12))), i16(d, fu, dep, 11), d.b(fu, dep, True), ncol, "[0,1]")
        badge = d.node(fu, dep, "Concatenate Strings",
                       [("string", d.sel(fu, dep, gr, d.const(fu, dep, "string", "G"), d.const(fu, dep, "string", ""))),
                        ("string", d.sel(fu, dep, sv, d.const(fu, dep, "string", " S"), d.const(fu, dep, "string", "")))],
                       ["concatenated string"])["concatenated string"]
        p = text_at(d, fu, dep, p, badge, i16c(d, fu, dep, d.sub(fu, dep, r, i16(d, fu, dep, 8))),
                    i16c(d, fu, dep, d.add(fu, dep, t, i16(d, fu, dep, 12))), i16(d, fu, dep, 10), d.b(fu, dep, True),
                    d.sel(fu, dep, on, u(WHITE), u(BLUE)), "[2,1]")
        vs = d.node(fu, dep, "Concatenate Strings", [("string", fixed(d, fu, dep, v, 2)), ("string", d.const(fu, dep, "string", " ")),
                                                     ("string", unit)], ["concatenated string"])["concatenated string"]
        vs = d.sel(fu, dep, run, vs, d.const(fu, dep, "string", "--"))
        cx = i16c(d, fu, dep, d.div(fu, dep, d.add(fu, dep, l, r), i16(d, fu, dep, 2)))
        p = text_at(d, fu, dep, p, vs, cx, i16c(d, fu, dep, d.add(fu, dep, t, i16(d, fu, dep, 36))), i16(d, fu, dep, 16),
                    d.b(fu, dep, True), vcol)
        return [p]

    subvi(d, [("Picture", "picture", "", "r0", "recommended"), ("Rect", RECT16, "[0,0,91,54]", "r5", "required"),
              ("Channel", CHANNEL, CH0, "r7", "required"), ("Running", "bool", "false", "r9", "recommended"),
              ("Phase", "bool", "false", "r1", "recommended")],
          [("New Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Draw_Tile.xml", "UI_Draw_Tile.vi",
                   "채널 타일 1개(디지털 인디케이터): 이름, G(그래프)/S(저장) 표시, 값+단위.\\0A"
                   "측정 중 값 > High Limit 이면 빨강, < Low Limit 이면 파랑으로 Phase에 맞춰 점멸.")


# ---------------------------------------------------------------- 128 tiles
def draw_tiles():
    d = Doc()

    def body(fu, dep, ins):
        pic, chs, run, phase = ins
        d.label(fu, dep, "16열(섀시-모듈) x 8행(ai0~7) 바둑판")

        def hdr(lu, ld, i, L, it):
            q, r = qr(d, lu, ld, it, d.i32(lu, ld, 8))
            s = d.node(lu, ld, "Concatenate Strings",
                       [("string", d.const(lu, ld, "string", "C")),
                        ("string", d.node(lu, ld, "Number To Decimal String", [("number", d.add(lu, ld, q, d.i32(lu, ld, 1)))],
                                          ["decimal integer string"])["decimal integer string"]),
                        ("string", d.const(lu, ld, "string", esc(" · M"))),
                        ("string", d.node(lu, ld, "Number To Decimal String", [("number", d.add(lu, ld, r, d.i32(lu, ld, 1)))],
                                          ["decimal integer string"])["decimal integer string"])],
                       ["concatenated string"])["concatenated string"]
            x = d.add(lu, ld, d.i32(lu, ld, X0 + TW // 2), d.mul(lu, ld, it, d.i32(lu, ld, GX)))
            p = text_at(d, lu, ld, L[0], s, i16c(d, lu, ld, x), i16(d, lu, ld, Y0 - 10), i16(d, lu, ld, 11),
                        d.b(lu, ld, True), u32(d, lu, ld, GRAY))
            return [], [p], None
        _, h = d.loop("For Loop", fu, dep, [], [pic], hdr, maxin=d.i32(fu, dep, 16))

        def lb(lu, ld, i, L, it):
            r_, ph_, ch = i
            col, row = qr(d, lu, ld, it, d.i32(lu, ld, 8))
            l = d.add(lu, ld, d.i32(lu, ld, X0), d.mul(lu, ld, col, d.i32(lu, ld, GX)))
            t = d.add(lu, ld, d.i32(lu, ld, Y0), d.mul(lu, ld, row, d.i32(lu, ld, GY)))
            rc = rect16(d, lu, ld, l, t, d.add(lu, ld, l, d.i32(lu, ld, TW)), d.add(lu, ld, t, d.i32(lu, ld, TH)))
            o = d.call(lu, ld, "UI_Draw_Tile.vi", [("Picture", L[0]), ("Rect", rc), ("Channel", ch), ("Running", r_),
                                                   ("Phase", ph_), ("error in", d.noerr(lu, ld))], ["New Picture", "error out"])
            return [], [o["New Picture"]], None
        _, f = d.loop("For Loop", fu, dep, [(run, None), (phase, None), (chs, "index")], [h[0]], lb)
        return [f[0]]

    subvi(d, [("Picture", "picture", "", "r0", "recommended"), ("Channels", CHANNELS, "[]", "r5", "required"),
              ("Running", "bool", "false", "r7", "recommended"), ("Phase", "bool", "false", "r9", "recommended")],
          [("New Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Draw_Tiles.xml", "UI_Draw_Tiles.vi",
                   "128채널 타일 바둑판. 채널 i -> 열 i/8 (C섀시·M모듈), 행 i%8 (ai0~7).")


def tile_hit():
    d = Doc()

    def body(fu, dep, ins):
        x, y = ins
        dx = d.sub(fu, dep, x, d.i32(fu, dep, X0))
        dy = d.sub(fu, dep, y, d.i32(fu, dep, Y0))
        col, rx = qr(d, fu, dep, dx, d.i32(fu, dep, GX))
        row, ry = qr(d, fu, dep, dy, d.i32(fu, dep, GY))
        ok = d.and_(fu, dep, d.and_(fu, dep, d.inrange(fu, dep, col, d.i32(fu, dep, 0), d.i32(fu, dep, 15)),
                                    d.inrange(fu, dep, row, d.i32(fu, dep, 0), d.i32(fu, dep, 7))),
                    d.and_(fu, dep, d.lt(fu, dep, rx, d.i32(fu, dep, TW)), d.lt(fu, dep, ry, d.i32(fu, dep, TH))))
        d.label(fu, dep, "타일 안이면 채널 번호, 아니면 -1")
        idx = d.add(fu, dep, d.mul(fu, dep, col, d.i32(fu, dep, 8)), row)
        return [d.sel(fu, dep, ok, idx, d.i32(fu, dep, -1))]

    subvi(d, [("X", "int32", "0", "r0", "required"), ("Y", "int32", "0", "r5", "required")],
          [("Channel Index", "int32", "-1", "r4")], body)
    return d.write(f"{OUT}/UI_Tile_Hit.xml", "UI_Tile_Hit.vi", "클릭 좌표 -> 채널 번호(0~127), 타일 밖이면 -1.")


# ---------------------------------------------------------------- graph
def graph_series():
    d = Doc()

    def body(fu, dep, ins):
        pic, row, color, rect, ymin, ymax = ins
        l, t, r, b = d.unb(fu, dep, rect, ["left", "top", "right", "bottom"])
        n = d.size(fu, dep, row)
        m = d.node(fu, dep, "Max & Min", [("x", n), ("y", d.i32(fu, dep, 600))], ["max(x\\2Cy)", "min(x\\2Cy)"])["min(x\\2Cy)"]
        d.label(fu, dep, "최대 600점으로 줄여 선 그리기")
        wpx = d.sub(fu, dep, r, l)
        hpx = d.sub(fu, dep, b, t)
        span = d.sub(fu, dep, ymax, ymin)

        def lb(lu, ld, i, L, it):
            rw, nn, mm, ll, bb, ww, hh, y0, sp = i
            k = d.node(lu, ld, "To Long Integer", [("number", d.div(lu, ld, d.mul(lu, ld, it, nn), mm))], ["32bit integer"])["32bit integer"]
            v = d.idx1(lu, ld, rw, k)
            den = d.max_(lu, ld, d.sub(lu, ld, mm, d.i32(lu, ld, 1)), d.i32(lu, ld, 1))
            x = d.add(lu, ld, ll, d.div(lu, ld, d.mul(lu, ld, it, ww), den))
            y = d.sub(lu, ld, bb, d.mul(lu, ld, d.div(lu, ld, d.sub(lu, ld, v, y0), sp), hh))
            pt = d.bnd(lu, ld, d.const(lu, ld, POINT16, "[0,0]"), [("x", i16c(d, lu, ld, x)), ("y", i16c(d, lu, ld, y))])
            return [(pt, "index")], [], None
        pts, _ = d.loop("For Loop", fu, dep, [(row, None), (n, None), (m, None), (l, None), (b, None), (wpx, None), (hpx, None),
                                              (ymin, None), (span, None)], [], lb, maxin=m)
        o = d.call(fu, dep, "Draw Multiple Lines.vi", [("picture", pic), ("line endpoints", pts[0]), ("color(black)", color),
                                                       ("pen", d.const(fu, dep, PEN, "[2,0]"))], ["new picture"])
        return [o["new picture"]]

    subvi(d, [("Picture", "picture", "", "r0", "recommended"), ("Samples", "array{double}", "[]", "r5", "required"),
              ("Color", "uint32", "0", "r7", "recommended"), ("Plot Rect", RECT16, "[0,0,100,100]", "r9", "required"),
              ("Y Min", "double", "0", "r1", "recommended"), ("Y Max", "double", "1", "r2", "recommended")],
          [("New Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Graph_Series.xml", "UI_Graph_Series.vi", "채널 1개 파형을 Plot Rect 안에 꺾은선으로 그린다(Y Min~Y Max).")


def draw_graph():
    d = Doc()

    def body(fu, dep, ins):
        pic, rect, data, chs, dt = ins
        l, t, r, b = d.unb(fu, dep, rect, ["left", "top", "right", "bottom"])
        d.label(fu, dep, "Graph가 켜진 채널만 골라 Y 자동 스케일")

        def sel_lb(lu, ld, i, L, it):
            row, ch = i
            nm, g = d.unb(lu, ld, ch, ["Name", "Graph"])
            return [(row, "index", g), (nm, "index", g)], [], None
        so, _ = d.loop("For Loop", fu, dep, [(data, "index"), (chs, "index")], [], sel_lb)
        rows, names = so
        mm = d.node(fu, dep, "Array Max & Min", [("array", rows)], ["max value", "max index (indices)", "min value", "min index (indices)"])
        lo, hi = mm["min value"], mm["max value"]
        flat = d.lt(fu, dep, d.sub(fu, dep, hi, lo), d.dbl(fu, dep, 1e-9))
        hi = d.sel(fu, dep, flat, d.add(fu, dep, hi, d.dbl(fu, dep, 1)), hi)
        lo = d.sel(fu, dep, flat, d.sub(fu, dep, lo, d.dbl(fu, dep, 1)), lo)
        pad = d.mul(fu, dep, d.sub(fu, dep, hi, lo), d.dbl(fu, dep, 0.05))
        ymax = d.add(fu, dep, hi, pad)
        ymin = d.sub(fu, dep, lo, pad)
        p = d.call(fu, dep, "Draw Rectangle.vi", [("picture", pic), ("rect", rect), ("color(black)", u32(d, fu, dep, LGRAY))],
                   ["new picture"])["new picture"]

        def grid(lu, ld, i, L, it):
            ll, tt, rr, bb, y0, y1 = i
            y = d.add(lu, ld, tt, d.div(lu, ld, d.mul(lu, ld, d.sub(lu, ld, bb, tt), it), d.i32(lu, ld, 4)))
            yi = i16c(d, lu, ld, y)
            pts = d.node(lu, ld, "Build Array",
                         [("element", d.bnd(lu, ld, d.const(lu, ld, POINT16, "[0,0]"), [("x", ll), ("y", yi)])),
                          ("element", d.bnd(lu, ld, d.const(lu, ld, POINT16, "[0,0]"), [("x", rr), ("y", yi)]))],
                         ["appended array"])["appended array"]
            p1 = d.call(lu, ld, "Draw Multiple Lines.vi", [("picture", L[0]), ("line endpoints", pts),
                                                           ("color(black)", u32(d, lu, ld, 0xEDEBE9))], ["new picture"])["new picture"]
            v = d.sub(lu, ld, y1, d.mul(lu, ld, d.sub(lu, ld, y1, y0), d.div(lu, ld, it, d.dbl(lu, ld, 4))))
            p2 = text_at(d, lu, ld, p1, fixed(d, lu, ld, v, 2), i16c(d, lu, ld, d.sub(lu, ld, ll, i16(d, lu, ld, 8))), yi,
                         i16(d, lu, ld, 11), d.b(lu, ld, False), u32(d, lu, ld, GRAY), "[2,1]")
            return [], [p2], None
        _, g = d.loop("For Loop", fu, dep, [(l, None), (t, None), (r, None), (b, None), (ymin, None), (ymax, None)], [p], grid,
                      maxin=d.i32(fu, dep, 5))
        d.label(fu, dep, "가로 눈금 5개 + Y 값")
        pal = d.const(fu, dep, "array{uint32}", "[" + ",".join(str(c) for c in PALETTE) + "]", name="Palette")

        def series(lu, ld, i, L, it):
            rc, y0, y1, pl, rr, tt, row, nm = i
            _, k = qr(d, lu, ld, it, d.i32(lu, ld, len(PALETTE)))
            col = d.idx1(lu, ld, pl, k)
            o = d.call(lu, ld, "UI_Graph_Series.vi", [("Picture", L[0]), ("Samples", row), ("Color", col), ("Plot Rect", rc),
                                                      ("Y Min", y0), ("Y Max", y1), ("error in", d.noerr(lu, ld))],
                       ["New Picture", "error out"])
            ly = d.add(lu, ld, tt, d.add(lu, ld, d.mul(lu, ld, it, d.i32(lu, ld, 18)), d.i32(lu, ld, 8)))
            p2 = text_at(d, lu, ld, o["New Picture"], d.node(lu, ld, "Concatenate Strings",
                                                             [("string", d.const(lu, ld, "string", esc("■ "))), ("string", nm)],
                                                             ["concatenated string"])["concatenated string"],
                         i16c(d, lu, ld, d.add(lu, ld, rr, i16(d, lu, ld, 20))), i16c(d, lu, ld, ly), i16(d, lu, ld, 12),
                         d.b(lu, ld, True), col, "[0,1]")
            return [], [p2], None
        _, s = d.loop("For Loop", fu, dep, [(rect, None), (ymin, None), (ymax, None), (pal, None), (r, None), (t, None),
                                            (rows, "index"), (names, "index")], [g[0]], series)
        n = d.idx1(fu, dep, d.size(fu, dep, data), d.i32(fu, dep, 1))
        tsec = d.mul(fu, dep, n, dt)
        tl = d.node(fu, dep, "Concatenate Strings", [("string", fixed(d, fu, dep, tsec, 3)), ("string", d.const(fu, dep, "string", " s"))],
                    ["concatenated string"])["concatenated string"]
        p = text_at(d, fu, dep, s[0], d.const(fu, dep, "string", "0 s"), l, i16c(d, fu, dep, d.add(fu, dep, b, i16(d, fu, dep, 14))),
                    i16(d, fu, dep, 11), d.b(fu, dep, False), u32(d, fu, dep, GRAY), "[0,1]")
        p = text_at(d, fu, dep, p, tl, r, i16c(d, fu, dep, d.add(fu, dep, b, i16(d, fu, dep, 14))),
                    i16(d, fu, dep, 11), d.b(fu, dep, False), u32(d, fu, dep, GRAY), "[2,1]")
        return [p]

    subvi(d, [("Picture", "picture", "", "r0", "recommended"), ("Plot Rect", RECT16, "[96,648,1380,896]", "r5", "required"),
              ("Data", "array.2{double}", "[]", "r7", "required"), ("Channels", CHANNELS, "[]", "r9", "required"),
              ("dt", "double", "0.001", "r1", "recommended")],
          [("New Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Draw_Graph.xml", "UI_Draw_Graph.vi",
                   "Channels[i].Graph = True 인 채널만 Plot Rect에 꺾은선 그래프로 그림(Y 자동 스케일, 눈금, 범례, 시간축).")


# ---------------------------------------------------------------- whole screen
def render_main():
    d = Doc()

    def body(fu, dep, ins):
        chs, data, dt, run, logging, hover, phase, status = ins
        u = lambda c: u32(d, fu, dep, c)
        p = d.call(fu, dep, "Draw Rectangle.vi", [("rect", rect_c(d, fu, dep, 0, 0, W2, H2)), ("fill?(F)", d.b(fu, dep, True)),
                                                  ("color(black)", u(PAGE))], ["new picture"])["new picture"]
        p = d.call(fu, dep, "Draw Rectangle.vi", [("picture", p), ("rect", rect_c(d, fu, dep, 0, 0, W2, 64)),
                                                  ("fill?(F)", d.b(fu, dep, True)), ("color(black)", u(PPT))], ["new picture"])["new picture"]
        d.label(fu, dep, "제목 띠(PowerPoint 주황) + 상태 + 버튼")
        p = text_at(d, fu, dep, p, d.const(fu, dep, "string", esc("128CH 아날로그 입력 모니터")), i16(d, fu, dep, 24),
                    i16(d, fu, dep, 32), i16(d, fu, dep, 20), d.b(fu, dep, True), u(WHITE), "[0,1]")
        p = text_at(d, fu, dep, p, status, i16(d, fu, dep, 360), i16(d, fu, dep, 32), i16(d, fu, dep, 13), d.b(fu, dep, False),
                    u(0xFCE4D6), "[0,1]")
        m1 = d.i32(fu, dep, -1)
        vals = d.node(fu, dep, "Build Array", [("element", m1), ("element", m1), ("element", m1),
                                               ("element", d.sel(fu, dep, logging, d.i32(fu, dep, 0), m1))],
                      ["appended array"])["appended array"]
        nr = d.not_(fu, dep, run)
        dims = d.node(fu, dep, "Build Array", [("element", run), ("element", run), ("element", nr), ("element", nr)],
                      ["appended array"])["appended array"]
        specs = d.call(fu, dep, "UI_Header_Layout.vi", [("error in", d.noerr(fu, dep))], ["Specs", "error out"])["Specs"]
        p = d.call(fu, dep, "UI_Draw_Buttons.vi", [("Picture", p), ("Specs", specs), ("Values", vals), ("Dim Groups", dims),
                                                   ("Hover", hover), ("error in", d.noerr(fu, dep))], ["New Picture", "error out"])["New Picture"]
        p = text_at(d, fu, dep, p, d.const(fu, dep, "string", esc("채널 모니터   ·   타일을 클릭하면 상한/하한 · 스케일 · 저장 · 그래프 설정")),
                    i16(d, fu, dep, 24), i16(d, fu, dep, 86), i16(d, fu, dep, 13), d.b(fu, dep, True), u(INKD), "[0,1]")
        for x, txt, c in ((1130, "■ 상한 초과", RED), (1240, "■ 하한 미만", BLUE), (1350, "G 그래프", BLUE), (1450, "S 저장", BLUE)):
            p = text_at(d, fu, dep, p, d.const(fu, dep, "string", esc(txt)), i16(d, fu, dep, x), i16(d, fu, dep, 86),
                        i16(d, fu, dep, 12), d.b(fu, dep, True), u(c), "[0,1]")
        p = d.call(fu, dep, "UI_Draw_Tiles.vi", [("Picture", p), ("Channels", chs), ("Running", run), ("Phase", phase),
                                                 ("error in", d.noerr(fu, dep))], ["New Picture", "error out"])["New Picture"]
        d.label(fu, dep, "아래: 그래프 카드")
        gl, gt, gr, gb = GRAPH_CARD
        card = rect_c(d, fu, dep, gl, gt, gr, gb)
        p = rrect(d, fu, dep, p, card, u(WHITE), True, i16(d, fu, dep, 16))
        p = rrect(d, fu, dep, p, card, u(LGRAY), False, i16(d, fu, dep, 16), d.const(fu, dep, "uint16", "1"))
        p = text_at(d, fu, dep, p, d.const(fu, dep, "string", esc("그래프 - 선택 채널 (G)")), i16(d, fu, dep, gl + 16),
                    i16(d, fu, dep, gt + 16), i16(d, fu, dep, 14), d.b(fu, dep, True), u(INKD), "[0,1]")
        p = d.call(fu, dep, "UI_Draw_Graph.vi", [("Picture", p), ("Plot Rect", rect_c(d, fu, dep, *PLOT)), ("Data", data),
                                                 ("Channels", chs), ("dt", dt), ("error in", d.noerr(fu, dep))],
                   ["New Picture", "error out"])["New Picture"]
        return [p]

    subvi(d, [("Channels", CHANNELS, "[]", "r0", "required"), ("Data", "array.2{double}", "[]", "r5", "recommended"),
              ("dt", "double", "0.001", "r7", "recommended"), ("Running", "bool", "false", "r9", "recommended"),
              ("Logging", "bool", "false", "r1", "recommended"), ("Hover Button", "int32", "-1", "r2", "recommended"),
              ("Phase", "bool", "false", "r3", "recommended"), ("Status", "string", "", "r12", "recommended")],
          [("Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Render_Main.xml", "UI_Render_Main.vi",
                   "메인 화면 1600x940 전체 그리기: 주황 제목 띠 + 버튼 6개, 128채널 타일 바둑판, 하단 그래프 카드.")


if __name__ == "__main__":
    print(ui_common.draw_buttons(), ui_common.hit_test())
    for fn in (header_layout, draw_tile, draw_tiles, tile_hit, graph_series, draw_graph, render_main):
        print(fn.__name__, fn())
