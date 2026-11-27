"""AI_DAQ_Main.vi (state machine UI) + helper SubVIs."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from gen_engine import MSG0, LIVE0

OUT = sys.argv[1]
W2, H2 = 1600, 940
CTX = ("cluster{" + CHANNELS + ".Channels," + SETTINGS + ".Settings,bool.Running,bool.Logging,array.2{double}.Data,"
       "double.dt,int32.Hover,int32.Selected,string.Message,path.Log File}")
CTX0 = "[[]," + SETTINGS0 + ",false,false,[],0.001,-1,-1,,]"
ST = {n: str(i) for i, n in enumerate(["Init", "Wait", "Update", "Settings", "Start", "Stop", "Save", "Channel", "Graph", "Exit"])}


def ch_apply():
    d = Doc()

    def body(fu, dep, ins):
        chs, idx, ch, allf = ins
        d.label(fu, dep, "한 채널 교체 또는 전체 채널에 설정 복사")

        def one(f, fp, j):
            return [d.node(f, fp, "Replace Array Subset", [("array", j[0]), ("index", j[1]), ("new element/subarray", j[2])],
                           ["output array"])["output array"]]

        def every(f, fp, j):
            hi, lo, sv, gr, smin, smax, unit = d.unb(f, fp, j[2], ["High Limit", "Low Limit", "Save", "Graph", "Scale Min",
                                                                   "Scale Max", "Unit"])

            def lb(lu, ld, i, L, it):
                c = i[7]
                return [(d.bnd(lu, ld, c, [("High Limit", i[0]), ("Low Limit", i[1]), ("Save", i[2]), ("Graph", i[3]),
                                           ("Scale Min", i[4]), ("Scale Max", i[5]), ("Unit", i[6])]), "index")], [], None
            o, _ = d.loop("For Loop", f, fp, [(hi, None), (lo, None), (sv, None), (gr, None), (smin, None), (smax, None),
                                              (unit, None), (j[0], "index")], [], lb)
            d.label(f, fp, "이름과 현재값은 유지")
            return [o[0]]
        return d.case(fu, dep, allf, [chs, idx, ch], 1, [("True", "전체 적용", every), ("False", "한 채널", one)])

    subvi(d, [("Channels", CHANNELS, "[]", "r0", "required"), ("Index", "int32", "0", "r5", "required"),
              ("Channel", CHANNEL, CH0, "r7", "required"), ("Apply All", "bool", "false", "r9", "recommended")],
          [("Channels out", CHANNELS, "[]", "r4")], body)
    return d.write(f"{OUT}/Ch_Apply.xml", "Ch_Apply.vi",
                   "채널 설정 팝업 결과 반영: Apply All이면 상/하한·저장·그래프·스케일·단위를 128채널 모두에(이름/값 유지), 아니면 Index 채널만 교체.")


def ch_merge():
    d = Doc()

    def body(fu, dep, ins):
        chs, vals = ins
        d.label(fu, dep, "측정값(평균)을 각 채널 Value에 넣기")

        def lb(lu, ld, i, L, it):
            c, vs = i
            return [(d.bnd(lu, ld, c, [("Value", d.idx1(lu, ld, vs, it))]), "index")], [], None
        o, _ = d.loop("For Loop", fu, dep, [(chs, "index"), (vals, None)], [], lb)
        has = d.gt(fu, dep, d.size(fu, dep, vals), d.i32(fu, dep, 0))
        return [d.sel(fu, dep, has, o[0], chs)]

    subvi(d, [("Channels", CHANNELS, "[]", "r0", "required"), ("Values", "array{double}", "[]", "r5", "required")],
          [("Channels out", CHANNELS, "[]", "r4")], body)
    return d.write(f"{OUT}/Ch_Merge_Values.xml", "Ch_Merge_Values.vi", "Values[i]를 Channels[i].Value로 복사(Values가 비면 그대로).")


def status_text():
    d = Doc()

    def body(fu, dep, ins):
        sets, run, lg, lf, msg = ins
        rate, n = d.unb(fu, dep, sets, ["Sample Rate (Hz)", "Samples per Channel"])
        s = lambda t: d.const(fu, dep, "string", esc(t))
        name = d.node(fu, dep, "Strip Path", [("path", lf)], ["stripped path", "name"])["name"]
        d.label(fu, dep, "상단 상태 문구 만들기")
        info = d.node(fu, dep, "Concatenate Strings",
                      [("string", d.sel(fu, dep, run, s("● 측정 중"), s("○ 대기"))), ("string", s("   ·   ")),
                       ("string", d.node(fu, dep, "Number To Fractional String", [("number", rate), ("precision (6)", d.i32(fu, dep, 0))],
                                         ["F-format string"])["F-format string"]),
                       ("string", s(" Hz   ·   ")),
                       ("string", d.node(fu, dep, "Number To Decimal String", [("number", n)], ["decimal integer string"])["decimal integer string"]),
                       ("string", s(" 샘플/채널")),
                       ("string", d.sel(fu, dep, lg, d.node(fu, dep, "Concatenate Strings", [("string", s("   ·   저장 중 ")), ("string", name)],
                                                            ["concatenated string"])["concatenated string"], s("")))],
                      ["concatenated string"])["concatenated string"]
        empty = d.node(fu, dep, "Empty String/Path?", [("string/path", msg)], ["empty?"])["empty?"]
        return [d.sel(fu, dep, empty, info, d.node(fu, dep, "Concatenate Strings", [("string", info), ("string", s("   ·   ")),
                                                                                   ("string", msg)], ["concatenated string"])["concatenated string"])]

    subvi(d, [("Settings", SETTINGS, SETTINGS0, "r0", "required"), ("Running", "bool", "false", "r5", "recommended"),
              ("Logging", "bool", "false", "r7", "recommended"), ("Log File", "path", "", "r9", "recommended"),
              ("Message", "string", "", "r1", "recommended")],
          [("Status", "string", "", "r4")], body)
    return d.write(f"{OUT}/UI_Status_Text.xml", "UI_Status_Text.vi", "상단 상태 문구: 측정 중/대기, 샘플링 속도, 샘플 수, 저장 파일, 메시지.")


def main():
    d = Doc()
    R = "root"
    d.label(R, 1, "128CH AI 측정/가시화 - 메인 (상태머신)")
    pn = d.node(R, 1, "Property Node", [("error in (no error)", d.noerr(R, 1)), ("Label.Visible", d.b(R, 1, False)),
                                        ("Position\\3ALeft", d.i32(R, 1, 0)), ("Position\\3ATop", d.i32(R, 1, 0)),
                                        ("Draw Area Size", d.const(R, 1, "cluster{int32.Width,int32.Height}", f"[{W2},{H2}]"))],
                ["error out"], fields="write+Label.Visible,write+Position\\3ALeft,write+Position\\3ATop,write+Draw Area Size",
                link="Screen", type="{LV.Picture}")
    win = d.node(R, 1, "Property Node", [("error in (no error)", pn["error out"]),
                                         ("Front Panel Window\\3AShow Scroll Bars", d.b(R, 1, False)),
                                         ("Front Panel Window\\3ATitle", d.const(R, 1, "string", esc("128CH AI 모니터"))),
                                         ("Front Panel Window\\3APanel Bounds",
                                          d.const(R, 1, "cluster{int32.Left,int32.Top,int32.Right,int32.Bottom}", f"[40,40,{40 + W2},{40 + H2}]"))],
                 ["error out"], fields="write+Front Panel Window\\3AShow Scroll Bars,write+Front Panel Window\\3ATitle,"
                                       "write+Front Panel Window\\3APanel Bounds", type="{LV.VI}")
    d.label(R, 1, "창 = 1600x940 캔버스, 이름 있는 큐 준비")

    def obtain(name, typ, lit, size, err):
        o = d.node(R, 1, "Obtain Queue", [("name (unnamed)", d.const(R, 1, "string", name)), ("element data type", d.const(R, 1, typ, lit)),
                                          ("max queue size (-1\\2C unlimited)", d.i32(R, 1, size)), ("error in (no error)", err)],
                   ["queue out", "created new?", "error out"])
        return o["queue out"], o["error out"]
    cq, e = obtain("AIDAQ_CMD", DAQ_MSG, MSG0, -1, win["error out"])
    lq, e = obtain("AIDAQ_LIVE", LIVE, LIVE0, 1, e)
    pq, e = obtain("AIDAQ_POPUP", CHANNELS, "[]", -1, e)
    eng = d.call(R, 1, "DAQ_Engine.vi", [("error in", d.noerr(R, 1))], ["error out"])
    d.label(R, 1, "DAQ 엔진: 별도 루프로 측정/저장")

    # ---------------- graph popup loop
    def pop(lu, ld, i, L, it):
        dq = d.node(lu, ld, "Dequeue Element", [("queue", i[0]), ("error in (no error)", d.noerr(lu, ld))],
                    ["queue out", "element", "timed out?", "error out"])
        quit_ = d.eq(lu, ld, d.size(lu, ld, dq["element"]), d.i32(lu, ld, 0))

        def show(f, fp, j):
            g = d.call(f, fp, "Dlg_Graph.vi", [("Channels", j[0]), ("error in", d.noerr(f, fp))], ["error out"])
            return [g["error out"]]
        o = d.case(lu, ld, quit_, [dq["element"], dq["error out"]], 1,
                   [("False", "그래프 팝업 열기", show), ("True", "종료 신호", lambda f, fp, j: [j[1]])])
        return [(o[0], None)], [], d.or_(lu, ld, quit_, d.unb(lu, ld, dq["error out"], ["status"])[0])
    pop_out, _ = d.loop("While Loop", R, 1, [(pq, None)], [], pop, label="그래프 팝업 루프")

    # ---------------- main UI state machine
    def sm(lu, ld, i, L, it):
        cq_, lq_, pq_ = i
        state, ctx, err = L
        F, T = (lambda a, b: d.b(a, b, False)), (lambda a, b: d.b(a, b, True))
        S = lambda a, b, n: d.const(a, b, UI_STATE, ST[n])

        def send(f, fp, cmd, c, q):
            chs, sets = d.unb(f, fp, c, ["Channels", "Settings"])
            m = d.bnd(f, fp, d.const(f, fp, DAQ_MSG, MSG0), [("Cmd", d.const(f, fp, DAQ_CMD, cmd)), ("Settings", sets), ("Channels", chs)])
            d.node(f, fp, "Enqueue Element", [("queue", q), ("element", m), ("error in (no error)", d.noerr(f, fp))],
                   ["queue out", "timed out?", "error out"])

        def s_init(f, fp, j):
            ch = d.call(f, fp, "Ch_Defaults.vi", [("error in", j[1])], ["Channels", "error out"])
            c = d.bnd(f, fp, j[0], [("Channels", ch["Channels"])])
            send(f, fp, "2", c, j[2])
            d.label(f, fp, "초기화: 128채널 기본값 -> 엔진에 Config")
            return [c, S(f, fp, "Update"), ch["error out"], F(f, fp)]

        # Wait state is written below with explicit event handling
        def s_wait2(f, fp, j):
            c = j[0]
            run = d.unb(f, fp, c, ["Running"])[0]
            nr = d.not_(f, fp, run)
            dims = d.node(f, fp, "Build Array", [("element", run), ("element", run), ("element", nr), ("element", nr)],
                          ["appended array"])["appended array"]

            def down(g, gp, k):
                cc, dm = k
                m = d.node(g, gp, "Property Node", [("error in (no error)", d.noerr(g, gp))], ["Mouse", "error out"],
                           fields="read+Mouse", link="Screen", type="{LV.Picture}")
                pos = d.unb(g, gp, m["Mouse"], ["Mouse Position"])[0]
                xy = d.call(g, gp, "UI_Point_XY.vi", [("Point", pos), ("error in", m["error out"])], ["X", "Y", "error out"])
                specs = d.call(g, gp, "UI_Header_Layout.vi", [("error in", d.noerr(g, gp))], ["Specs", "error out"])["Specs"]
                h = d.call(g, gp, "UI_Hit_Test.vi", [("X", xy["X"]), ("Y", xy["Y"]), ("Specs", specs), ("Dim Groups", dm),
                                                     ("error in", d.noerr(g, gp))], ["Index", "Group", "Value", "error out"])
                t = d.call(g, gp, "UI_Tile_Hit.vi", [("X", xy["X"]), ("Y", xy["Y"]), ("error in", d.noerr(g, gp))],
                           ["Channel Index", "error out"])
                table = d.const(g, gp, "array{" + UI_STATE + "}",
                                "[" + ",".join(ST[n] for n in ["Settings", "Start", "Stop", "Save", "Graph", "Exit"]) + "]",
                                name="Button -> State")
                btn = d.ge(g, gp, h["Group"], d.i32(g, gp, 0))
                tile = d.ge(g, gp, t["Channel Index"], d.i32(g, gp, 0))
                nxt = d.sel(g, gp, btn, d.idx1(g, gp, table, h["Group"]),
                            d.sel(g, gp, tile, S(g, gp, "Channel"), S(g, gp, "Wait")))
                d.label(g, gp, "클릭: 버튼 -> 해당 상태, 타일 -> 채널 설정")
                return [d.bnd(g, gp, cc, [("Selected", t["Channel Index"])]), nxt, F(g, gp)]

            def move(g, gp, k):
                cc, dm = k
                m = d.node(g, gp, "Property Node", [("error in (no error)", d.noerr(g, gp))], ["Mouse", "error out"],
                           fields="read+Mouse", link="Screen", type="{LV.Picture}")
                pos = d.unb(g, gp, m["Mouse"], ["Mouse Position"])[0]
                xy = d.call(g, gp, "UI_Point_XY.vi", [("Point", pos), ("error in", m["error out"])], ["X", "Y", "error out"])
                specs = d.call(g, gp, "UI_Header_Layout.vi", [("error in", d.noerr(g, gp))], ["Specs", "error out"])["Specs"]
                h = d.call(g, gp, "UI_Hit_Test.vi", [("X", xy["X"]), ("Y", xy["Y"]), ("Specs", specs), ("Dim Groups", dm),
                                                     ("error in", d.noerr(g, gp))], ["Index", "Group", "Value", "error out"])
                old = d.unb(g, gp, cc, ["Hover"])[0]
                ch_ = d.ne(g, gp, old, h["Index"])
                d.label(g, gp, "버튼 위 강조가 바뀌면 다시 그림")
                return [d.bnd(g, gp, cc, [("Hover", h["Index"])]), d.sel(g, gp, ch_, S(g, gp, "Update"), S(g, gp, "Wait")), F(g, gp)]
            o = d.event(f, fp, [c, dims], 3, [
                (' "Screen"\\3A Mouse Down ', "", down),
                (' "Screen"\\3A Mouse Move ', "", move),
                (' Panel Close? ', "", lambda g, gp, k: [k[0], S(g, gp, "Exit"), F(g, gp)]),
                (' Timeout ', "", lambda g, gp, k: [k[0], S(g, gp, "Update"), F(g, gp)]),
            ], timeoutin=d.i32(f, fp, 200))
            return [o[0], o[1], j[1], o[2]]

        def s_update(f, fp, j):
            c, e_, q = j[0], j[1], j[3]
            dq = d.node(f, fp, "Dequeue Element", [("queue", q), ("timeout in ms (-1)", d.i32(f, fp, 0)),
                                                   ("error in (no error)", d.noerr(f, fp))],
                        ["queue out", "element", "timed out?", "error out"])

            def got(g, gp, k):
                cc, lv = k
                data, vals, dt, run, lg, msg, lf = d.unb(g, gp, lv, ["Data", "Values", "dt", "Running", "Logging", "Message", "Log File"])
                chs = d.call(g, gp, "Ch_Merge_Values.vi", [("Channels", d.unb(g, gp, cc, ["Channels"])[0]), ("Values", vals),
                                                           ("error in", d.noerr(g, gp))], ["Channels out", "error out"])["Channels out"]
                return [d.bnd(g, gp, cc, [("Channels", chs), ("Data", data), ("dt", dt), ("Running", run), ("Logging", lg),
                                          ("Message", msg), ("Log File", lf)])]
            c2 = d.case(f, fp, dq["timed out?"], [c, dq["element"]], 1,
                        [("False", "새 데이터 반영", got), ("True", "새 데이터 없음", lambda g, gp, k: [k[0]])])[0]
            chs, sets, run, lg, data, dt, hov, msg, lf = d.unb(f, fp, c2, ["Channels", "Settings", "Running", "Logging", "Data",
                                                                           "dt", "Hover", "Message", "Log File"])
            st = d.call(f, fp, "UI_Status_Text.vi", [("Settings", sets), ("Running", run), ("Logging", lg), ("Log File", lf),
                                                     ("Message", msg), ("error in", d.noerr(f, fp))], ["Status", "error out"])
            tk = d.node(f, fp, "Tick Count (ms)", [], ["millisecond timer value"])["millisecond timer value"]
            _, ph = qr(d, f, fp, d.node(f, fp, "Quotient & Remainder", [("x", tk), ("y", d.const(f, fp, "uint32", "400"))],
                                        ["x-y*floor(x/y)", "floor(x/y)"])["floor(x/y)"], d.const(f, fp, "uint32", "2"))
            phase = d.eq(f, fp, ph, d.const(f, fp, "uint32", "0"))
            d.label(f, fp, "화면 갱신 (400 ms 주기 점멸)")
            r = d.call(f, fp, "UI_Render_Main.vi", [("Channels", chs), ("Data", data), ("dt", dt), ("Running", run),
                                                    ("Logging", lg), ("Hover Button", hov), ("Phase", phase),
                                                    ("Status", st["Status"]), ("error in", d.noerr(f, fp))], ["Picture", "error out"])
            d.ind(f, fp, "Screen", "picture", "", r["Picture"])
            return [c2, S(f, fp, "Wait"), e_, F(f, fp)]

        def s_settings(f, fp, j):
            c = j[0]
            sets = d.unb(f, fp, c, ["Settings"])[0]
            dl = d.call(f, fp, "Dlg_Settings.vi", [("Settings", sets), ("error in", d.noerr(f, fp))],
                        ["Settings out", "OK?", "error out"])
            d.label(f, fp, "측정 옵션 팝업 (대기 중에만 버튼 활성)")
            return [d.bnd(f, fp, c, [("Settings", dl["Settings out"])]), S(f, fp, "Update"), j[1], F(f, fp)]

        def s_cmd(cmd, msg):
            def fn(f, fp, j):
                send(f, fp, cmd, j[0], j[2])
                c = d.bnd(f, fp, j[0], [("Message", d.const(f, fp, "string", esc(msg)))])
                return [c, S(f, fp, "Update"), j[1], F(f, fp)]
            return fn

        def s_save(f, fp, j):
            lg = d.unb(f, fp, j[0], ["Logging"])[0]
            chs, sets = d.unb(f, fp, j[0], ["Channels", "Settings"])
            m = d.bnd(f, fp, d.const(f, fp, DAQ_MSG, MSG0),
                      [("Cmd", d.sel(f, fp, lg, d.const(f, fp, DAQ_CMD, "4"), d.const(f, fp, DAQ_CMD, "3"))), ("Settings", sets),
                       ("Channels", chs)])
            d.node(f, fp, "Enqueue Element", [("queue", j[2]), ("element", m), ("error in (no error)", d.noerr(f, fp))],
                   ["queue out", "timed out?", "error out"])
            d.label(f, fp, "저장 중이면 Log Off, 아니면 Log On")
            return [j[0], S(f, fp, "Update"), j[1], F(f, fp)]

        def s_channel(f, fp, j):
            c = j[0]
            chs, sel = d.unb(f, fp, c, ["Channels", "Selected"])
            dl = d.call(f, fp, "Dlg_Channel.vi", [("Channel", d.idx1(f, fp, chs, sel)), ("error in", d.noerr(f, fp))],
                        ["Channel out", "OK?", "Apply All", "error out"])

            def apply(g, gp, k):
                a = d.call(g, gp, "Ch_Apply.vi", [("Channels", k[1]), ("Index", k[2]), ("Channel", k[3]), ("Apply All", k[4]),
                                                  ("error in", d.noerr(g, gp))], ["Channels out", "error out"])
                c2 = d.bnd(g, gp, k[0], [("Channels", a["Channels out"])])
                send(g, gp, "2", c2, k[5])
                return [c2]
            c3 = d.case(f, fp, dl["OK?"], [c, chs, sel, dl["Channel out"], dl["Apply All"], j[2]], 1,
                        [("True", "적용 + 엔진 Config", apply), ("False", "취소", lambda g, gp, k: [k[0]])])[0]
            d.label(f, fp, "타일 클릭: 채널 설정 팝업")
            return [c3, S(f, fp, "Update"), j[1], F(f, fp)]

        def s_graph(f, fp, j):
            chs = d.unb(f, fp, j[0], ["Channels"])[0]
            d.node(f, fp, "Enqueue Element", [("queue", j[4]), ("element", chs), ("error in (no error)", d.noerr(f, fp))],
                   ["queue out", "timed out?", "error out"])
            d.label(f, fp, "그래프 팝업 루프에 열기 요청")
            return [j[0], S(f, fp, "Update"), j[1], F(f, fp)]

        def s_exit(f, fp, j):
            send(f, fp, "5", j[0], j[2])
            d.node(f, fp, "Enqueue Element", [("queue", j[4]), ("element", d.const(f, fp, CHANNELS, "[]")),
                                              ("error in (no error)", d.noerr(f, fp))], ["queue out", "timed out?", "error out"])
            d.label(f, fp, "종료: 엔진/팝업 루프에 종료 알림")
            return [j[0], S(f, fp, "Exit"), j[1], T(f, fp)]
        o = d.case(lu, ld, state, [ctx, err, cq_, lq_, pq_], 4, [
            ('"Init"', "초기화", s_init),
            ('"Wait"', "이벤트 대기 (200 ms)", s_wait2),
            ('"Update"', "데이터 반영 + 화면 그리기", s_update),
            ('"Settings"', "측정 설정 팝업", s_settings),
            ('"Start"', "측정 시작", s_cmd("0", "측정 시작 요청")),
            ('"Stop"', "측정 정지", s_cmd("1", "측정 정지 요청")),
            ('"Save"', "TDMS 저장 시작/끝", s_save),
            ('"Channel"', "채널 설정 팝업", s_channel),
            ('"Graph"', "그래프 팝업", s_graph),
            ('"Exit"', "종료", s_exit),
        ])
        c, nxt, e2, stop = o
        return [(e2, None)], [nxt, c, e2], d.or_(lu, ld, stop, d.unb(lu, ld, e2, ["status"])[0])
    sm_out, _ = d.loop("While Loop", R, 1, [(cq, None), (lq, None), (pq, None)],
                       [d.const(R, 1, UI_STATE, ST["Init"]), d.const(R, 1, CTX, CTX0), e], sm, label="UI 상태머신")
    d.label(R, 1, "세 루프 종료 후 큐 해제, 오류 합치기")
    me = d.node(R, 1, "Merge Errors", [("error in", sm_out[0]), ("error in", eng["error out"]), ("error in", pop_out[0])],
                ["error out"])["error out"]
    r1 = d.node(R, 1, "Release Queue", [("queue", cq), ("error in (no error)", me)], ["queue name", "remaining elements", "error out"])
    r2 = d.node(R, 1, "Release Queue", [("queue", lq), ("error in (no error)", r1["error out"])], ["queue name", "remaining elements", "error out"])
    r3 = d.node(R, 1, "Release Queue", [("queue", pq), ("error in (no error)", r2["error out"])], ["queue name", "remaining elements", "error out"])
    d.call(R, 1, "Simple Error Handler.vi", [("error in (no error)", r3["error out"])], ["error out"])
    return d.write(f"{OUT}/AI_DAQ_Main.xml", "AI_DAQ_Main.vi",
                   "128채널(NI 9178 x2 + NI 9203 x16) 전류 입력 측정/가시화 메인.\\0A"
                   "UI 상태머신(Init/Wait/Update/Settings/Start/Stop/Save/Channel/Graph/Exit) + DAQ 엔진 + 그래프 팝업 루프.\\0A"
                   "창 전체가 Picture 'Screen' 하나: 상단 버튼 6개, 128채널 타일, 하단 그래프.")


def point_xy():
    d = Doc()

    def body(fu, dep, ins):
        x, y = d.unb(fu, dep, ins[0], ["X", "Y"])
        return [x, y]
    subvi(d, [("Point", "cluster{int32.X,int32.Y}", "[0,0]", "r0", "required")],
          [("X", "int32", "0", "r4"), ("Y", "int32", "0", "r6")], body)
    return d.write(f"{OUT}/UI_Point_XY.xml", "UI_Point_XY.vi", "마우스 좌표 클러스터 -> X, Y.")


if __name__ == "__main__":
    for fn in (ch_apply, ch_merge, status_text, point_xy, main):
        print(fn.__name__, fn())
