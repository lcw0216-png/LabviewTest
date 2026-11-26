#!/usr/bin/env python3
"""Generate AIXML for 'DO seq.vi' - sequence-table driven 64-ch DO boolean output with a time counter."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from aixml_doc import Doc, quoteattr

d = Doc(start=5000)


def kr(t):
    """Korean LabVIEW stores text as CP949: hand the composer CP949 bytes, one char per byte."""
    return t.encode("cp949").decode("latin-1")


def esc(t):
    t = kr(t)
    return t.replace(",", "\\2C").replace(":", "\\3A")


def label(parent, depth, text):
    text = esc(text)
    d.el("FreeLabel", {"comment": text, "uid": d.uid(), "uid_parent": parent}, depth)


DESC = ("시퀀스 테이블 기반 DO 출력 시험 VI.\\0A"
        "[시험 시작] 시퀀스 테이블 1열의 채널 이름을 Channel Names 배열에서 검색해 인덱스를 구하고(0부터 시작, DO01=1), "
        "2열 On Time / 3열 Off Time(초)을 숫자로 변환한다. DO Output을 모두 OFF로, Time을 0으로 초기화하고 카운트를 시작한다.\\0A"
        "[실행 중] 50 ms마다 경과 시간 Time(s)을 갱신하고, 각 행의 채널을 On Time <= Time < Off Time 동안 ON, 그 밖에는 OFF로 출력한다.\\0A"
        "[자동 정지] Time이 시퀀스 테이블의 가장 큰 Off Time에 도달하면(>=) 시험을 정지한다.\\0A"
        "[시험 정지] 버튼을 누르면 중간에 정지한다(출력 상태는 유지). 다시 시작하면 출력과 시간이 초기화된다.\\0A"
        "창을 닫으면 VI가 종료된다. 같은 채널이 여러 행에 있으면 아래쪽 행의 판정이 우선한다.")

ROOT = "root"
names_default = "[" + ",".join(f"DO{i:02d}" for i in range(64)) + "]"
bool_default = "[" + ",".join(["false"] * 64) + "]"

# --- front panel terminals at root (read where they are used: inside event frames) ---
label(ROOT, 1, "DO 시퀀스 시험: 시작/정지/50 ms 타이머/종료")

# seeds for the shift registers (outside the loop)
s_run = d.const(ROOT, 1, "bool", "false")
s_t0 = d.const(ROOT, 1, "uint32", "0")
s_idx = d.const(ROOT, 1, "array{int32}", "[]")
s_on = d.const(ROOT, 1, "array{double}", "[]")
s_off = d.const(ROOT, 1, "array{double}", "[]")
s_max = d.const(ROOT, 1, "double", "0")
s_out = d.const(ROOT, 1, "array{bool}", bool_default)
s_time = d.const(ROOT, 1, "double", "0")

loop = d.uid()
SR = ["run", "t0", "idx", "on", "off", "max", "out", "time"]
seeds = dict(zip(SR, [s_run, s_t0, s_idx, s_on, s_off, s_max, s_out, s_time]))


def loop_body():
    ld = 2
    left_uid = {k: d.uid() for k in SR}
    left = {k: f"{left_uid[k]}.value" for k in SR}
    label(loop, ld, "Shift Register: 시험 상태/설정/출력/시간 유지")
    c50 = d.const(loop, ld, "int32", "50")
    cm1 = d.const(loop, ld, "int32", "-1")
    tmo = d.node(loop, ld, "Select", [("t", c50), ("s", left["run"]), ("f", cm1)], ["s? t\\3Af"])
    label(loop, ld, "실행 중 50 ms Timeout, 대기 중 무한 대기")

    # Event In: 1 run 2 t0 3 idx 4 on 5 off 6 max 7 out 8 time ; Out: same 8 + 9 quit
    def ev_start(fu, dep, i):
        d.el("Control", {"_name": "Start", "outputs": "value:", "style": "latched", "type": "bool",
                         "uid": d.uid(), "uid_parent": fu, "value": "false"}, dep)
        u = d.uid()
        d.el("Control", {"_name": "Channel Names", "conIdx": "0", "connection": "required",
                         "outputs": f"value:{u}.value", "type": "array{string}", "uid": u,
                         "uid_parent": fu, "value": names_default}, dep)
        names = f"{u}.value"
        u = d.uid()
        d.el("Control", {"_name": "Sequence Table", "conIdx": "5", "connection": "recommended",
                         "outputs": f"value:{u}.value", "type": "array.2{string}", "uid": u,
                         "uid_parent": fu, "value": "[[DO01,1,5],[DO63,3,8]]"}, dep)
        table = f"{u}.value"
        label(fu, dep, "테이블 행: 1열 채널->인덱스, 2열 On, 3열 Off")
        lp = d.uid()
        lo = {}

        def lbody():
            l2 = dep + 1
            tu = d.uid()
            d.el("Tunnel", {"_id": "In1", "inputs": f"value:{table}", "mode": "index",
                            "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp}, l2)
            row = f"{tu}.value"
            tu = d.uid()
            d.el("Tunnel", {"_id": "In2", "inputs": f"value:{names}",
                            "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp}, l2)
            nm = f"{tu}.value"
            c0 = d.const(lp, l2, "int32", "0")
            c1 = d.const(lp, l2, "int32", "1")
            c2 = d.const(lp, l2, "int32", "2")
            e0 = d.node(lp, l2, "Index Array", [("array", row), ("index", c0)], ["element"])
            e1 = d.node(lp, l2, "Index Array", [("array", row), ("index", c1)], ["element"])
            e2 = d.node(lp, l2, "Index Array", [("array", row), ("index", c2)], ["element"])
            sr = d.node(lp, l2, "Search 1D Array", [("1D array", nm), ("element", e0["element"]),
                                                     ("start index (0)", "")], ["index of element"])
            on = d.node(lp, l2, "Fract/Exp String To Number", [("string", e1["element"])],
                        ["offset past number", "number"])
            off = d.node(lp, l2, "Fract/Exp String To Number", [("string", e2["element"])],
                         ["offset past number", "number"])
            label(lp, l2, "채널 검색(없으면 -1), On/Off 문자->숫자")
            for k, net in enumerate([sr["index of element"], on["number"], off["number"]], 1):
                tu = d.uid()
                d.el("Tunnel", {"_id": f"Out{k}", "inputs": f"value:{net}", "mode": "index",
                                "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp}, l2)
                lo[k] = f"{tu}.value"
        d.el("Structure", {"_name": "For Loop", "count": "", "maxin": "", "maxout": "", "uid": lp,
                           "uid_parent": fu}, dep, lbody)
        mm = d.node(fu, dep, "Array Max & Min", [("array", lo[3])],
                    ["max value", "max index (indices)", "min value", "min index (indices)"])
        sz = d.node(fu, dep, "Array Size", [("array", names)], ["size(s)"])
        cf = d.const(fu, dep, "bool", "false")
        ini = d.node(fu, dep, "Initialize Array", [("element", cf), ("dimension size", sz["size(s)"])],
                     ["initialized array"])
        tk = d.node(fu, dep, "Tick Count (ms)", [], ["millisecond timer value"])
        ct = d.const(fu, dep, "bool", "true")
        cz = d.const(fu, dep, "double", "0")
        cq = d.const(fu, dep, "bool", "false")
        label(fu, dep, "초기화: 출력 OFF, Time=0, 시작 Tick 기록")
        return [ct, tk["millisecond timer value"], lo[1], lo[2], lo[3], mm["max value"],
                ini["initialized array"], cz, cq]

    def ev_stop(fu, dep, i):
        d.el("Control", {"_name": "Stop", "outputs": "value:", "style": "latched", "type": "bool",
                         "uid": d.uid(), "uid_parent": fu, "value": "false"}, dep)
        cf = d.const(fu, dep, "bool", "false")
        cq = d.const(fu, dep, "bool", "false")
        label(fu, dep, "중간 정지: 실행 상태 OFF (출력 유지)")
        return [cf, i[1], i[2], i[3], i[4], i[5], i[6], i[7], cq]

    def ev_timeout(fu, dep, i):
        def running(fu2, dep2, j):
            # j: 0 t0, 1 idx, 2 on, 3 off, 4 max, 5 out
            tk = d.node(fu2, dep2, "Tick Count (ms)", [], ["millisecond timer value"])
            sub = d.node(fu2, dep2, "Subtract", [("x", tk["millisecond timer value"]), ("y", j[0])], ["x-y"])
            dbl = d.node(fu2, dep2, "To Double Precision Float", [("number", sub["x-y"])],
                         ["double precision float"])
            k1000 = d.const(fu2, dep2, "double", "1000")
            t = d.node(fu2, dep2, "Divide", [("x", dbl["double precision float"]), ("y", k1000)], ["x/y"])
            tnet = t["x/y"]
            label(fu2, dep2, "경과 시간(s) = (현재 Tick - 시작 Tick) / 1000")
            lp = d.uid()
            res = {}

            def lbody():
                l3 = dep2 + 1
                tin = []
                for k, (net, mode_) in enumerate([(j[1], "index"), (j[2], "index"), (j[3], "index"),
                                                   (tnet, None)], 1):
                    tu = d.uid()
                    at = {"_id": f"In{k}", "inputs": f"value:{net}"}
                    if mode_:
                        at["mode"] = mode_
                    at.update({"outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp})
                    d.el("Tunnel", at, l3)
                    tin.append(f"{tu}.value")
                ix, on, off, tt = tin
                su = d.uid()
                lu, ru = d.uid(), d.uid()
                ge = d.node(lp, l3, "Greater Or Equal?", [("x", tt), ("y", on)], ["x >= y?"])
                lt = d.node(lp, l3, "Less?", [("x", tt), ("y", off)], ["x < y?"])
                an = d.node(lp, l3, "And", [("x", ge["x >= y?"]), ("y", lt["x < y?"])], ["x .and. y?"])
                rp = d.node(lp, l3, "Replace Array Subset",
                            [("array", f"{lu}.value"), ("index", ix), ("new element/subarray", an["x .and. y?"])],
                            ["output array"])
                label(lp, l3, "On <= Time < Off 이면 ON (인덱스 -1 무시)")

                def srb():
                    d.el("Left", {"inputs": f"value:{j[5]}", "outputs": f"value:{lu}.value", "uid": lu,
                                  "uid_parent": su}, l3 + 1)
                    d.el("Right", {"inputs": f"value:{rp['output array']}", "outputs": f"value:{ru}.value",
                                   "uid": ru, "uid_parent": su}, l3 + 1)
                d.el("ShiftReg", {"uid": su, "uid_parent": lp}, l3, srb)
                res["out"] = f"{ru}.value"
            d.el("Structure", {"_name": "For Loop", "count": "", "maxin": "", "maxout": "", "uid": lp,
                               "uid_parent": fu2}, dep2, lbody)
            done = d.node(fu2, dep2, "Greater Or Equal?", [("x", tnet), ("y", j[4])], ["x >= y?"])
            nr = d.node(fu2, dep2, "Not", [("x", done["x >= y?"])], [".not. x?"])
            label(fu2, dep2, "Time >= 최대 Off Time 이면 시험 자동 정지")
            return [nr[".not. x?"], res["out"], tnet]

        def idle(fu2, dep2, j):
            cf = d.const(fu2, dep2, "bool", "false")
            return [cf, j[5], j[6]]

        o = d.struct(fu, dep, "Case Structure", [i[1], i[2], i[3], i[4], i[5], i[6], i[7]], 3,
                     [({"selector": "True", "label": esc("실행 중: 시간 갱신 및 채널 On/Off")}, running),
                      ({"selector": "False", "label": kr("대기")}, idle)],
                     selectin=i[0])
        cq = d.const(fu, dep, "bool", "false")
        return [o[0], i[1], i[2], i[3], i[4], i[5], o[1], o[2], cq]

    def ev_close(fu, dep, i):
        ct = d.const(fu, dep, "bool", "true")
        label(fu, dep, "창 닫기: 루프 종료")
        return [i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], ct]

    ev = d.struct(loop, ld, "Event Structure", [left[k] for k in SR], 9,
                  [({"selector": ' "Start"\\3A Value Change '}, ev_start),
                   ({"selector": ' "Stop"\\3A Value Change '}, ev_stop),
                   ({"selector": " Timeout "}, ev_timeout),
                   ({"selector": " Panel Close? "}, ev_close)],
                  timeoutin=tmo["s? t\\3Af"])
    d.el("Indicator", {"_name": "DO Output", "conIdx": "4", "connection": "recommended",
                       "inputs": f"value:{ev[6]}", "type": "array{bool}", "uid": d.uid(),
                       "uid_parent": loop, "value": bool_default}, ld)
    d.el("Indicator", {"_name": "Time (s)", "conIdx": "6", "connection": "recommended",
                       "inputs": f"value:{ev[7]}", "type": "double", "uid": d.uid(),
                       "uid_parent": loop, "value": "0"}, ld)
    d.el("Condition", {"inputs": f"value:{ev[8]}", "uid": d.uid(), "uid_parent": loop, "value": "stop"}, ld)
    for n, k in enumerate(SR):
        su = d.uid()

        def srb(su=su, k=k, n=n):
            d.el("Left", {"inputs": f"value:{seeds[k]}", "outputs": f"value:{left[k]}", "uid": left_uid[k],
                          "uid_parent": su}, ld + 1)
            d.el("Right", {"inputs": f"value:{ev[n]}", "outputs": "value:", "uid": d.uid(),
                           "uid_parent": su}, ld + 1)
        d.el("ShiftReg", {"uid": su, "uid_parent": loop}, ld, srb)


d.el("Structure", {"_name": "While Loop", "count": "", "uid": loop, "uid_parent": ROOT}, 1, loop_body)

xml = f'<VI _name="DO seq.vi" description={quoteattr(kr(DESC))}>\n' + "\n".join(d.out) + "\n</VI>\n"
open(sys.argv[1], "w", encoding="utf-8").write(xml)
print("written", len(xml), "last uid", d.n)
