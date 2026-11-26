#!/usr/bin/env python3
"""Generate AIXML for 'DO seq.vi' as a STATE MACHINE (While Loop + enum shift register + Case Structure)."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from aixml_doc import Doc, quoteattr

d = Doc(start=5000)


def kr(t):
    """Korean LabVIEW stores text as CP949: hand the composer CP949 bytes, one char per byte."""
    return t.encode("cp949").decode("latin-1")


def esc(t):
    return kr(t).replace(",", "\\2C").replace(":", "\\3A")


def label(parent, depth, text):
    d.el("FreeLabel", {"comment": esc(text), "uid": d.uid(), "uid_parent": parent}, depth)


STATE_T = "uint16{Idle,Init,Run,Exit}"
IDLE, INIT, RUN, EXIT = "0", "1", "2", "3"


def st(parent, depth, idx):
    return d.const(parent, depth, STATE_T, idx)


def sel(parent, depth, s, t, f):
    return d.node(parent, depth, "Select", [("t", t), ("s", s), ("f", f)], ["s? t\\3Af"])["s? t\\3Af"]


DESC = ("시퀀스 테이블 기반 DO 출력 시험 VI (상태머신 구조: Idle / Init / Run / Exit).\\0A"
        "[Idle] 대기. 시험 시작 -> Init\\2C 종료 -> Exit.\\0A"
        "[Init] 시퀀스 테이블 1열의 채널 이름을 Channel Names 배열에서 검색해 인덱스를 구하고(0부터 시작\\2C DO01=1)\\2C "
        "2열 On Time / 3열 Off Time(초)을 숫자로 변환. DO Output 전부 OFF\\2C Time=0\\2C 시작 시각 기록 -> Run.\\0A"
        "[Run] 50 ms마다 경과 시간 갱신\\2C 각 행 채널을 On Time <= Time < Off Time 동안 ON. "
        "Time이 가장 큰 Off Time에 도달(>=)하거나 시험 정지를 누르면 -> Idle (출력 유지)\\2C 시험 시작을 다시 누르면 -> Init(초기화 후 재시작).\\0A"
        "[Exit] 루프 종료.\\0A"
        "같은 채널이 여러 행에 있으면 아래쪽 행의 판정이 우선한다. 테이블에 없는 채널 이름은 무시된다.")

ROOT = "root"
names_default = "[" + ",".join(f"DO{i:02d}" for i in range(64)) + "]"
bool_default = "[" + ",".join(["false"] * 64) + "]"

label(ROOT, 1, "DO 시퀀스 시험: 상태머신 Idle/Init/Run/Exit")


# shift register seeds (outside the loop)
SR = ["state", "t0", "idx", "on", "off", "max", "out", "time"]
seeds = dict(zip(SR, [st(ROOT, 1, IDLE), d.const(ROOT, 1, "uint32", "0"),
                      d.const(ROOT, 1, "array{int32}", "[]"), d.const(ROOT, 1, "array{double}", "[]"),
                      d.const(ROOT, 1, "array{double}", "[]"), d.const(ROOT, 1, "double", "0"),
                      d.const(ROOT, 1, "array{bool}", bool_default), d.const(ROOT, 1, "double", "0")]))
loop = d.uid()


def loop_body():
    ld = 2
    left_uid = {k: d.uid() for k in SR}
    left = {k: f"{left_uid[k]}.value" for k in SR}

    def btn(name):
        u = d.uid()
        d.el("Control", {"_name": name, "outputs": f"value:{u}.value", "style": "latched", "type": "bool",
                         "uid": u, "uid_parent": loop, "value": "false"}, ld)
        return f"{u}.value"
    u = d.uid()
    d.el("Control", {"_name": "Channel Names", "conIdx": "0", "connection": "required",
                     "outputs": f"value:{u}.value", "type": "array{string}", "uid": u,
                     "uid_parent": loop, "value": names_default}, ld)
    names = f"{u}.value"
    b_start = btn("Start")
    b_stop = btn("Stop")
    b_exit = btn("Exit")
    u = d.uid()
    d.el("Control", {"_name": "Sequence Table", "conIdx": "5", "connection": "recommended",
                     "outputs": f"value:{u}.value", "type": "array.2{string}", "uid": u,
                     "uid_parent": loop, "value": "[[DO01,1,5],[DO63,3,8]]"}, ld)
    table = f"{u}.value"
    label(loop, ld, "버튼은 매 반복 읽음 (래치 동작)")
    w50 = d.const(loop, ld, "uint32", "50")
    d.node(loop, ld, "Wait (ms)", [("milliseconds to wait", w50)], ["millisecond timer value"])
    label(loop, ld, "루프 주기 50 ms")

    # Case In: 1 state(unused) 2 t0 3 idx 4 on 5 off 6 max 7 out 8 time 9 start 10 stop 11 exit 12 table 13 names
    # Case Out: 1 next 2 t0 3 idx 4 on 5 off 6 max 7 out 8 time 9 quit
    def common_next(fu, dep, i, default):
        """exit -> Exit, else start -> Init, else default"""
        s2 = sel(fu, dep, i[8], st(fu, dep, INIT), default)
        return sel(fu, dep, i[10], st(fu, dep, EXIT), s2)

    def f_idle(fu, dep, i):
        nxt = common_next(fu, dep, i, st(fu, dep, IDLE))
        label(fu, dep, "대기: 시작 -> Init / 종료 -> Exit")
        q = d.const(fu, dep, "bool", "false")
        return [nxt, i[1], i[2], i[3], i[4], i[5], i[6], i[7], q]

    def f_init(fu, dep, i):
        label(fu, dep, "테이블 행: 1열 채널->인덱스, 2열 On, 3열 Off")
        lp = d.uid()
        lo = {}

        def lbody():
            l2 = dep + 1
            tu = d.uid()
            d.el("Tunnel", {"_id": "In1", "inputs": f"value:{i[11]}", "mode": "index",
                            "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp}, l2)
            row = f"{tu}.value"
            tu = d.uid()
            d.el("Tunnel", {"_id": "In2", "inputs": f"value:{i[12]}",
                            "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp}, l2)
            nm = f"{tu}.value"
            el = [d.node(lp, l2, "Index Array", [("array", row), ("index", d.const(lp, l2, "int32", str(c)))],
                         ["element"])["element"] for c in range(3)]
            sr = d.node(lp, l2, "Search 1D Array", [("1D array", nm), ("element", el[0]), ("start index (0)", "")],
                        ["index of element"])
            on = d.node(lp, l2, "Fract/Exp String To Number", [("string", el[1])], ["offset past number", "number"])
            off = d.node(lp, l2, "Fract/Exp String To Number", [("string", el[2])], ["offset past number", "number"])
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
        sz = d.node(fu, dep, "Array Size", [("array", i[12])], ["size(s)"])
        ini = d.node(fu, dep, "Initialize Array", [("element", d.const(fu, dep, "bool", "false")),
                                                   ("dimension size", sz["size(s)"])], ["initialized array"])
        tk = d.node(fu, dep, "Tick Count (ms)", [], ["millisecond timer value"])
        label(fu, dep, "초기화: 출력 OFF, Time=0, 시작 Tick -> Run")
        nxt = sel(fu, dep, i[10], st(fu, dep, EXIT), st(fu, dep, RUN))
        q = d.const(fu, dep, "bool", "false")
        return [nxt, tk["millisecond timer value"], lo[1], lo[2], lo[3], mm["max value"],
                ini["initialized array"], d.const(fu, dep, "double", "0"), q]

    def f_run(fu, dep, i):
        tk = d.node(fu, dep, "Tick Count (ms)", [], ["millisecond timer value"])
        sub = d.node(fu, dep, "Subtract", [("x", tk["millisecond timer value"]), ("y", i[1])], ["x-y"])
        dbl = d.node(fu, dep, "To Double Precision Float", [("number", sub["x-y"])], ["double precision float"])
        t = d.node(fu, dep, "Divide", [("x", dbl["double precision float"]),
                                       ("y", d.const(fu, dep, "double", "1000"))], ["x/y"])["x/y"]
        label(fu, dep, "경과 시간(s) = (현재 Tick - 시작 Tick) / 1000")
        lp = d.uid()
        res = {}

        def lbody():
            l3 = dep + 1
            tin = []
            for k, (net, mode_) in enumerate([(i[2], "index"), (i[3], "index"), (i[4], "index"), (t, None)], 1):
                tu = d.uid()
                at = {"_id": f"In{k}", "inputs": f"value:{net}"}
                if mode_:
                    at["mode"] = mode_
                at.update({"outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp})
                d.el("Tunnel", at, l3)
                tin.append(f"{tu}.value")
            ix, on, off, tt = tin
            su, lu, ru = d.uid(), d.uid(), d.uid()
            ge = d.node(lp, l3, "Greater Or Equal?", [("x", tt), ("y", on)], ["x >= y?"])
            lt = d.node(lp, l3, "Less?", [("x", tt), ("y", off)], ["x < y?"])
            an = d.node(lp, l3, "And", [("x", ge["x >= y?"]), ("y", lt["x < y?"])], ["x .and. y?"])
            rp = d.node(lp, l3, "Replace Array Subset",
                        [("array", f"{lu}.value"), ("index", ix), ("new element/subarray", an["x .and. y?"])],
                        ["output array"])
            label(lp, l3, "On <= Time < Off 이면 ON (인덱스 -1 무시)")

            def srb():
                d.el("Left", {"inputs": f"value:{i[6]}", "outputs": f"value:{lu}.value", "uid": lu,
                              "uid_parent": su}, l3 + 1)
                d.el("Right", {"inputs": f"value:{rp['output array']}", "outputs": f"value:{ru}.value",
                               "uid": ru, "uid_parent": su}, l3 + 1)
            d.el("ShiftReg", {"uid": su, "uid_parent": lp}, l3, srb)
            res["out"] = f"{ru}.value"
        d.el("Structure", {"_name": "For Loop", "count": "", "maxin": "", "maxout": "", "uid": lp,
                           "uid_parent": fu}, dep, lbody)
        done = d.node(fu, dep, "Greater Or Equal?", [("x", t), ("y", i[5])], ["x >= y?"])
        halt = d.node(fu, dep, "Or", [("x", done["x >= y?"]), ("y", i[9])], ["x .or. y?"])
        s1 = sel(fu, dep, halt["x .or. y?"], st(fu, dep, IDLE), st(fu, dep, RUN))
        nxt = common_next(fu, dep, i, s1)
        label(fu, dep, "최대 Off 도달 또는 정지 -> Idle, 시작 -> Init")
        q = d.const(fu, dep, "bool", "false")
        return [nxt, i[1], i[2], i[3], i[4], i[5], res["out"], t, q]

    def f_exit(fu, dep, i):
        label(fu, dep, "루프 종료")
        q = d.const(fu, dep, "bool", "true")
        return [st(fu, dep, EXIT), i[1], i[2], i[3], i[4], i[5], i[6], i[7], q]

    ins = [left[k] for k in SR] + [b_start, b_stop, b_exit, table, names]
    o = d.struct(loop, ld, "Case Structure", ins, 9,
                 [({"selector": '"Idle"', "label": kr("대기")}, f_idle),
                  ({"selector": '"Init"', "label": kr("초기화")}, f_init),
                  ({"selector": '"Run"', "label": kr("시험 실행")}, f_run),
                  ({"selector": '"Exit"', "label": kr("종료")}, f_exit)],
                 selectin=left["state"])
    d.el("Indicator", {"_name": "DO Output", "conIdx": "4", "connection": "recommended",
                       "inputs": f"value:{o[6]}", "type": "array{bool}", "uid": d.uid(),
                       "uid_parent": loop, "value": bool_default}, ld)
    d.el("Indicator", {"_name": "Time (s)", "conIdx": "6", "connection": "recommended",
                       "inputs": f"value:{o[7]}", "type": "double", "uid": d.uid(),
                       "uid_parent": loop, "value": "0"}, ld)
    d.el("Condition", {"inputs": f"value:{o[8]}", "uid": d.uid(), "uid_parent": loop, "value": "stop"}, ld)
    label(loop, ld, "Shift Register: 상태/설정/출력/시간 유지")
    for n, k in enumerate(SR):
        su = d.uid()

        def srb(su=su, k=k, n=n):
            d.el("Left", {"inputs": f"value:{seeds[k]}", "outputs": f"value:{left[k]}", "uid": left_uid[k],
                          "uid_parent": su}, ld + 1)
            d.el("Right", {"inputs": f"value:{o[n]}", "outputs": "value:", "uid": d.uid(),
                           "uid_parent": su}, ld + 1)
        d.el("ShiftReg", {"uid": su, "uid_parent": loop}, ld, srb)


d.el("Structure", {"_name": "While Loop", "count": "", "uid": loop, "uid_parent": ROOT}, 1, loop_body)

xml = f'<VI _name="DO seq.vi" description={quoteattr(kr(DESC))}>\n' + "\n".join(d.out) + "\n</VI>\n"
open(sys.argv[1], "w", encoding="utf-8").write(xml)
print("written", len(xml), "last uid", d.n)
