"""v2 canvas UI: buttons, hit test, layouts, full-screen render."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
WHITE_C, CHIP_SEL, CHIP_BORDER, BLUE = 0xFFFFFF, 0xEAF4FC, 0xDADFE3, 0x3498DB
GRAY_T, SUB_T = 0x95A5A6, 0x7F8C8D
DIM_FILL, DIM_BORDER, DIM_TEXT, HOVER_B = 0xF2F3F4, 0xE5E7E9, 0xB3B6B7, 0x2C3E50


def spec(rect, fill, fill_sel, border, border_sel, text, tc, tcs, size, bold, group, value, radius):
    l, t, r, b = rect
    return (f"[[{l},{t},{r},{b}],{fill},{fill_sel},{border},{border_sel},{esc(text)},{tc},{tcs},{size},"
            f"{'true' if bold else 'false'},{group},{value},{radius}]")


def label(rect, text, size, color, bold=False):
    return spec(rect, TRANSP, TRANSP, TRANSP, TRANSP, text, color, color, size, bold, -1, -1, 0)


def chip(rect, text, group, value):
    return spec(rect, WHITE_C, CHIP_SEL, CHIP_BORDER, BLUE, text, INK, INK, 16, True, group, value, 14)


def diff_btn(rect, text, value, full, pastel):
    return spec(rect, pastel, full, pastel, INK, text, full, WHITE_C, 16, True, 2, value, 14)


def solid(rect, text, color, group, value, size=18):
    return spec(rect, color, color, color, color, text, WHITE_C, WHITE_C, size, True, group, value, 14)


SETTINGS_SPECS = [
    label((36, 84, 556, 128), "오목을 할 준비가 되셨나요?", 26, INK, True),
    label((36, 132, 556, 162), "돌 다섯 개를 먼저 일렬로 놓으면 승리!", 15, SUB_T),
    label((36, 180, 556, 204), "게임 모드", 14, GRAY_T),
    chip((76, 210, 292, 262), "사람 vs AI", 0, 0),
    chip((300, 210, 516, 262), "2인 플레이", 0, 1),
    label((36, 280, 556, 304), "선공 · 후공 선택", 14, GRAY_T),
    chip((76, 310, 292, 362), "● 흑 · 선공", 1, 0),
    chip((300, 310, 516, 362), "○ 백 · 후공", 1, 1),
    label((36, 380, 556, 404), "난이도 선택", 14, GRAY_T),
    diff_btn((76, 410, 180, 462), "쉬움", 0, 0x27AE60, 0xD5F5E3),
    diff_btn((188, 410, 292, 462), "보통", 1, 0x3498DB, 0xD6EAF8),
    diff_btn((300, 410, 404, 462), "어려움", 2, 0xE67E22, 0xFAE5D3),
    diff_btn((412, 410, 516, 462), "마스터", 3, 0xE74C3C, 0xFADBD8),
    label((36, 480, 556, 504), "규칙", 14, GRAY_T),
    chip((76, 510, 292, 562), "렌주룰 (흑 금수)", 3, 1),
    chip((300, 510, 516, 562), "자유룰 (제한 없음)", 3, 0),
    solid((76, 600, 516, 670), "게임 시작", INK, 4, -1, 22),
]
GAME_SPECS = [
    solid((12, 690, 196, 750), "무르기", 0x5D6D7E, 5, 0),
    solid((204, 690, 388, 750), "새 게임", 0x27AE60, 5, 1),
    solid((396, 690, 580, 750), "설정", 0xE67E22, 5, 2),
]


def layout(name, specs, desc):
    d = Doc()

    def body(fu, dep, ins):
        d.label(fu, dep, "버튼/글자 배치표 (Rect, 색, 글자, Group, Value)")
        return [d.const(fu, dep, SPECS, "[" + ",".join(specs) + "]", name="Layout")]
    subvi(d, [], [("Specs", SPECS, "[]", "r4")], body)
    return d.write(f"{OUT}/{name}.xml", f"{name}.vi", desc)


# ---------------------------------------------------------------- UI_Draw_Buttons
def draw_buttons():
    d = Doc()

    def body(fu, dep, ins):
        pic, specs, values, dims, hover = ins
        d.label(fu, dep, "선택=Fill Sel, 호버=진한 테두리, 비활성=회색")

        def lb(lu, ld, i, L, it):
            vals, dm, hv, sp = i
            rect, fill, fsel, bord, bsel, text, tc, tcs, size, bold, grp, val, rad = d.unb(
                lu, ld, sp, ["Rect", "Fill", "Fill Sel", "Border", "Border Sel", "Text", "Text Color", "Text Sel",
                             "Size", "Bold", "Group", "Value", "Radius"])
            sel = d.eq(lu, ld, d.idx1(lu, ld, vals, grp), val)
            dim = d.idx1(lu, ld, dm, grp)
            hov = d.and_(lu, ld, d.and_(lu, ld, d.eq(lu, ld, it, hv), d.ge(lu, ld, grp, d.i32(lu, ld, 0))),
                         d.not_(lu, ld, dim))
            f = d.sel(lu, ld, dim, u32(d, lu, ld, DIM_FILL), d.sel(lu, ld, sel, fsel, fill))
            b = d.sel(lu, ld, dim, u32(d, lu, ld, DIM_BORDER),
                      d.sel(lu, ld, hov, u32(d, lu, ld, HOVER_B), d.sel(lu, ld, sel, bsel, bord)))
            t = d.sel(lu, ld, dim, u32(d, lu, ld, DIM_TEXT), d.sel(lu, ld, sel, tcs, tc))
            pw = d.sel(lu, ld, d.or_(lu, ld, sel, hov), d.const(lu, ld, "uint16", "3"), d.const(lu, ld, "uint16", "2"))
            box = d.ne(lu, ld, fill, u32(d, lu, ld, TRANSP))

            def draw_box(f2, d2, j):
                p0, r_, f_, b_, rd, w_ = j
                diam = d.add(f2, d2, rd, rd)
                p1 = rrect(d, f2, d2, p0, r_, f_, True, diam)
                return [rrect(d, f2, d2, p1, r_, b_, False, diam, w_)]
            p = d.case(lu, ld, box, [L[0], rect, f, b, rad, pw], 1,
                       [("True", "둥근 버튼", draw_box), ("False", "글자만", lambda f2, d2, j: [j[0]])])[0]
            l, tp, r, bt = d.unb(lu, ld, rect, ["left", "top", "right", "bottom"])
            two = d.const(lu, ld, "int16", "2")
            cx = d.div(lu, ld, d.add(lu, ld, l, r), two)
            cy = d.div(lu, ld, d.add(lu, ld, tp, bt), two)
            cxi = d.node(lu, ld, "To Word Integer", [("number", cx)], ["16bit integer"])["16bit integer"]
            cyi = d.node(lu, ld, "To Word Integer", [("number", cy)], ["16bit integer"])["16bit integer"]
            p = text_at(d, lu, ld, p, text, cxi, cyi, size, bold, t)
            return [], [p], None
        _, fin = d.loop("For Loop", fu, dep, [(values, None), (dims, None), (hover, None), (specs, "index")],
                        [pic], lb)
        return [fin[0]]

    subvi(d, [("Picture", "picture", "", "r0", "recommended"),
              ("Specs", SPECS, "[]", "r5", "required"),
              ("Values", "array{int32}", "[]", "r7", "recommended"),
              ("Dim Groups", "array{bool}", "[]", "r9", "recommended"),
              ("Hover", "int32", "-1", "r1", "recommended")],
          [("New Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Draw_Buttons.xml", "UI_Draw_Buttons.vi",
                   "Specs 배열의 버튼/글자를 둥근 사각형 + 가운데 글자로 그린다.\\0A"
                   "Values[Group] = Value면 선택 상태, Hover = 마우스가 올라간 항목 번호, Dim Groups[Group] = 비활성.")


# ---------------------------------------------------------------- UI_Hit_Test
def hit_test():
    d = Doc()

    def body(fu, dep, ins):
        x, y, specs, dims = ins
        d.label(fu, dep, "Group>=0 이고 비활성이 아닌 첫 번째 사각형")

        def lb(lu, ld, i, L, it):
            xx, yy, dm, sp = i
            rect, grp = d.unb(lu, ld, sp, ["Rect", "Group"])
            l, t, r, b = d.unb(lu, ld, rect, ["left", "top", "right", "bottom"])
            inside = d.and_(lu, ld, d.inrange(lu, ld, xx, l, r), d.inrange(lu, ld, yy, t, b))
            ok = d.and_(lu, ld, d.and_(lu, ld, inside, d.ge(lu, ld, grp, d.i32(lu, ld, 0))),
                        d.not_(lu, ld, d.idx1(lu, ld, dm, grp)))
            first = d.and_(lu, ld, ok, d.lt(lu, ld, L[0], d.i32(lu, ld, 0)))
            return [], [d.sel(lu, ld, first, it, L[0])], None
        _, fin = d.loop("For Loop", fu, dep, [(x, None), (y, None), (dims, None), (specs, "index")],
                        [d.i32(fu, dep, -1)], lb)
        idx = fin[0]
        g, v = d.unb(fu, dep, d.idx1(fu, dep, specs, idx), ["Group", "Value"])
        found = d.ge(fu, dep, idx, d.i32(fu, dep, 0))
        m1 = d.i32(fu, dep, -1)
        return [idx, d.sel(fu, dep, found, g, m1), d.sel(fu, dep, found, v, m1)]

    subvi(d, [("X", "int32", "0", "r0", "required"), ("Y", "int32", "0", "r5", "required"),
              ("Specs", SPECS, "[]", "r7", "required"), ("Dim Groups", "array{bool}", "[]", "r9", "recommended")],
          [("Index", "int32", "-1", "r4"), ("Group", "int32", "-1", "r6"), ("Value", "int32", "-1", "r8")], body)
    return d.write(f"{OUT}/UI_Hit_Test.xml", "UI_Hit_Test.vi",
                   "(X,Y)가 들어 있는 버튼 찾기. 없으면 Index/Group/Value = -1. 글자(Group -1)와 비활성 그룹은 제외.")


# ---------------------------------------------------------------- UI_Render
def render():
    d = Doc()

    def body(fu, dep, ins):
        ctx = ins[0]
        scr, sets, bs, st, pst, hov, hb, wl, s1, s2, dr, txt, tcol = d.unb(
            fu, dep, ctx, ["Screen", "Settings", "Board", "Status", "Player Stone", "Hover", "Hover Button",
                           "Win Line", "Score 1", "Score 2", "Draws", "Status Text", "Status Color"])
        pvp = d.eq(fu, dep, d.idx1(fu, dep, sets, d.i32(fu, dep, 0)), d.i32(fu, dep, 1))
        is_set = d.eq(fu, dep, scr, d.const(fu, dep, SCREEN, "0"))
        d.label(fu, dep, "화면: 설정 / 게임")

        def settings(f, dp, j):
            sets_, hb_, pvp_ = j[1], j[6], j[13]
            p = d.call(f, dp, "Draw Rectangle.vi", [("rect", rect_c(d, f, dp, 0, 0, W, H)), ("fill?(F)", d.b(f, dp, True)),
                                                    ("color(black)", u32(d, f, dp, BG))], ["new picture"])["new picture"]
            p = rrect(d, f, dp, p, rect_c(d, f, dp, 36, 50, 556, 700), u32(d, f, dp, 0xFFFFFF), True, i16(d, f, dp, 40))
            for cx, col in ((268, 0x1C1C1C), (324, 0xFFFFFF)):
                ctr = d.const(f, dp, CENTER16, f"[{cx},40]")
                p = d.call(f, dp, "Draw Circle by Radius.vi", [("picture", p), ("pixel center", ctr), ("radius", i16(d, f, dp, 22)),
                                                              ("fill?(F)", d.b(f, dp, True)), ("color(black)", u32(d, f, dp, col))],
                           ["new picture"])["new picture"]
                p = d.call(f, dp, "Draw Circle by Radius.vi", [("picture", p), ("pixel center", ctr), ("radius", i16(d, f, dp, 22)),
                                                              ("fill?(F)", d.b(f, dp, False)), ("color(black)", u32(d, f, dp, 0x555555))],
                           ["new picture"])["new picture"]
            d.label(f, dp, "배경 + 흰 카드 + 흑백 돌 장식")
            specs = d.call(f, dp, "UI_Settings_Layout.vi", [("error in", d.noerr(f, dp))], ["Specs", "error out"])["Specs"]
            dims = d.node(f, dp, "Build Array", [("element", d.b(f, dp, False)), ("element", pvp_), ("element", pvp_)],
                          ["appended array"])["appended array"]
            o = d.call(f, dp, "UI_Draw_Buttons.vi", [("Picture", p), ("Specs", specs), ("Values", sets_), ("Dim Groups", dims),
                                                     ("Hover", hb_), ("error in", d.noerr(f, dp))], ["New Picture", "error out"])
            return [o["New Picture"]]

        def game(f, dp, j):
            sets_, bs_, st_, pst_, hov_, hb_, wl_, s1_, s2_, dr_, txt_, tcol_, pvp_ = j[1:]
            p = d.call(f, dp, "UI_Draw_Board.vi", [("Board State", bs_), ("Hover", hov_), ("Win Line", wl_),
                                                   ("error in", d.noerr(f, dp))], ["Picture", "error out"])["Picture"]
            p = d.call(f, dp, "Draw Rectangle.vi", [("picture", p), ("rect", rect_c(d, f, dp, 0, 592, W, H)),
                                                    ("fill?(F)", d.b(f, dp, True)), ("color(black)", u32(d, f, dp, BG))],
                       ["new picture"])["new picture"]
            p = rrect(d, f, dp, p, rect_c(d, f, dp, 12, 602, 580, 678), u32(d, f, dp, 0xFFFFFF), True, i16(d, f, dp, 32))
            d.label(f, dp, "아래: 상태 카드 + 버튼 3개")
            # whose turn
            hist = d.unb(f, dp, bs_, ["Move History"])[0]
            q, r = qr(d, f, dp, d.size(f, dp, hist), d.i32(f, dp, 2))
            B, Wt = d.const(f, dp, STONE, BLACK), d.const(f, dp, STONE, WHITE)
            parity = d.sel(f, dp, d.eq(f, dp, r, d.i32(f, dp, 0)), B, Wt)
            ai_turn = d.eq(f, dp, st_, d.const(f, dp, GSTAT, "2"))
            turn = d.sel(f, dp, pvp_, parity, d.sel(f, dp, ai_turn, opp_stone(d, f, dp, pst_), pst_))
            show = d.or_(f, dp, d.eq(f, dp, st_, d.const(f, dp, GSTAT, "1")), ai_turn)

            def stone(f2, d2, k):
                isb = d.eq(f2, d2, k[1], d.const(f2, d2, STONE, BLACK))
                col = d.sel(f2, d2, isb, u32(d, f2, d2, 0x1C1C1C), u32(d, f2, d2, 0xFFFFFF))
                ctr = d.const(f2, d2, CENTER16, "[46,640]")
                p1 = d.call(f2, d2, "Draw Circle by Radius.vi", [("picture", k[0]), ("pixel center", ctr), ("radius", i16(d, f2, d2, 17)),
                                                                 ("fill?(F)", d.b(f2, d2, True)), ("color(black)", col)],
                            ["new picture"])["new picture"]
                p2 = d.call(f2, d2, "Draw Circle by Radius.vi", [("picture", p1), ("pixel center", ctr), ("radius", i16(d, f2, d2, 17)),
                                                                 ("fill?(F)", d.b(f2, d2, False)), ("color(black)", u32(d, f2, d2, 0x555555))],
                            ["new picture"])["new picture"]
                return [p2]
            p = d.case(f, dp, show, [p, turn], 1, [("True", "차례 돌 표시", stone), ("False", "표시 안 함", lambda f2, d2, k: [k[0]])])[0]
            p = text_at(d, f, dp, p, txt_, i16(d, f, dp, 306), i16(d, f, dp, 626), i16(d, f, dp, 20), d.b(f, dp, True), tcol_)
            # score line
            n2s = lambda v: d.node(f, dp, "Number To Decimal String", [("number", v)], ["decimal integer string"])["decimal integer string"]
            left = d.sel(f, dp, pvp_, d.const(f, dp, "string", esc("흑 ")), d.const(f, dp, "string", esc("플레이어 ")))
            right = d.sel(f, dp, pvp_, d.const(f, dp, "string", esc(" 백")), d.const(f, dp, "string", esc(" AI")))
            cat = d.node(f, dp, "Concatenate Strings",
                         [("string", left), ("string", n2s(s1_)), ("string", d.const(f, dp, "string", " \\3A ")),
                          ("string", n2s(s2_)), ("string", right), ("string", d.const(f, dp, "string", esc("   ·   무승부 "))),
                          ("string", n2s(dr_))], ["concatenated string"])["concatenated string"]
            p = text_at(d, f, dp, p, cat, i16(d, f, dp, 306), i16(d, f, dp, 658), i16(d, f, dp, 15), d.b(f, dp, False),
                        u32(d, f, dp, SUB_T))
            specs = d.call(f, dp, "UI_Game_Layout.vi", [("error in", d.noerr(f, dp))], ["Specs", "error out"])["Specs"]
            o = d.call(f, dp, "UI_Draw_Buttons.vi", [("Picture", p), ("Specs", specs), ("Hover", hb_),
                                                     ("error in", d.noerr(f, dp))], ["New Picture", "error out"])
            return [o["New Picture"]]
        return d.case(fu, dep, is_set, [scr, sets, bs, st, pst, hov, hb, wl, s1, s2, dr, txt, tcol, pvp], 1,
                      [("True", "설정 화면", settings), ("False", "게임 화면", game)])

    subvi(d, [("Context", CTX, CTX0, "r0", "required")], [("Picture", "picture", "", "r4")], body)
    return d.write(f"{OUT}/UI_Render.xml", "UI_Render.vi",
                   "게임 Context를 화면 전체(592x780) Picture로 그린다.\\0A"
                   "설정 화면: 갈색 배경 + 흰 카드 + 모드/선공/난이도/규칙 선택 + 게임 시작.\\0A"
                   "게임 화면: 오목판 + 상태 카드(차례 돌, 상태, 점수) + 무르기/새 게임/설정 버튼.")


if __name__ == "__main__":
    print(layout("UI_Settings_Layout", SETTINGS_SPECS, "설정 화면 버튼/글자 배치표. Group 0=모드, 1=선공, 2=난이도, 3=규칙, 4=게임 시작."))
    print(layout("UI_Game_Layout", GAME_SPECS, "게임 화면 버튼 배치표. Group 5: 0=무르기, 1=새 게임, 2=설정."))
    print(draw_buttons(), hit_test(), render())
