import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
OUT = sys.argv[1]


def ch_defaults():
    d = Doc()

    def body(fu, dep, ins):
        d.label(fu, dep, "CH001~CH128 기본 설정 (0~100 %, 상한 80, 하한 20)")

        def lb(lu, ld, i, L, it):
            k = d.node(lu, ld, "Increment", [("x", it)], ["x+1"])["x+1"]
            s = d.node(lu, ld, "Number To Decimal String", [("number", k)], ["decimal integer string"])["decimal integer string"]
            pad = d.sel(lu, ld, d.lt(lu, ld, k, d.i32(lu, ld, 10)), d.const(lu, ld, "string", "00"),
                        d.sel(lu, ld, d.lt(lu, ld, k, d.i32(lu, ld, 100)), d.const(lu, ld, "string", "0"),
                              d.const(lu, ld, "string", "")))
            nm = d.node(lu, ld, "Concatenate Strings", [("string", d.const(lu, ld, "string", "CH")), ("string", pad),
                                                        ("string", s)], ["concatenated string"])["concatenated string"]
            g = d.lt(lu, ld, it, d.i32(lu, ld, 8))
            c = d.bnd(lu, ld, d.const(lu, ld, CHANNEL, "[CH000,0,80,20,true,false,0,100,%]"), [("Name", nm), ("Graph", g)])
            return [(c, "index")], [], None
        outs, _ = d.loop("For Loop", fu, dep, [], [], lb, maxin=d.i32(fu, dep, 128))
        d.label(fu, dep, "그래프는 처음 8채널만 선택")
        return outs

    subvi(d, [], [("Channels", CHANNELS, "[]", "r4")], body)
    return d.write(f"{OUT}/Ch_Defaults.xml", "Ch_Defaults.vi", "128채널 기본 Channel 배열(이름 CH001~CH128, 스케일 0~100 %, 상한 80/하한 20, 저장 ON, 그래프 CH001~CH008).")


if __name__ == "__main__":
    print(ch_defaults())
