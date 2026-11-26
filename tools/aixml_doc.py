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


