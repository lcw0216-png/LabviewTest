#!/usr/bin/env python3
"""Generate AIXML for AI_Data_Tdms.vi (NI 9203 8ch current acquisition, scaling, TDMS save)."""
import sys
from xml.sax.saxutils import quoteattr

ERR_T = "cluster{bool.status,int32.code,string.source}"


class Doc:
    def __init__(self, start=5000):
        self.n = start
        self.out = []

    def uid(self):
        self.n += 10
        return str(self.n)

    def el(self, tag, attrs, depth, children=None):
        a = " ".join(f"{k}={quoteattr(v)}" for k, v in attrs.items())
        pad = "  " * depth
        if children is None:
            self.out.append(f"{pad}<{tag} {a}/>")
        else:
            self.out.append(f"{pad}<{tag} {a}>")
            children()
            self.out.append(f"{pad}</{tag}>")

    # --- leaf helpers ---------------------------------------------------
    def const(self, parent, depth, typ, value, name=None):
        u = self.uid()
        at = {}
        if name:
            at["_name"] = name
        at.update({"outputs": f"value:{u}.value", "type": typ, "uid": u,
                   "uid_parent": parent, "value": value})
        self.el("Constant", at, depth)
        return f"{u}.value"

    def node(self, parent, depth, name, inputs, outs, **extra):
        """inputs: list of (term, net); outs: list of term names. returns dict term->net"""
        u = self.uid()
        ins = ",".join(f"{t}:{n}" for t, n in inputs)
        onets = {t: f"{u}.{t}" for t in outs}
        os_ = ",".join(f"{t}:{onets[t]}" for t in outs)
        at = {"_name": name}
        at.update(extra)
        at.update({"inputs": ins, "outputs": os_, "uid": u, "uid_parent": parent})
        self.el("Node", at, depth)
        return onets

    def call(self, parent, depth, target, inputs, outs, instance=None):
        u = self.uid()
        ins = ",".join(f"{t}:{n}" for t, n in inputs)
        onets = {t: f"{u}.{t}" for t in outs}
        os_ = ",".join(f"{t}:{onets[t]}" for t in outs)
        at = {}
        if instance:
            at["adapt"] = "true"
            at["instance"] = instance
        at.update({"target": target, "inputs": ins, "outputs": os_, "uid": u,
                   "uid_parent": parent})
        self.el("Call", at, depth)
        return onets

    # --- case / event structure with tunnels -----------------------------
    def struct(self, parent, depth, name, in_nets, nouts, frames, **sattrs):
        """frames: list of (frame_attrs, fn(fu, fdepth, ins)->list_of_out_nets).
        returns list of outer out nets."""
        su = self.uid()
        outer_out = []

        def body():
            in_ids = []
            for i, net in enumerate(in_nets, 1):
                tu = self.uid()
                self.el("Tunnel", {"_id": f"In{i}", "inputs": f"value:{net}",
                                   "uid": tu, "uid_parent": su}, depth + 1)
                in_ids.append(i)
            for fattrs, fn in frames:
                fu = self.uid()

                def fbody(fu=fu, fn=fn):
                    ins = []
                    for i in in_ids:
                        tu = self.uid()
                        self.el("Tunnel", {"_id": f"In{i}", "outputs": f"value:{tu}.value",
                                           "uid": tu, "uid_parent": fu}, depth + 2)
                        ins.append(f"{tu}.value")
                    outs = fn(fu, depth + 2, ins)
                    assert len(outs) == nouts, (name, fattrs, len(outs), nouts)
                    for j, onet in enumerate(outs, 1):
                        tu = self.uid()
                        self.el("Tunnel", {"_id": f"Out{j}", "inputs": f"value:{onet}",
                                           "uid": tu, "uid_parent": fu}, depth + 2)
                at = dict(fattrs)
                at.setdefault("selectout", "")
                at.update({"uid": fu, "uid_parent": su})
                self.el("CaseFrame", at, depth + 1, fbody)
            for j in range(1, nouts + 1):
                tu = self.uid()
                self.el("Tunnel", {"_id": f"Out{j}", "outputs": f"value:{tu}.value",
                                   "uid": tu, "uid_parent": su}, depth + 1)
                outer_out.append(f"{tu}.value")

        at = {"_name": name}
        at.update(sattrs)
        at.update({"uid": su, "uid_parent": parent})
        self.el("Structure", at, depth, body)
        return outer_out


