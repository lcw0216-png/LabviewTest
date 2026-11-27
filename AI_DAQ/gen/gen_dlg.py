"""Popup dialogs: settings, channel, graph window. Each opens its own front panel when called."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
LIVE0 = "[[],[],0.001,false,false,,]"


def vi_prop(d, p, dep, err, pairs):
    """write properties of This VI (unwired reference)"""
    fields = ",".join("write+" + n for n, _ in pairs)
    return d.node(p, dep, "Property Node", [("error in (no error)", err)] + list(pairs), ["error out"],
                  fields=fields, type="{LV.VI}")["error out"]


def hide(d, p, dep, err, labels, typ="{LV.Control}"):
    for lab in labels:
        err = d.node(p, dep, "Property Node", [("error in (no error)", err), ("Visible", d.b(p, dep, False))], ["error out"],
                     fields="write+Visible", link=lab, type=typ)["error out"]
    return err


def edit_dialog(title, ctl_label, ctl_type, ctl_val, desc, out_label, apply_all=False):
    """Generic OK/Cancel editor: the input control itself is the editor on the popup panel."""
    d = Doc()
    R = "root"
    K = kr
    src = d.ctl(R, 1, K(ctl_label), ctl_type, ctl_val, conIdx=0, conn="required")
    if apply_all:
        d.ctl(R, 1, K("모든 채널에 적용"), "bool", "false")
    err = d.ctl(R, 1, "error in", ERR_T, "[false,0,]", conIdx=11, conn="required")
    d.label(R, 1, "팝업: 패널 열기 -> 확인/취소 대기 -> 닫기")
    e = vi_prop(d, R, 1, err, [("Front Panel Window\\3AOpen", d.b(R, 1, True)),
                               ("Front Panel Window\\3ATitle", d.const(R, 1, "string", esc(title))),
                               ("Front Panel Window\\3APanel Bounds",
                                d.const(R, 1, "cluster{int32.Left,int32.Top,int32.Right,int32.Bottom}", "[300,200,1060,720]"))])
    hidden = [out_label, "OK?", "error in", "error out"] + (["Apply All"] if apply_all else [])
    e = hide(d, R, 1, e, hidden)

    def lb(lu, ld, i, L, it):
        cur = i[0]
        F, T = (lambda a, b: d.b(a, b, False)), (lambda a, b: d.b(a, b, True))

        def ok(f, fp, j):
            d.ctl(f, fp, K("확인"), "bool", "false", style="latched")
            v = d.node(f, fp, "Property Node", [("error in (no error)", d.noerr(f, fp))], ["Value", "error out"],
                       fields="read+Value", link=K(ctl_label), type="{LV.Control}")
            d.label(f, fp, "편집한 값을 읽어 확인")
            outs = [T(f, fp), T(f, fp), v["Value"]]
            if apply_all:
                a = d.node(f, fp, "Property Node", [("error in (no error)", v["error out"])], ["Value", "error out"],
                           fields="read+Value", link=K("모든 채널에 적용"), type="{LV.Control}")["Value"]
                outs.append(a)
            return outs

        def cancel(f, fp, j):
            d.ctl(f, fp, K("취소"), "bool", "false", style="latched")
            return [T(f, fp), F(f, fp), j[0]] + ([F(f, fp)] if apply_all else [])

        def close(f, fp, j):
            return [T(f, fp), F(f, fp), j[0]] + ([F(f, fp)] if apply_all else [])
        n = 4 if apply_all else 3
        o = d.event(lu, ld, [cur], n, [
            (' "' + K("확인") + '"\\3A Value Change ', "", ok),
            (' "' + K("취소") + '"\\3A Value Change ', "", cancel),
            (' Panel Close? ', "", close),
        ])
        return [(x, None) for x in o[1:]], [L[0]], o[0]
    outs, fin = d.loop("While Loop", R, 1, [(src, None)], [e], lb, label="확인/취소 대기")
    okv, val = outs[0], outs[1]
    d.label(R, 1, "에러선을 루프 시프트 레지스터로 통과: 루프 종료 후에만 창 닫기")
    e = vi_prop(d, R, 1, fin[0], [("Front Panel Window\\3AOpen", d.b(R, 1, False))])
    d.label(R, 1, "확인이면 편집값, 취소면 원래 값")
    d.ind(R, 1, out_label, ctl_type, ctl_val, d.sel(R, 1, okv, val, src), conIdx=4)
    d.ind(R, 1, "OK?", "bool", "false", okv, conIdx=6)
    if apply_all:
        d.ind(R, 1, "Apply All", "bool", "false", outs[2], conIdx=8)
    d.ind(R, 1, "error out", ERR_T, "[false,0,]", e, conIdx=15)
    return d, desc


def dlg_settings():
    d, desc = edit_dialog("측정 설정", "Settings", SETTINGS, SETTINGS0,
                          "측정 옵션 팝업: 샘플링 속도, 채널당 샘플 수, 섀시별 물리 채널, 저장 폴더. 확인이면 OK? = True.",
                          "Settings out")
    return d.write(f"{OUT}/Dlg_Settings.xml", "Dlg_Settings.vi", desc)


def dlg_channel():
    d, desc = edit_dialog("채널 설정", "Channel", CHANNEL, CH0,
                          "채널 설정 팝업: 상한/하한, 저장(Save), 그래프(Graph), 스케일 Min/Max, 단위.\\0A"
                          "'모든 채널에 적용'을 켜면 이름을 뺀 설정을 128채널 전체에 적용(Apply All).",
                          "Channel out", apply_all=True)
    return d.write(f"{OUT}/Dlg_Channel.xml", "Dlg_Channel.vi", desc)


def dlg_graph():
    d = Doc()
    R = "root"
    chs = d.ctl(R, 1, "Channels", CHANNELS, "[]", conIdx=0, conn="required")
    err = d.ctl(R, 1, "error in", ERR_T, "[false,0,]", conIdx=11, conn="required")
    d.label(R, 1, "그래프 팝업: 그래프 큐(최신 데이터)를 받아 큰 화면에 그림")
    e = vi_prop(d, R, 1, err, [("Front Panel Window\\3AOpen", d.b(R, 1, True)),
                               ("Front Panel Window\\3ATitle", d.const(R, 1, "string", esc("그래프 - 선택 채널")))])
    e = hide(d, R, 1, e, ["Channels", "error in", "error out"])
    e = d.node(R, 1, "Property Node", [("error in (no error)", e), ("Label.Visible", d.b(R, 1, False)),
                                       ("Position\\3ALeft", d.i32(R, 1, 0)), ("Position\\3ATop", d.i32(R, 1, 0)),
                                       ("Draw Area Size", d.const(R, 1, "cluster{int32.Width,int32.Height}", "[1300,720]"))],
               ["error out"], fields="write+Label.Visible,write+Position\\3ALeft,write+Position\\3ATop,write+Draw Area Size",
               link="Graph", type="{LV.Picture}")["error out"]
    e = vi_prop(d, R, 1, e, [("Front Panel Window\\3APanel Bounds",
                              d.const(R, 1, "cluster{int32.Left,int32.Top,int32.Right,int32.Bottom}", "[120,120,1420,840]"))])
    gq = d.node(R, 1, "Obtain Queue", [("name (unnamed)", d.const(R, 1, "string", "AIDAQ_GRAPH")),
                                       ("element data type", d.const(R, 1, LIVE, LIVE0)),
                                       ("max queue size (-1\\2C unlimited)", d.i32(R, 1, 1)), ("error in (no error)", e)],
                ["queue out", "created new?", "error out"])

    def lb(lu, ld, i, L, it):
        q, cs = i
        F, T = (lambda a, b: d.b(a, b, False)), (lambda a, b: d.b(a, b, True))

        def tick(f, fp, j):
            dq = d.node(f, fp, "Dequeue Element", [("queue", j[0]), ("timeout in ms (-1)", d.i32(f, fp, 0)),
                                                   ("error in (no error)", d.noerr(f, fp))],
                        ["queue out", "element", "timed out?", "error out"])

            def draw(g, gp, k):
                data, dt = d.unb(g, gp, k[0], ["Data", "dt"])
                p = d.call(g, gp, "Draw Rectangle.vi", [("rect", rect_c(d, g, gp, 0, 0, 1300, 720)), ("fill?(F)", d.b(g, gp, True)),
                                                        ("color(black)", u32(d, g, gp, 0xFFFFFF))], ["new picture"])["new picture"]
                p = d.call(g, gp, "UI_Draw_Graph.vi", [("Picture", p), ("Plot Rect", rect_c(d, g, gp, 80, 30, 1130, 680)),
                                                       ("Data", data), ("Channels", k[1]), ("dt", dt), ("error in", d.noerr(g, gp))],
                           ["New Picture", "error out"])["New Picture"]
                d.ind(g, gp, "Graph", "picture", "", p)
                return []
            d.case(f, fp, dq["timed out?"], [dq["element"], j[1]], 0,
                   [("False", "새 데이터 그리기", draw), ("True", "데이터 없음", lambda g, gp, k: [])])
            return [F(f, fp)]

        def close(f, fp, j):
            d.ctl(f, fp, kr("닫기"), "bool", "false", style="latched")
            return [T(f, fp)]
        o = d.event(lu, ld, [q, cs], 1, [
            (' Timeout ', "", tick),
            (' "' + kr("닫기") + '"\\3A Value Change ', "", close),
            (' Panel Close? ', "", lambda f, fp, j: [T(f, fp)]),
        ], timeoutin=d.i32(lu, ld, 100))
        return [], [L[0]], o[0]
    _, fin = d.loop("While Loop", R, 1, [(gq["queue out"], None), (chs, None)], [gq["error out"]], lb, label="그래프 갱신 (100 ms)")
    d.label(R, 1, "에러선을 루프 시프트 레지스터로 통과: 루프 종료 후 큐 해제 및 창 닫기")
    r = d.node(R, 1, "Release Queue", [("queue", gq["queue out"]), ("error in (no error)", fin[0])],
               ["queue name", "remaining elements", "error out"])
    e = vi_prop(d, R, 1, r["error out"], [("Front Panel Window\\3AOpen", d.b(R, 1, False))])
    d.ind(R, 1, "error out", ERR_T, "[false,0,]", e, conIdx=15)
    return d.write(f"{OUT}/Dlg_Graph.xml", "Dlg_Graph.vi",
                   "그래프 팝업 창(1300x720): AIDAQ_GRAPH 큐의 최신 데이터를 100 ms마다 그림. 닫기 버튼이나 창 닫기로 종료.")


if __name__ == "__main__":
    for fn in (dlg_settings, dlg_channel, dlg_graph):
        print(fn.__name__, fn())
