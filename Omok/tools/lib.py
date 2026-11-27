"""Small AIXML builder used by every omok VI generator."""
import sys
from xml.sax.saxutils import quoteattr

ERR_T = "cluster{bool.status,int32.code,string.source}"
STONE = "uint8{Empty,Black,White}"
GRID = "array.2{" + STONE + "}"
MOVE = "cluster{int32.Row,int32.Col," + STONE + ".Stone}"
MOVES = "array{" + MOVE + "}"
DIR = "cluster{int32.dR,int32.dC}"
DIFF = "uint8{Easy,Normal,Hard,Master}"
FORB = "uint8{None,Double Three,Double Four,Overline}"
EMPTY, BLACK, WHITE = "0", "1", "2"
EMPTY_GRID = "[" + ",".join(["[" + ",".join(["0"] * 15) + "]"] * 15) + "]"


def kr(t):
    """Korean LabVIEW stores text as CP949: hand the composer CP949 bytes, one char per byte."""
    return t.encode("cp949").decode("latin-1")


def esc(t):
    return kr(t).replace(",", "\\2C").replace(":", "\\3A")


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

    # ---- leaves -----------------------------------------------------------
    def label(self, parent, depth, text):
        self.el("FreeLabel", {"comment": esc(text), "uid": self.uid(), "uid_parent": parent}, depth)

    def const(self, parent, depth, typ, value, name=None):
        u = self.uid()
        at = {}
        if name:
            at["_name"] = name
        at.update({"outputs": f"value:{u}.value", "type": typ, "uid": u, "uid_parent": parent, "value": value})
        self.el("Constant", at, depth)
        return f"{u}.value"

    def ctl(self, parent, depth, name, typ, value, conIdx=None, conn=None, **extra):
        u = self.uid()
        at = {"_name": name}
        if conIdx is not None:
            at["conIdx"] = str(conIdx)
            at["connection"] = conn or "recommended"
        at.update(extra)
        at.update({"outputs": f"value:{u}.value", "type": typ, "uid": u, "uid_parent": parent, "value": value})
        self.el("Control", at, depth)
        return f"{u}.value"

    def ind(self, parent, depth, name, typ, value, net, conIdx=None, **extra):
        u = self.uid()
        at = {"_name": name}
        if conIdx is not None:
            at["conIdx"] = str(conIdx)
            at["connection"] = "recommended"
        at.update(extra)
        at.update({"inputs": f"value:{net}", "type": typ, "uid": u, "uid_parent": parent, "value": value})
        self.el("Indicator", at, depth)
        return u

    def node(self, parent, depth, name, inputs, outs, **extra):
        u = self.uid()
        ins = ",".join(f"{t}:{n}" for t, n in inputs)
        onets = {t: f"{u}.{t}" for t in outs}
        at = {"_name": name}
        at.update(extra)
        at.update({"inputs": ins, "outputs": ",".join(f"{t}:{onets[t]}" for t in outs),
                   "uid": u, "uid_parent": parent})
        self.el("Node", at, depth)
        return onets

    def call(self, parent, depth, target, inputs, outs, instance=None):
        u = self.uid()
        ins = ",".join(f"{t}:{n}" for t, n in inputs)
        onets = {t: f"{u}.{t}" for t in outs}
        at = {}
        if instance:
            at["adapt"] = "true"
            at["instance"] = instance
        at.update({"target": target, "inputs": ins, "outputs": ",".join(f"{t}:{onets[t]}" for t in outs),
                   "uid": u, "uid_parent": parent})
        self.el("Call", at, depth)
        return onets

    # ---- shorthand nodes --------------------------------------------------
    def bin(self, p, d, name, x, y, out):
        return self.node(p, d, name, [("x", x), ("y", y)], [out])[out]

    def add(self, p, d, x, y): return self.bin(p, d, "Add", x, y, "x+y")
    def sub(self, p, d, x, y): return self.bin(p, d, "Subtract", x, y, "x-y")
    def mul(self, p, d, x, y): return self.bin(p, d, "Multiply", x, y, "x*y")
    def div(self, p, d, x, y): return self.bin(p, d, "Divide", x, y, "x/y")
    def eq(self, p, d, x, y): return self.bin(p, d, "Equal?", x, y, "x = y?")
    def ne(self, p, d, x, y): return self.bin(p, d, "Not Equal?", x, y, "x != y?")
    def ge(self, p, d, x, y): return self.bin(p, d, "Greater Or Equal?", x, y, "x >= y?")
    def gt(self, p, d, x, y): return self.bin(p, d, "Greater?", x, y, "x > y?")
    def lt(self, p, d, x, y): return self.bin(p, d, "Less?", x, y, "x < y?")
    def le(self, p, d, x, y): return self.bin(p, d, "Less Or Equal?", x, y, "x <= y?")
    def and_(self, p, d, x, y): return self.bin(p, d, "And", x, y, "x .and. y?")
    def or_(self, p, d, x, y): return self.bin(p, d, "Or", x, y, "x .or. y?")

    def not_(self, p, d, x):
        return self.node(p, d, "Not", [("x", x)], [".not. x?"])[".not. x?"]

    def neg(self, p, d, x):
        return self.node(p, d, "Negate", [("x", x)], ["-x"])["-x"]

    def sel(self, p, d, s, t, f):
        return self.node(p, d, "Select", [("t", t), ("s", s), ("f", f)], ["s? t\\3Af"])["s? t\\3Af"]

    def max_(self, p, d, x, y):
        o = self.node(p, d, "Max & Min", [("x", x), ("y", y)], ["max(x\\2Cy)", "min(x\\2Cy)"])
        return o["max(x\\2Cy)"]

    def unb(self, p, d, cluster, fields):
        o = self.node(p, d, "Unbundle By Name", [("input cluster", cluster)], fields, fields=",".join(fields))
        return [o[f] for f in fields]

    def bnd(self, p, d, cluster, pairs):
        fields = [f for f, _ in pairs]
        o = self.node(p, d, "Bundle By Name", list(pairs) + [("input cluster", cluster)], ["output cluster"],
                      fields=",".join(fields))
        return o["output cluster"]

    def idx2(self, p, d, arr, r, c):
        return self.node(p, d, "Index Array", [("array", arr), ("index (row)", r), ("index (col)", c)],
                         ["element"], dimensions="2")["element"]

    def rep2(self, p, d, arr, r, c, v):
        return self.node(p, d, "Replace Array Subset",
                         [("array", arr), ("index (row)", r), ("index (col)", c), ("new element/subarray", v)],
                         ["output array"], dimensions="2")["output array"]

    def idx1(self, p, d, arr, i):
        return self.node(p, d, "Index Array", [("array", arr), ("index", i)], ["element"])["element"]

    def inrange(self, p, d, x, lo, hi):
        o = self.node(p, d, "In Range and Coerce", [("upper limit", hi), ("x", x), ("lower limit", lo)],
                      ["coerced(x)", "In Range?"], includeLow="true", includeHigh="true")
        return o["In Range?"]

    def size(self, p, d, arr):
        return self.node(p, d, "Array Size", [("array", arr)], ["size(s)"])["size(s)"]

    def noerr(self, p, d):
        return self.const(p, d, ERR_T, "[false,0,]")

    def i32(self, p, d, v): return self.const(p, d, "int32", str(v))
    def dbl(self, p, d, v): return self.const(p, d, "double", str(v))
    def b(self, p, d, v): return self.const(p, d, "bool", "true" if v else "false")

    # ---- structures -------------------------------------------------------
    def case(self, parent, depth, selectin, in_nets, nouts, frames, **sattrs):
        """frames: list of (selector, label, fn(fu, fdepth, ins)->outs)"""
        su = self.uid()
        outer = []

        def body():
            for i, net in enumerate(in_nets, 1):
                self.el("Tunnel", {"_id": f"In{i}", "inputs": f"value:{net}", "uid": self.uid(), "uid_parent": su},
                        depth + 1)
            for sel_, lab, fn in frames:
                fu = self.uid()

                def fbody(fu=fu, fn=fn):
                    ins = []
                    for i in range(1, len(in_nets) + 1):
                        tu = self.uid()
                        self.el("Tunnel", {"_id": f"In{i}", "outputs": f"value:{tu}.value", "uid": tu,
                                           "uid_parent": fu}, depth + 2)
                        ins.append(f"{tu}.value")
                    outs = fn(fu, depth + 2, ins)
                    assert len(outs) == nouts, (sel_, len(outs), nouts)
                    for j, o in enumerate(outs, 1):
                        self.el("Tunnel", {"_id": f"Out{j}", "inputs": f"value:{o}", "uid": self.uid(),
                                           "uid_parent": fu}, depth + 2)
                at = {"selector": sel_, "selectout": ""}
                if lab:
                    at["label"] = esc(lab)
                at.update({"uid": fu, "uid_parent": su})
                self.el("CaseFrame", at, depth + 1, fbody)
            for j in range(1, nouts + 1):
                tu = self.uid()
                self.el("Tunnel", {"_id": f"Out{j}", "outputs": f"value:{tu}.value", "uid": tu, "uid_parent": su},
                        depth + 1)
                outer.append(f"{tu}.value")
        at = {"_name": kind_name(sattrs)}
        sattrs.pop("_kind", None)
        at.update(sattrs)
        at.update({"selectin": selectin} if selectin is not None else {})
        at.update({"uid": su, "uid_parent": parent})
        self.el("Structure", at, depth, body)
        return outer

    def event(self, parent, depth, in_nets, nouts, frames, **sattrs):
        return self.case(parent, depth, None, in_nets, nouts, frames, _kind="Event Structure", **sattrs)

    def loop(self, kind, parent, depth, ins, srs, body, maxin=None, label=None):
        """ins: list of (net, mode or None); srs: list of seed nets.
        body(lu, ld, in_nets, sr_left, i_net) -> (outs[(net, mode)], sr_right[], stop_net or None)
        returns (outer_out_nets, sr_final_nets)"""
        lu = self.uid()
        res = {}

        def lbody():
            ld = depth + 1
            in_nets = []
            for k, (net, mode) in enumerate(ins, 1):
                tu = self.uid()
                at = {"_id": f"In{k}", "inputs": f"value:{net}"}
                if mode:
                    at["mode"] = mode
                at.update({"outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lu})
                self.el("Tunnel", at, ld)
                in_nets.append(f"{tu}.value")
            left_uids = [self.uid() for _ in srs]
            left = [f"{u}.value" for u in left_uids]
            outs, rights, stop = body(lu, ld, in_nets, left, f"{lu}.value")
            outer = []
            for k, ent in enumerate(outs, 1):
                net, mode = ent[0], ent[1]
                tu = self.uid()
                at = {"_id": f"Out{k}"}
                if len(ent) > 2:
                    at["cond"] = ent[2]
                at["inputs"] = f"value:{net}"
                if mode:
                    at["mode"] = mode
                at.update({"outputs": f"value:{tu}.value", "uid": tu, "uid_parent": lu})
                self.el("Tunnel", at, ld)
                outer.append(f"{tu}.value")
            finals = []
            for seed, lid, rnet in zip(srs, left_uids, rights):
                su = self.uid()
                ru = self.uid()
                finals.append(f"{ru}.value")

                def srb(su=su, seed=seed, lid=lid, rnet=rnet, ru=ru):
                    self.el("Left", {"inputs": f"value:{seed}", "outputs": f"value:{lid}.value", "uid": lid,
                                     "uid_parent": su}, ld + 1)
                    self.el("Right", {"inputs": f"value:{rnet}", "outputs": f"value:{ru}.value", "uid": ru,
                                      "uid_parent": su}, ld + 1)
                self.el("ShiftReg", {"uid": su, "uid_parent": lu}, ld, srb)
            if kind == "While Loop":
                self.el("Condition", {"inputs": f"value:{stop}", "uid": self.uid(), "uid_parent": lu,
                                      "value": "stop"}, ld)
            res["outer"], res["finals"] = outer, finals
        at = {"_name": kind, "count": f"{lu}.value"}
        if kind == "For Loop":
            at["maxin"] = maxin or ""
            at["maxout"] = ""
        if label:
            at["label"] = esc(label)
        at.update({"uid": lu, "uid_parent": parent})
        self.el("Structure", at, depth, lbody)
        return res["outer"], res["finals"]

    def write(self, path, name, desc):
        xml = f'<VI _name={quoteattr(name)} description={quoteattr(kr(desc))}>\n' + "\n".join(self.out) + "\n</VI>\n"
        open(path, "w", encoding="utf-8").write(xml)
        return len(xml)


def kind_name(sattrs):
    return sattrs.get("_kind", "Case Structure")


BOARD_STATE = "cluster{" + GRID + ".Grid," + MOVES + ".Move History," + MOVE + ".Last Move}"
POINT16 = "cluster{int16.x,int16.y}"
CENTER16 = "cluster{int16.horizontal,int16.vertical}"
PEN = "cluster{uint16.Width,uint32{Solid,Dash,Dot,DashDot,DashDotDot}.Style}"
RECT16 = "cluster{int16.left,int16.top,int16.right,int16.bottom}"


P4833 = {11: 0, 10: 5, 9: 7, 8: 11, 3: 4, 2: 6, 1: 8, 0: 15}


def subvi(d, inputs, outputs, body, err_label=True):
    """conIdx values are written in 4815 terms (left 11,10,9 / err 8, right 3,2,1 / err 0) and mapped to
    this station's default pattern 4833."""
    m = lambda c: int(c[1:]) if isinstance(c, str) else P4833[c]
    inputs = [(n, t, v, m(c), cn) for n, t, v, c, cn in inputs]
    outputs = [(n, t, v, m(c)) for n, t, v, c in outputs]
    """Standard SubVI shell (pattern 4815): inputs [(name, type, value, conIdx, conn)],
    outputs [(name, type, default_literal, conIdx)]. Logic runs only when error in has no error.
    body(fu, dep, in_nets) -> list of output nets (same order as outputs)."""
    R = "root"
    in_nets = [d.ctl(R, 1, n, t, v, conIdx=c, conn=cn) for n, t, v, c, cn in inputs]
    err = d.ctl(R, 1, "error in", ERR_T, "[false,0,]", conIdx=11, conn="required")
    st = d.unb(R, 1, err, ["status"])[0]

    def ok(fu, dep, ins):
        return body(fu, dep, ins[:-1]) + [ins[-1]]

    def dflt(fu, dep, t, v):
        if t == "picture":
            return d.call(fu, dep, "Draw Rectangle.vi", [("rect", d.const(fu, dep, RECT16, "[0,0,0,0]"))],
                          ["new picture"])["new picture"]
        return d.const(fu, dep, t, v)

    def bad(fu, dep, ins):
        return [dflt(fu, dep, t, v) for _, t, v, _ in outputs] + [ins[-1]]

    outs = d.case(R, 1, st, in_nets + [err], len(outputs) + 1,
                  [("False", "No Error", ok), ("True", "Error", bad)])
    for (n, t, v, c), net in zip(outputs, outs):
        d.ind(R, 1, n, t, v, net, conIdx=c)
    d.ind(R, 1, "error out", ERR_T, "[false,0,]", outs[-1], conIdx=15)


SC = "cluster{double.Score,int32.Row,int32.Col}"
SCS = "array{" + SC + "}"


def qr(d, p, dep, x, y):
    o = d.node(p, dep, "Quotient & Remainder", [("x", x), ("y", y)], ["x-y*floor(x/y)", "floor(x/y)"])
    return o["floor(x/y)"], o["x-y*floor(x/y)"]


def opp_stone(d, p, dep, st):
    return d.sel(p, dep, d.eq(p, dep, st, d.const(p, dep, STONE, BLACK)), d.const(p, dep, STONE, WHITE),
                 d.const(p, dep, STONE, BLACK))


# ---- v2: canvas UI -------------------------------------------------------
W, H = 592, 780
FONT = ("cluster{string.Font Name\\3A,int16.Size,bool.Strikeout?,bool.Italic?,bool.Underline?,bool.Outline?,"
        "bool.Shadow?,bool.Bold?}")
ALIGN = "cluster{uint16{left,center,right}.horizontal,uint16{top,center,bottom}.vertical}"
SPEC = ("cluster{" + RECT16 + ".Rect,uint32.Fill,uint32.Fill Sel,uint32.Border,uint32.Border Sel,string.Text,"
        "uint32.Text Color,uint32.Text Sel,int16.Size,bool.Bold,int32.Group,int32.Value,int16.Radius}")
SPECS = "array{" + SPEC + "}"
SCREEN = "uint16{Settings,Game}"
GSTAT = "uint16{Idle,Player Turn,AI Thinking,Game Over}"
CTX = ("cluster{" + SCREEN + ".Screen,array{int32}.Settings," + BOARD_STATE + ".Board," + GSTAT + ".Status,"
       "uint32.Game ID," + STONE + ".Player Stone," + MOVE + ".Hover,int32.Hover Button," + MOVES + ".Win Line,"
       "int32.Score 1,int32.Score 2,int32.Draws,string.Status Text,uint32.Status Color}")
EMPTY_BS = "[" + EMPTY_GRID + ",[],[-1,-1,0]]"
CTX0 = "[0,[0,0,1,1]," + EMPTY_BS + ",0,0,1,[-1,-1,0],-1,[],0,0,0,,0]"
TRANSP = 16777216
BG = 0x3B2A1E
INK = 0x2C3E50


def font(d, p, dep, size, bold):
    f = d.const(p, dep, FONT, "[Malgun Gothic,16,false,false,false,false,false,false]")
    return d.bnd(p, dep, f, [("Size", size), ("Bold?", bold)])


def text_at(d, p, dep, pic, text, x, y, size, bold, color):
    """centered text; x, y, size: nets (int16-compatible)"""
    org = d.bnd(p, dep, d.const(p, dep, POINT16, "[0,0]"), [("x", x), ("y", y)])
    o = d.call(p, dep, "Draw Text at Point.vi",
               [("picture", pic), ("text", text), ("text color(black)", color), ("origin", org),
                ("alignment(left\\2C top)", d.const(p, dep, ALIGN, "[1,1]")),
                ("desired font(Application)", d.const(p, dep, "uint16{User-specified Font,Application Font,System Font,Dialog Font}", "0")),
                ("[user-specified font]", font(d, p, dep, size, bold))], ["text rect", "new picture"])
    return o["new picture"]


def u32(d, p, dep, v):
    return d.const(p, dep, "uint32", str(v))


def i16(d, p, dep, v):
    return d.const(p, dep, "int16", str(v))


def rrect(d, p, dep, pic, rect, color, fill, radius, pen_w=None):
    ins = [("rect", rect), ("color(black)", color), ("fill?(F)", d.b(p, dep, fill) if isinstance(fill, bool) else fill),
           ("oval width", radius), ("oval height", radius)]
    if pic is not None:
        ins.append(("picture", pic))
    if pen_w is not None:
        ins.append(("pen", d.bnd(p, dep, d.const(p, dep, PEN, "[2,0]"), [("Width", pen_w)])))
    return d.call(p, dep, "Draw Round Rect.vi", ins, ["new picture"])["new picture"]


def rect_c(d, p, dep, l, t, r, b):
    return d.const(p, dep, RECT16, f"[{l},{t},{r},{b}]")


def ai_inputs(d, p, dep, ctx):
    """Grid, AI Stone, Difficulty enum, Renju, Game ID taken from the Context."""
    sets, bs, pst, gid = d.unb(p, dep, ctx, ["Settings", "Board", "Player Stone", "Game ID"])
    grid = d.unb(p, dep, bs, ["Grid"])[0]
    diffs = d.const(p, dep, "array{" + DIFF + "}", "[0,1,2,3]", name="Difficulties")
    diff = d.idx1(p, dep, diffs, d.idx1(p, dep, sets, d.i32(p, dep, 2)))
    renju = d.eq(p, dep, d.idx1(p, dep, sets, d.i32(p, dep, 3)), d.i32(p, dep, 1))
    return grid, opp_stone(d, p, dep, pst), diff, renju, gid
