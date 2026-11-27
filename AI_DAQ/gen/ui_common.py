"""Generic button drawing / hit test (shared with the Omok project)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
DIM_FILL, DIM_BORDER, DIM_TEXT, HOVER_B = 0xF3F2F1, 0xE1DFDD, 0xC8C6C4, 0x262626


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


