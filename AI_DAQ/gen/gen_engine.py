"""DAQ_Engine.vi: acquisition loop (queued message state machine) using NAMED queues."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
MSG0 = "[0," + SETTINGS0 + ",[]]"
LIVE0 = "[[],[],0.001,false,false,,]"
d = Doc()


def obtain(p, dep, name, typ, lit, size, err):
    o = d.node(p, dep, "Obtain Queue", [("name (unnamed)", d.const(p, dep, "string", name)),
                                        ("element data type", d.const(p, dep, typ, lit)),
                                        ("max queue size (-1\\2C unlimited)", d.i32(p, dep, size)),
                                        ("error in (no error)", err)], ["queue out", "created new?", "error out"])
    return o["queue out"], o["error out"]


def lossy(p, dep, q, el):
    d.node(p, dep, "Lossy Enqueue Element", [("queue", q), ("element", el), ("error in (no error)", d.noerr(p, dep))],
           ["queue out", "overflow element", "overflow?", "error out"])


def err_text(p, dep, err):
    code, src = d.unb(p, dep, err, ["code", "source"])
    cs = d.node(p, dep, "Number To Decimal String", [("number", code)], ["decimal integer string"])["decimal integer string"]
    return d.node(p, dep, "Concatenate Strings", [("string", d.const(p, dep, "string", esc("오류 "))), ("string", cs),
                                                  ("string", d.const(p, dep, "string", " \\3A ")), ("string", src)],
                  ["concatenated string"])["concatenated string"]


def create_task(p, dep, chans, rate, n, err):
    ch = d.call(p, dep, "DAQmx Create Virtual Channel.vi",
                [("physical channels", chans), ("minimum value", d.dbl(p, dep, 0)),
                 ("maximum value", d.dbl(p, dep, 0.02)), ("error in", err)],
                ["task out", "error out"], instance="DAQmx Create Channel (AI-Current-Basic).vi")
    tm = d.call(p, dep, "DAQmx Timing.vi",
                [("task/channels in", ch["task out"]), ("sample mode", d.const(p, dep, "int32", "10123")),
                 ("samples per channel", d.mul(p, dep, n, d.i32(p, dep, 10))), ("rate", rate),
                 ("error in", ch["error out"])],
                ["task out", "error out"], instance="DAQmx Timing (Sample Clock).vi")
    st = d.call(p, dep, "DAQmx Start Task.vi", [("task/channels in", tm["task out"]), ("error in", tm["error out"])],
                ["task out", "error out"])
    return st["task out"], st["error out"]


def body(fu, dep, ins):
    err0 = ins[0]
    d.label(fu, dep, "이름 있는 큐: 명령 / 실시간 데이터 / 그래프 팝업 데이터")
    cq, e1 = obtain(fu, dep, "AIDAQ_CMD", DAQ_MSG, MSG0, -1, err0)
    lq, e2 = obtain(fu, dep, "AIDAQ_LIVE", LIVE, LIVE0, 1, e1)
    gq, e3 = obtain(fu, dep, "AIDAQ_GRAPH", LIVE, LIVE0, 1, e2)

    def outer(lu, ld, i, L, it):
        cq_, lq_, gq_ = i
        chs, err = L
        dq = d.node(lu, ld, "Dequeue Element", [("queue", cq_), ("error in (no error)", err)],
                    ["queue out", "element", "timed out?", "error out"])
        cmd, sets, mchs = d.unb(lu, ld, dq["element"], ["Cmd", "Settings", "Channels"])
        d.label(lu, ld, "대기 상태: 명령이 올 때까지 기다림")

        def start(f, fp, j):
            c, e, s, q1, q2, q3 = j[3], j[1], j[2], j[4], j[5], j[6]
            rate, n, c1, c2, folder = d.unb(f, fp, s, ["Sample Rate (Hz)", "Samples per Channel", "Chassis 1 Channels",
                                                      "Chassis 2 Channels", "Save Folder"])
            d.label(f, fp, "측정 시작: 섀시 2대 태스크 생성 (64ch + 64ch)")
            t1, ea = create_task(f, fp, c1, rate, n, e)
            t2, eb = create_task(f, fp, c2, rate, n, ea)
            dt = d.div(f, fp, d.dbl(f, fp, 1), rate)

            def acq(au, ad, k, A, it2):
                t1_, t2_, n_, dt_, cq2, lq2, gq2, fol = k
                chs2, logging, lpath, e2_ = A
                cm = d.node(au, ad, "Dequeue Element", [("queue", cq2), ("timeout in ms (-1)", d.i32(au, ad, 0)),
                                                        ("error in (no error)", d.noerr(au, ad))],
                            ["queue out", "element", "timed out?", "error out"])
                d.label(au, ad, "측정 중 명령 확인 (대기 0 ms)")

                def none(h, hd, q):
                    return [q[0], q[1], q[2], d.b(h, hd, False), d.b(h, hd, False)]

                def handle(h, hd, q):
                    ch_, lg, lp, el, fo = q
                    c3, m3 = d.unb(h, hd, el, ["Cmd", "Channels"])
                    F, T = (lambda a, b: d.b(a, b, False)), (lambda a, b: d.b(a, b, True))

                    def lon(x, xd, w):
                        pth = d.call(x, xd, "TDMS_Make_Path.vi", [("Save Folder", w[4]), ("error in", d.noerr(x, xd))],
                                     ["File Path", "error out"])["File Path"]
                        return [w[0], T(x, xd), pth, F(x, xd), F(x, xd)]
                    return d.case(h, hd, c3, [ch_, lg, lp, m3, fo], 5, [
                        ('"Start"', "이미 측정 중", lambda x, xd, w: [w[0], w[1], w[2], F(x, xd), F(x, xd)]),
                        ('"Stop"', "측정 정지", lambda x, xd, w: [w[0], w[1], w[2], T(x, xd), F(x, xd)]),
                        ('"Config"', "채널 설정 갱신", lambda x, xd, w: [w[3], w[1], w[2], F(x, xd), F(x, xd)]),
                        ('"Log On"', "저장 시작: 새 파일", lon),
                        ('"Log Off"', "저장 끝", lambda x, xd, w: [w[0], F(x, xd), w[2], F(x, xd), F(x, xd)]),
                        ('"Exit"', "종료", lambda x, xd, w: [w[0], w[1], w[2], T(x, xd), T(x, xd)]),
                    ])
                h = d.case(au, ad, cm["timed out?"], [chs2, logging, lpath, cm["element"], fol], 5,
                           [("True", "명령 없음", none), ("False", "명령 처리", handle)])
                chs3, log3, path3, stopreq, exitreq = h
                r1 = d.call(au, ad, "DAQmx Read.vi", [("task/channels in", t1_), ("number of samples per channel", n_),
                                                      ("error in", e2_)],
                            ["task out", "data", "error out"], instance="DAQmx Read (Analog 2D DBL NChan NSamp).vi")
                r2 = d.call(au, ad, "DAQmx Read.vi", [("task/channels in", t2_), ("number of samples per channel", n_),
                                                      ("error in", r1["error out"])],
                            ["task out", "data", "error out"], instance="DAQmx Read (Analog 2D DBL NChan NSamp).vi")
                raw = d.node(au, ad, "Build Array", [("array", r1["data"]), ("array", r2["data"])], ["appended array"],
                             concat="true")["appended array"]
                d.label(au, ad, "읽기 -> 환산 -> (저장) -> 화면 큐")
                sc = d.call(au, ad, "DAQ_Scale.vi", [("Raw Data (A)", raw), ("Channels", chs3), ("error in", r2["error out"])],
                            ["Scaled Data", "Values", "error out"])

                def wr(x, xd, w):
                    o = d.call(x, xd, "TDMS_Write_Log.vi", [("File Path", w[0]), ("Scaled Data", w[1]), ("Channels", w[2]),
                                                            ("error in", w[3])], ["error out"])
                    return [o["error out"]]
                e4 = d.case(au, ad, log3, [path3, sc["Scaled Data"], chs3, sc["error out"]], 1,
                            [("True", "TDMS 저장", wr), ("False", "저장 안 함", lambda x, xd, w: [w[3]])])[0]
                live = d.bnd(au, ad, d.const(au, ad, LIVE, LIVE0),
                             [("Data", sc["Scaled Data"]), ("Values", sc["Values"]), ("dt", dt_), ("Running", d.b(au, ad, True)),
                              ("Logging", log3), ("Log File", path3)])
                lossy(au, ad, lq2, live)
                lossy(au, ad, gq2, live)
                bad = d.unb(au, ad, e4, ["status"])[0]
                stop = d.or_(au, ad, stopreq, bad)
                return [(exitreq, None)], [chs3, log3, path3, e4], stop
            ao, af = d.loop("While Loop", f, fp, [(t1, None), (t2, None), (n, None), (dt, None), (q1, None), (q2, None),
                                                   (q3, None), (folder, None)],
                            [c, d.b(f, fp, False), d.const(f, fp, "path", ""), eb], acq, label="측정 루프")
            d.label(f, fp, "측정 끝: 태스크 해제, 상태/오류 알림")
            c1e = d.call(f, fp, "DAQmx Clear Task.vi", [("task in", t1), ("error in", af[3])], ["error out"])
            c2e = d.call(f, fp, "DAQmx Clear Task.vi", [("task in", t2), ("error in", c1e["error out"])], ["error out"])
            st = d.unb(f, fp, c2e["error out"], ["status"])[0]
            msg = d.sel(f, fp, st, err_text(f, fp, c2e["error out"]), d.const(f, fp, "string", esc("측정 정지됨")))
            fin = d.bnd(f, fp, d.const(f, fp, LIVE, LIVE0), [("Message", msg)])
            lossy(f, fp, q2, fin)
            lossy(f, fp, q3, fin)
            return [af[0], ao[0], d.noerr(f, fp)]
        F, T = (lambda a, b: d.b(a, b, False)), (lambda a, b: d.b(a, b, True))
        o = d.case(lu, ld, cmd, [chs, dq["error out"], sets, mchs, cq_, lq_, gq_], 3, [
            ('"Start"', "측정 시작 ~ 정지", start),
            ('"Stop"', "대기 중: 무시", lambda f, fp, j: [j[0], F(f, fp), j[1]]),
            ('"Config"', "채널 설정 저장", lambda f, fp, j: [j[3], F(f, fp), j[1]]),
            ('"Log On"', "대기 중: 무시", lambda f, fp, j: [j[0], F(f, fp), j[1]]),
            ('"Log Off"', "대기 중: 무시", lambda f, fp, j: [j[0], F(f, fp), j[1]]),
            ('"Exit"', "엔진 종료", lambda f, fp, j: [j[0], T(f, fp), j[1]]),
        ])
        nch, ex, ne = o
        stop = d.or_(lu, ld, ex, d.unb(lu, ld, ne, ["status"])[0])
        return [], [nch, ne], stop
    _, fin = d.loop("While Loop", fu, dep, [(cq, None), (lq, None), (gq, None)], [d.const(fu, dep, CHANNELS, "[]"), e3],
                    outer, label="DAQ 엔진 (명령 대기)")
    r1 = d.node(fu, dep, "Release Queue", [("queue", cq), ("error in (no error)", fin[1])],
                ["queue name", "remaining elements", "error out"])
    r2 = d.node(fu, dep, "Release Queue", [("queue", lq), ("error in (no error)", r1["error out"])],
                ["queue name", "remaining elements", "error out"])
    r3 = d.node(fu, dep, "Release Queue", [("queue", gq), ("error in (no error)", r2["error out"])],
                ["queue name", "remaining elements", "error out"])
    return [r3["error out"]]


subvi(d, [], [], body, err_through=True)
print(d.write(f"{OUT}/DAQ_Engine.xml", "DAQ_Engine.vi",
              "DAQ 엔진: 이름 있는 큐 AIDAQ_CMD 로 명령(Start/Stop/Config/Log On/Log Off/Exit)을 받아 128채널 측정.\\0A"
              "측정 데이터는 AIDAQ_LIVE(메인 화면), AIDAQ_GRAPH(그래프 팝업) 큐(크기 1, 최신값)로 보낸다. Exit 명령에 끝난다."))
