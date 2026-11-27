"""DAQ SubVIs: task create / read / scale / stop, TDMS log open / write."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

OUT = sys.argv[1]
ERRIN = None


def scale():
    d = Doc()

    def body(fu, dep, ins):
        raw, chs = ins
        d.label(fu, dep, "4~20 mA -> Scale Min~Max, 표시값 = 평균")

        def lb(lu, ld, i, L, it):
            row, ch = i
            smin, smax = d.unb(lu, ld, ch, ["Scale Min", "Scale Max"])
            k = d.div(lu, ld, d.sub(lu, ld, smax, smin), d.dbl(lu, ld, 0.016))
            y = d.add(lu, ld, d.mul(lu, ld, d.sub(lu, ld, row, d.dbl(lu, ld, 0.004)), k), smin)
            n = d.size(lu, ld, y)
            s = d.node(lu, ld, "Add Array Elements", [("numeric array", y)], ["sum"])["sum"]
            mean = d.div(lu, ld, s, d.max_(lu, ld, n, d.i32(lu, ld, 1)))
            return [(y, "index"), (mean, "index")], [], None
        outs, _ = d.loop("For Loop", fu, dep, [(raw, "index"), (chs, "index")], [], lb)
        return outs

    subvi(d, [("Raw Data (A)", "array.2{double}", "[]", "r0", "required"),
              ("Channels", CHANNELS, "[]", "r5", "required")],
          [("Scaled Data", "array.2{double}", "[]", "r4"), ("Values", "array{double}", "[]", "r6")], body)
    return d.write(f"{OUT}/DAQ_Scale.xml", "DAQ_Scale.vi",
                   "채널별 4~20 mA 선형 환산: y = Scale Min + (I - 4 mA) x (Scale Max - Scale Min) / 16 mA.\\0A"
                   "Values = 채널별 평균(디지털 인디케이터 표시값).")


def tdms_path():
    d = Doc()

    def body(fu, dep, ins):
        folder = ins[0]
        d.label(fu, dep, "파일명 AI_년월일_시분초.tdms")
        ts = d.node(fu, dep, "Format Date/Time String",
                    [("time format string (%c)", d.const(fu, dep, "string", "%Y%m%d_%H%M%S"))], ["date/time string"])
        name = d.node(fu, dep, "Concatenate Strings",
                      [("string", d.const(fu, dep, "string", "AI_")), ("string", ts["date/time string"]),
                       ("string", d.const(fu, dep, "string", ".tdms"))], ["concatenated string"])["concatenated string"]
        p = d.node(fu, dep, "Build Path", [("base path", folder), ("name or relative path", name)],
                   ["appended path"])["appended path"]
        return [p]

    subvi(d, [("Save Folder", "path", "", "r0", "required")], [("File Path", "path", "", "r4")], body)
    return d.write(f"{OUT}/TDMS_Make_Path.xml", "TDMS_Make_Path.vi",
                   "저장 폴더 + AI_YYYYMMDD_HHMMSS.tdms 경로 생성.")


def tdms_write():
    d = Doc()

    def body(fu, dep, ins):
        p, data, chs, err = ins
        d.label(fu, dep, "Save가 켜진 채널 행만 골라 추가 기록")

        def lb(lu, ld, i, L, it):
            row, ch = i
            nm, sv = d.unb(lu, ld, ch, ["Name", "Save"])
            return [(row, "index", sv), (nm, "index", sv)], [], None
        outs, _ = d.loop("For Loop", fu, dep, [(data, "index"), (chs, "index")], [], lb)
        op = d.const(fu, dep, "uint16{open,open or create,create or replace,create,open (read-only)}", "1")
        to = d.node(fu, dep, "TDMS Open", [("file path", p), ("operation (0\\3Aopen)", op), ("error in (no error)", err)],
                    ["tdms file out", "error out"])
        tw = d.node(fu, dep, "TDMS Write",
                    [("tdms file", to["tdms file out"]), ("group name in (Untitled)", d.const(fu, dep, "string", "AI Data")),
                     ("channel name(s) in (Untitled)", outs[1]), ("data", outs[0]), ("error in (no error)", to["error out"])],
                    ["tdms file out", "error out"])
        d.label(fu, dep, "열기(없으면 생성) -> 쓰기 -> 닫기")
        tc = d.node(fu, dep, "TDMS Close", [("tdms file", tw["tdms file out"]), ("error in (no error)", tw["error out"])],
                    ["error out"])
        return [tc["error out"]]

    subvi(d, [("File Path", "path", "", "r0", "required"), ("Scaled Data", "array.2{double}", "[]", "r5", "required"),
              ("Channels", CHANNELS, "[]", "r7", "required")], [], body, err_through=True)
    return d.write(f"{OUT}/TDMS_Write_Log.xml", "TDMS_Write_Log.vi",
                   "Channels[i].Save = True 인 채널만 TDMS 'AI Data' 그룹에 채널 이름(Name)으로 추가 기록(열기-쓰기-닫기).")


if __name__ == "__main__":
    for fn in (scale, tdms_path, tdms_write):
        print(fn.__name__, fn())