d = Doc()
D = d  # alias

DESC = ("NI 9203 (8ch, 4-20 mA) current acquisition with DAQmx, per-channel scaling and TDMS save.\\0A"
        "Start: creates the AI current task (0-20 mA range), sample clock timing (finite or continuous) and starts it.\\0A"
        "Timeout (while running): reads N samples/ch as 2D DBL [ch][sample] in A, scales each channel "
        "EU = min + (I[mA]-4)/16*(max-min) using row ch of Scale (Min/Max) [min,max], charts it and appends it to the buffer. "
        "Finite mode stops the task after one read.\\0A"
        "Stop: stops and clears the task.\\0A"
        "Save Data: opens a file dialog (name and folder) and writes the buffered scaled data of every channel to TDMS "
        "(group AI Data, channels CH0..CHn).\\0A"
        "Closing the panel ends the VI. Runs only when error in carries no error.")

lines_head = f'<VI _name="AI_Data_Tdms.vi" description={quoteattr(DESC)}>'

ROOT = "root"
# --- front panel terminals at root ------------------------------------------
err_in = "4013.value"
d.el("Control", {"_name": "error in", "conIdx": "11", "connection": "required",
                 "outputs": f"value:{err_in}", "type": ERR_T, "uid": "4013",
                 "uid_parent": ROOT, "value": "[false,0,]"}, 1)
err_out_uid = "4023"
st = d.node(ROOT, 1, "Unbundle By Name", [("input cluster", err_in)], ["status"], fields="status")


