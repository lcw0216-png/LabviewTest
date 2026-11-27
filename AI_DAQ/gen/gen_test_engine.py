import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from gen_engine import MSG0, LIVE0
OUT = sys.argv[1]
d = Doc()
R = "root"
d.label(R, 1, "테스트: 엔진을 병렬 실행하고 명령 순서대로 전송")
eng = d.call(R, 1, "DAQ_Engine.vi", [("error in", d.noerr(R, 1))], ["error out"])
cq = d.node(R, 1, "Obtain Queue", [("name (unnamed)", d.const(R, 1, "string", "AIDAQ_CMD")),
                                    ("element data type", d.const(R, 1, DAQ_MSG, MSG0)), ("error in (no error)", d.noerr(R, 1))],
            ["queue out", "created new?", "error out"])
lq = d.node(R, 1, "Obtain Queue", [("name (unnamed)", d.const(R, 1, "string", "AIDAQ_LIVE")),
                                    ("element data type", d.const(R, 1, LIVE, LIVE0)),
                                    ("max queue size (-1\\2C unlimited)", d.i32(R, 1, 1)), ("error in (no error)", cq["error out"])],
            ["queue out", "created new?", "error out"])
chs = d.call(R, 1, "Ch_Defaults.vi", [("error in", lq["error out"])], ["Channels", "error out"])
msg = d.const(R, 1, DAQ_MSG, MSG0)
e = chs["error out"]
live = None
for cmd, wait in (("0", 1500), ("3", 1000), ("4", 300), ("1", 800), ("5", 0)):
    m = d.bnd(R, 1, msg, [("Cmd", d.const(R, 1, DAQ_CMD, cmd)), ("Channels", chs["Channels"])])
    q = d.node(R, 1, "Enqueue Element", [("queue", cq["queue out"]), ("element", m), ("error in (no error)", e)],
               ["queue out", "timed out?", "error out"])
    e = q["error out"]
    if cmd == "4":
        dq = d.node(R, 1, "Dequeue Element", [("queue", lq["queue out"]), ("timeout in ms (-1)", d.i32(R, 1, 2000)),
                                              ("error in (no error)", e)], ["queue out", "element", "timed out?", "error out"])
        e = dq["error out"]
        live = dq["element"]

    if wait:
        def w(f, fp, j, ms=wait):
            d.node(f, fp, "Wait (ms)", [("milliseconds to wait", d.i32(f, fp, ms))], ["millisecond timer value"])
            return [j[0]]
        e = d.case(R, 1, d.unb(R, 1, e, ["status"])[0], [e], 1, [("False", "대기", w), ("True", None, lambda f, fp, j: [j[0]])])[0]
dq2 = d.node(R, 1, "Dequeue Element", [("queue", lq["queue out"]), ("timeout in ms (-1)", d.i32(R, 1, 2000)),
                                       ("error in (no error)", e)], ["queue out", "element", "timed out?", "error out"])
data, vals, dt, run, lg, mess, lf = d.unb(R, 1, live, ["Data", "Values", "dt", "Running", "Logging", "Message", "Log File"])
d.ind(R, 1, "Values", "array{double}", "[]", vals)
d.ind(R, 1, "Rows", "int32", "0", d.idx1(R, 1, d.size(R, 1, data), d.i32(R, 1, 0)))
d.ind(R, 1, "dt", "double", "0", dt)
d.ind(R, 1, "Running", "bool", "false", run)
d.ind(R, 1, "Logging", "bool", "false", lg)
d.ind(R, 1, "Log File", "path", "", lf)
m2 = d.unb(R, 1, dq2["element"], ["Message"])[0]
d.ind(R, 1, "Final Message", "string", "", m2)
d.ind(R, 1, "Mid Message", "string", "", mess)
d.ind(R, 1, "error out", ERR_T, "[false,0,]", dq2["error out"])
d.ind(R, 1, "engine error", ERR_T, "[false,0,]", eng["error out"])
print(d.write(f"{OUT}/Test_Engine.xml", "Test_Engine.vi", "DAQ_Engine 테스트: Start, Log On, Log Off(이때 최신 데이터 확인), Stop, Exit."))