def frame_noerror(fu, dep, ins):
    err0 = ins[0]
    run_seed = d.const(fu, dep, "bool", "false")
    buf_seed = d.const(fu, dep, "array.2{double}", "[]")
    SEEDS = (d.const(fu, dep, "int32", "10123"), d.const(fu, dep, "double", "100"),
             d.const(fu, dep, "int32", "100"),
             d.const(fu, dep, "ref{GenClassTag.Task.NIDAQ}", ""))
    loop = d.uid()
    sr = {}
    final = {}

    def loop_body():
        ld = dep + 1
        # controls inside the loop (read every iteration)
        def ctl(name, typ, value, **extra):
            u = d.uid()
            at = {"_name": name}
            at.update(extra)
            at.update({"outputs": f"value:{u}.value", "type": typ, "uid": u,
                       "uid_parent": loop, "value": value})
            d.el("Control", at, ld)
            return f"{u}.value"
        def fctl(parent, dep_, name, typ, value, **extra):
            u = d.uid()
            at = {"_name": name}
            at.update(extra)
            at.update({"outputs": f"value:{u}.value", "type": typ, "uid": u,
                       "uid_parent": parent, "value": value})
            d.el("Control", at, dep_)
            return f"{u}.value"
        mode_seed, rate_seed, ns_seed, task_seed = SEEDS

        # shift registers: Left outputs are the per-iteration values
        names = ["task", "run", "buf", "err", "mode", "rate", "ns"]
        seeds = {"task": task_seed, "run": run_seed, "buf": buf_seed, "err": err0,
                 "mode": mode_seed, "rate": rate_seed, "ns": ns_seed}
        left = {}
        left_uid = {}
        for k in names:
            left_uid[k] = d.uid()
            left[k] = f"{left_uid[k]}.value"
        # timeout: 0 ms while running, -1 (wait forever) when idle
        c0 = d.const(loop, ld, "int32", "0")
        cm1 = d.const(loop, ld, "int32", "-1")
        sel = d.node(loop, ld, "Select", [("t", c0), ("s", left["run"]), ("f", cm1)], ["s? t\\3Af"])
        tmo = sel["s? t\\3Af"]

        # ---------------- event frames --------------------------------
        # In: 1 task, 2 run, 3 buf, 4 err, 5 chans, 6 mode, 7 rate, 8 nsamp, 9 scale
        # Out: 1 task, 2 run, 3 buf, 4 err, 5 stop
        def ev_start(fu, dep, i):
            d.el("Control", {"_name": "Start", "outputs": "value:", "style": "latched",
                             "type": "bool", "uid": d.uid(), "uid_parent": fu, "value": "false"}, dep)

            def already(fu2, dep2, j):  # running: ignore
                return [j[0], j[1], j[6]]

            def create(fu2, dep2, j):
                cmin = d.const(fu2, dep2, "double", "0")
                cmax = d.const(fu2, dep2, "double", "0.02")
                ch = d.call(fu2, dep2, "DAQmx Create Virtual Channel.vi",
                            [("task in", ""), ("physical channels", j[2]), ("minimum value", cmin),
                             ("maximum value", cmax), ("error in", j[1])],
                            ["task out", "error out"], instance="DAQmx Create Channel (AI-Current-Basic).vi")
                tm = d.call(fu2, dep2, "DAQmx Timing.vi",
                            [("task/channels in", ch["task out"]), ("sample mode", j[3]),
                             ("samples per channel", j[5]), ("rate", j[4]), ("error in", ch["error out"])],
                            ["task out", "error out"], instance="DAQmx Timing (Sample Clock).vi")
                sa = d.call(fu2, dep2, "DAQmx Start Task.vi",
                            [("task/channels in", tm["task out"]), ("error in", tm["error out"])],
                            ["task out", "error out"])
                empty = d.const(fu2, dep2, "array.2{double}", "[]")
                return [sa["task out"], sa["error out"], empty]

            chans = fctl(fu, dep, "Physical Channels", "tag{14}", "cDAQ1Mod1/ai0:7")
            mode = fctl(fu, dep, "Sample Mode", "int32", "10123", style="Ring",
                        items="Finite Samples,Continuous Samples", values="[10178,10123]")
            rate = fctl(fu, dep, "Sample Rate (Hz)", "double", "100")
            nsamp = fctl(fu, dep, "Samples per Channel", "int32", "100")
            o = d.struct(fu, dep, "Case Structure", [i[0], i[3], chans, mode, rate, nsamp, i[2]], 3,
                         [({"selector": "True", "label": "Already running"}, already),
                          ({"selector": "False", "label": "Create task and start"}, create)],
                         selectin=i[1])
            t = d.const(fu, dep, "bool", "true")
            f = d.const(fu, dep, "bool", "false")
            return [o[0], t, o[2], o[1], f, mode, rate, nsamp]

        def ev_stop(fu, dep, i):
            d.el("Control", {"_name": "Stop", "outputs": "value:", "style": "latched",
                             "type": "bool", "uid": d.uid(), "uid_parent": fu, "value": "false"}, dep)

            def running(fu2, dep2, j):
                sp = d.call(fu2, dep2, "DAQmx Stop Task.vi",
                            [("task/channels in", j[0]), ("error in", j[1])], ["task out", "error out"])
                cl = d.call(fu2, dep2, "DAQmx Clear Task.vi",
                            [("task in", sp["task out"]), ("error in", sp["error out"])], ["error out"])
                return [cl["error out"]]

            def idle(fu2, dep2, j):
                return [j[1]]

            o = d.struct(fu, dep, "Case Structure", [i[0], i[3]], 1,
                         [({"selector": "True", "label": "Stop and clear task"}, running),
                          ({"selector": "False", "label": "Not running"}, idle)],
                         selectin=i[1])
            f1 = d.const(fu, dep, "bool", "false")
            f2 = d.const(fu, dep, "bool", "false")
            return [i[0], f1, i[2], o[0], f2, i[4], i[5], i[6]]

        def ev_save(fu, dep, i):
            d.el("Control", {"_name": "Save Data", "outputs": "value:", "style": "latched",
                             "type": "bool", "uid": d.uid(), "uid_parent": fu, "value": "false"}, dep)
            prompt = d.const(fu, dep, "string", "Save TDMS file")
            dname = d.const(fu, dep, "string", "AI_Data.tdms")
            patt = d.const(fu, dep, "string", "*.tdms")
            fd = d.node(fu, dep, "File Dialog",
                        [("start path", ""), ("default name", dname), ("error in", i[3]),
                         ("prompt", prompt), ("pattern (all files)", patt)],
                        ["selected path", "exists", "cancelled", "error out"])

            def write(fu2, dep2, j):
                data = d.node(fu2, dep2, "Transpose 2D Array", [("2D array", j[2])], ["transposed array"])
                # channel names CH0..CHn, one per row of the [ch][sample] data
                lp = d.uid()
                names_out = {}

                def lbody():
                    pre = d.const(lp, dep2 + 1, "string", "CH")
                    num = d.node(lp, dep2 + 1, "Number To Decimal String", [("number", f"{lp}.value")],
                                 ["decimal integer string"])
                    cat = d.node(lp, dep2 + 1, "Concatenate Strings",
                                 [("string", pre), ("string", num["decimal integer string"])],
                                 ["concatenated string"])
                    d.el("Tunnel", {"_id": "In1", "inputs": f"value:{data['transposed array']}",
                                    "mode": "index", "outputs": "value:", "uid": d.uid(),
                                    "uid_parent": lp}, dep2 + 1)
                    tu = d.uid()
                    d.el("Tunnel", {"_id": "Out1", "inputs": f"value:{cat['concatenated string']}",
                                    "mode": "index", "outputs": f"value:{tu}.value", "uid": tu,
                                    "uid_parent": lp}, dep2 + 1)
                    names_out["n"] = f"{tu}.value"
                d.el("Structure", {"_name": "For Loop", "count": f"{lp}.value", "maxin": "", "maxout": "",
                                   "uid": lp, "uid_parent": fu2}, dep2, lbody)
                op = d.const(fu2, dep2, "uint16{open,open or create,create or replace,create,open (read-only)}", "2",
                             name="operation")
                grp = d.const(fu2, dep2, "string", "AI Data")
                to = d.node(fu2, dep2, "TDMS Open",
                            [("file path", j[0]), ("operation (0\\3Aopen)", op), ("error in (no error)", j[1])],
                            ["tdms file out", "error out"])
                tw = d.node(fu2, dep2, "TDMS Write",
                            [("tdms file", to["tdms file out"]), ("group name in (Untitled)", grp),
                             ("channel name(s) in (Untitled)", names_out["n"]), ("data", data["transposed array"]),
                             ("error in (no error)", to["error out"])],
                            ["tdms file out", "error out"])
                tc = d.node(fu2, dep2, "TDMS Close",
                            [("tdms file", tw["tdms file out"]), ("error in (no error)", tw["error out"])],
                            ["error out"])
                return [tc["error out"]]

            def cancelled(fu2, dep2, j):
                return [j[1]]

            o = d.struct(fu, dep, "Case Structure", [fd["selected path"], fd["error out"], i[2]], 1,
                         [({"selector": "False", "label": "Write buffer to TDMS"}, write),
                          ({"selector": "True", "label": "Dialog cancelled"}, cancelled)],
                         selectin=fd["cancelled"])
            f = d.const(fu, dep, "bool", "false")
            return [i[0], i[1], i[2], o[0], f, i[4], i[5], i[6]]

        def ev_timeout(fu, dep, i):
            def acquire(fu2, dep2, j):
                # j: 0 task, 1 err, 2 buf, 3 scale, 4 nsamp, 5 rate, 6 mode
                rd = d.call(fu2, dep2, "DAQmx Read.vi",
                            [("task/channels in", j[0]), ("number of samples per channel", j[4]),
                             ("timeout", ""), ("error in", j[1])],
                            ["task out", "data", "error out"], instance="DAQmx Read (Analog 2D DBL NChan NSamp).vi")
                one = d.const(fu2, dep2, "double", "1")
                dt = d.node(fu2, dep2, "Divide", [("x", one), ("y", j[5])], ["x/y"])
                lp = d.uid()
                lo = {}

                def lbody():
                    ld2 = dep2 + 1
                    tin = []
                    for k, (net, mode_) in enumerate([(rd["data"], "index"), (j[3], "index"), (dt["x/y"], None)], 1):
                        tu = d.uid()
                        at = {"_id": f"In{k}", "inputs": f"value:{net}"}
                        if mode_:
                            at["mode"] = mode_
                        at.update({"outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp})
                        d.el("Tunnel", at, ld2)
                        tin.append(f"{tu}.value")
                    row, srow, dtv = tin
                    i0 = d.const(lp, ld2, "int32", "0")
                    i1 = d.const(lp, ld2, "int32", "1")
                    mn = d.node(lp, ld2, "Index Array", [("array", srow), ("index", i0)], ["element"])
                    mx = d.node(lp, ld2, "Index Array", [("array", srow), ("index", i1)], ["element"])
                    k1000 = d.const(lp, ld2, "double", "1000")
                    k4 = d.const(lp, ld2, "double", "4")
                    k16 = d.const(lp, ld2, "double", "16")
                    ma = d.node(lp, ld2, "Multiply", [("x", row), ("y", k1000)], ["x*y"])
                    s4 = d.node(lp, ld2, "Subtract", [("x", ma["x*y"]), ("y", k4)], ["x-y"])
                    n16 = d.node(lp, ld2, "Divide", [("x", s4["x-y"]), ("y", k16)], ["x/y"])
                    span = d.node(lp, ld2, "Subtract", [("x", mx["element"]), ("y", mn["element"])], ["x-y"])
                    ms = d.node(lp, ld2, "Multiply", [("x", n16["x/y"]), ("y", span["x-y"])], ["x*y"])
                    eu = d.node(lp, ld2, "Add", [("x", ms["x*y"]), ("y", mn["element"])], ["x+y"])
                    wf = d.node(lp, ld2, "Build Waveform", [("waveform", ""), ("dt", dtv), ("Y", eu["x+y"])],
                                ["output waveform"], fields="dt,Y")
                    for k, net in enumerate([eu["x+y"], wf["output waveform"]], 1):
                        tu = d.uid()
                        d.el("Tunnel", {"_id": f"Out{k}", "inputs": f"value:{net}", "mode": "index",
                                        "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lp}, ld2)
                        lo[k] = f"{tu}.value"
                d.el("Structure", {"_name": "For Loop", "count": "", "maxin": "", "maxout": "",
                                   "uid": lp, "uid_parent": fu2}, dep2, lbody)
                d.el("Indicator", {"_name": "Scaled Data Chart", "inputs": f"value:{lo[2]}",
                                   "style": "graph21717", "type": "array{doublewaveform.Waveform}",
                                   "uid": d.uid(), "uid_parent": fu2, "value": "[]"}, dep2)
                tr = d.node(fu2, dep2, "Transpose 2D Array", [("2D array", lo[1])], ["transposed array"])
                ba = d.node(fu2, dep2, "Build Array", [("array", j[2]), ("array", tr["transposed array"])],
                            ["appended array"], concat="true")
                kfin = d.const(fu2, dep2, "int32", "10178")
                eq = d.node(fu2, dep2, "Equal?", [("x", j[6]), ("y", kfin)], ["x = y?"])

                def finite_done(fu3, dep3, k):
                    sp = d.call(fu3, dep3, "DAQmx Stop Task.vi",
                                [("task/channels in", k[0]), ("error in", k[1])], ["task out", "error out"])
                    cl = d.call(fu3, dep3, "DAQmx Clear Task.vi",
                                [("task in", sp["task out"]), ("error in", sp["error out"])], ["error out"])
                    f = d.const(fu3, dep3, "bool", "false")
                    return [k[0], cl["error out"], f]

                def keep(fu3, dep3, k):
                    t = d.const(fu3, dep3, "bool", "true")
                    return [k[0], k[1], t]

                o = d.struct(fu2, dep2, "Case Structure", [rd["task out"], rd["error out"]], 3,
                             [({"selector": "True", "label": "Finite: stop and clear after the read"}, finite_done),
                              ({"selector": "False", "label": "Continuous: keep running"}, keep)],
                             selectin=eq["x = y?"])
                return [o[0], o[1], ba["appended array"], o[2]]

            def idle(fu2, dep2, j):
                f = d.const(fu2, dep2, "bool", "false")
                return [j[0], j[1], j[2], f]

            scale = fctl(fu, dep, "Scale (Min/Max)", "array.2{double}",
                         "[[0,100],[0,100],[0,100],[0,100],[0,100],[0,100],[0,100],[0,100]]")
            o = d.struct(fu, dep, "Case Structure", [i[0], i[3], i[2], scale, i[6], i[5], i[4]], 4,
                         [({"selector": "True", "label": "Read\\2C scale\\2C chart\\2C buffer"}, acquire),
                          ({"selector": "False", "label": "Idle"}, idle)],
                         selectin=i[1])
            f = d.const(fu, dep, "bool", "false")
            return [o[0], o[3], o[2], o[1], f, i[4], i[5], i[6]]

        def ev_close(fu, dep, i):
            t = d.const(fu, dep, "bool", "true")
            return [i[0], i[1], i[2], i[3], t, i[4], i[5], i[6]]

        ev_out = d.struct(loop, ld, "Event Structure",
                          [left["task"], left["run"], left["buf"], left["err"], left["mode"], left["rate"], left["ns"]], 8,
                          [({"selector": ' "Start"\\3A Value Change '}, ev_start),
                           ({"selector": ' "Stop"\\3A Value Change '}, ev_stop),
                           ({"selector": ' "Save Data"\\3A Value Change '}, ev_save),
                           ({"selector": " Timeout "}, ev_timeout),
                           ({"selector": " Panel Close? "}, ev_close)],
                          timeoutin=tmo)
        # loop stop: panel closed or error
        es = d.node(loop, ld, "Unbundle By Name", [("input cluster", ev_out[3])], ["status"], fields="status")
        orr = d.node(loop, ld, "Or", [("x", ev_out[4]), ("y", es["status"])], ["x .or. y?"])
        d.el("Condition", {"inputs": f"value:{orr['x .or. y?']}", "uid": d.uid(), "uid_parent": loop,
                           "value": "stop"}, ld)
        rights = {"task": ev_out[0], "run": ev_out[1], "buf": ev_out[2], "err": ev_out[3],
                  "mode": ev_out[5], "rate": ev_out[6], "ns": ev_out[7]}
        for k in names:
            su = d.uid()

            def srb(su=su, k=k):
                lu = left_uid[k]
                d.el("Left", {"inputs": f"value:{seeds[k]}", "outputs": f"value:{left[k]}", "uid": lu,
                              "uid_parent": su}, ld + 1)
                ru = d.uid()
                fin = f"{ru}.value" if k in ("task", "run", "err") else ""
                final[k] = fin
                d.el("Right", {"inputs": f"value:{rights[k]}", "outputs": f"value:{fin}", "uid": ru,
                               "uid_parent": su}, ld + 1)
            d.el("ShiftReg", {"uid": su, "uid_parent": loop}, ld, srb)

    d.el("Structure", {"_name": "While Loop", "count": "", "uid": loop, "uid_parent": fu}, dep, loop_body)

    # after the loop: clear a task left running when the panel closed
    def clr(fu2, dep2, j):
        cl = d.call(fu2, dep2, "DAQmx Clear Task.vi", [("task in", j[0]), ("error in", j[1])], ["error out"])
        return [cl["error out"]]

    def noclr(fu2, dep2, j):
        return [j[1]]

    o = d.struct(fu, dep, "Case Structure", [final["task"], final["err"]], 1,
                 [({"selector": "True", "label": "Task still running: clear it"}, clr),
                  ({"selector": "False"}, noclr)],
                 selectin=final["run"])
    return [o[0]]


def frame_error(fu, dep, ins):
    return [ins[0]]


outer = d.struct(ROOT, 1, "Case Structure", [err_in], 1,
                 [({"selector": "False", "label": "No Error"}, frame_noerror),
                  ({"selector": "True", "label": "Error"}, frame_error)],
                 selectin=st["status"])
d.el("Indicator", {"_name": "error out", "conIdx": "15", "connection": "recommended",
                   "inputs": f"value:{outer[0]}", "type": ERR_T, "uid": err_out_uid,
                   "uid_parent": ROOT, "value": "[false,0,]"}, 1)

body = "\n".join(d.out)
# resolve shift-register placeholder nets (SRL_k -> Left uid nets)
import re
for m in re.finditer(r'<Left inputs="value:[^"]*" outputs="value:(SRL_\w+)" uid="(\d+)"', body):
    pass
# Left outputs keep the SRL_* token as the net name: arbitrary tokens are legal, keep them.
xml = lines_head + "\n" + body + "\n</VI>\n"
open(sys.argv[1], "w", encoding="utf-8").write(xml)
print("written", len(xml), "bytes, last uid", d.n)
