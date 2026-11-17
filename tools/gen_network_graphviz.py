"""Generate the PDM/AON network diagram with Graphviz (left-to-right).

Reuses plan/tasks.csv and the CPM engine in pm_metrics.py; does not reverse-engineer
the old PNG.  Writes plan/network.dot (source) and plan/network.png (rendered).

Requirements implemented:
  - rankdir=LR, activity-on-node boxes (Schwalbe textbook style)
  - every real dependency is labelled with its type (this project uses only FS)
  - a legend lists all four dependency types: FS / SS / FF / SF
  - node time data: duration, ES, EF, LS, LF, total float
  - critical path in red, plus the critical chain and project buffer shown at the end
"""

import argparse
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pm_metrics import DEFAULT_START, RATES, cpm, critical_path, fmt_date, load_rates, load_tasks  # noqa: E402


def find_dot(explicit):
    if explicit:
        return explicit
    found = shutil.which("dot")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Graphviz\bin\dot.exe",
        r"C:\Program Files (x86)\Graphviz\bin\dot.exe",
    ):
        if os.path.exists(candidate):
            return candidate
    sys.exit("找不到 Graphviz dot.exe，请用 --dot 指定路径")


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def node_id(tid):
    return "t" + tid.replace(".", "_").replace("-", "_")


def node_label(t):
    critical = t["critical"]
    border = "#c0392b" if critical else ("#5b8db8" if t["resource"] == "QA" else "#7f8c8d")
    fill = "#fdecea" if critical else ("#eef4fa" if t["resource"] == "QA" else "#f7f7f7")
    star = " ★关键" if critical else ""
    return (
        '<<table border="0" cellborder="1" cellspacing="0" cellpadding="2" '
        'color="%s" bgcolor="%s">' % (border, fill)
        + '<tr><td colspan="2" bgcolor="%s"><font face="Microsoft YaHei" '
          'point-size="10" color="%s"><b>%s %s</b></font></td></tr>'
          % (border, "white" if critical else "#222222", esc(t["id"]), esc(t["name"]))
        + '<tr><td><font face="Microsoft YaHei" point-size="9">%s</font></td>'
          '<td><font face="Microsoft YaHei" point-size="9">工期 %.2fd</font></td></tr>'
          % (esc(t["resource"]), t["duration"])
        + '<tr><td><font face="Microsoft YaHei" point-size="9">ES %.2f</font></td>'
          '<td><font face="Microsoft YaHei" point-size="9">EF %.2f</font></td></tr>'
          % (t["es"], t["ef"])
        + '<tr><td><font face="Microsoft YaHei" point-size="9">LS %.2f</font></td>'
          '<td><font face="Microsoft YaHei" point-size="9">LF %.2f</font></td></tr>'
          % (t["ls"], t["lf"])
        + '<tr><td colspan="2"><font face="Microsoft YaHei" point-size="9" '
          'color="%s">TF %.2f%s</font></td></tr>' % (border, t["float"], star)
        + "</table>>"
    )


def graph_label(tasks, finish, cp):
    chain = sum(tasks[x]["duration"] * 0.5 for x in cp)
    pb = chain * 0.5
    return (
        '<<table border="0" cellborder="0" cellspacing="0" cellpadding="3">'
        '<tr><td><font face="Microsoft YaHei" point-size="15"><b>'
        "DeviceLoan MVP — PDM / 前导图（活动节点 AON，从左到右）</b></font></td></tr>"
        '<tr><td><font face="Microsoft YaHei" point-size="10">'
        "总工期 %.2f 工作日 · %s → %s · 红框 = 关键路径 / 关键链活动"
        "</font></td></tr>" % (finish, fmt_date(DEFAULT_START, 0), fmt_date(DEFAULT_START, finish))
        + '<tr><td><font face="Microsoft YaHei" point-size="10">'
          "依赖类型（本项目实际全部为 FS）：<b>FS</b> 完成—开始 · <b>SS</b> 开始—开始 · "
          "<b>FF</b> 完成—完成 · <b>SF</b> 开始—完成"
          "</font></td></tr>"
        + '<tr><td><font face="Microsoft YaHei" point-size="10" color="#d68910">'
          "关键链 %.2f 天 + 项目缓冲 PB %.2f 天 = %.2f 天（对外承诺 20 天）"
          "</font></td></tr>" % (chain, pb, chain + pb)
        + "</table>>"
    )


def build_dot(tasks, order, finish, cp):
    lines = [
        "digraph pdm {",
        "  rankdir=LR;",
        '  graph [fontname="Microsoft YaHei", labelloc=t, nodesep=0.30, ranksep=0.55,',
        "          dpi=140, splines=ortho];",
        '  node [fontname="Microsoft YaHei", shape=box, style=filled];',
        '  edge [fontname="Microsoft YaHei", fontsize=9];',
        "  label=%s;" % graph_label(tasks, finish, cp),
    ]
    for tid in order:
        t = tasks[tid]
        lines.append("  %s [label=%s];" % (node_id(tid), node_label(t)))

    for tid in order:
        for pred in tasks[tid]["preds"]:
            both = tasks[pred]["critical"] and tasks[tid]["critical"]
            attrs = [
                'xlabel="FS"',
                "fontsize=8",
                'color="%s"' % ("#c0392b" if both else "#9bb4c9"),
                "penwidth=%.1f" % (2.0 if both else 0.9),
            ]
            lines.append("  %s -> %s [%s];" % (node_id(pred), node_id(tid), ", ".join(attrs)))

    # critical chain: the critical path is also the critical chain (single-role resource),
    # show the aggregated project buffer as the final dashed node.
    chain = sum(tasks[x]["duration"] * 0.5 for x in cp)
    pb = chain * 0.5
    lines.append(
        '  pb [label=<<table border="2" cellborder="0" cellspacing="0" cellpadding="4" '
        'color="#d68910" bgcolor="#fff6e6"><tr><td><font face="Microsoft YaHei" '
        'point-size="11" color="#d68910"><b>项目缓冲 PB %.2f 天</b></font></td></tr>'
        "</table>>, style=dashed, color=\"#d68910\"];" % pb
    )
    lines.append(
        "  %s -> pb [xlabel=\"缓冲\", style=dashed, color=\"#d68910\", penwidth=1.6, fontsize=9];"
        % node_id(cp[-1])
    )
    lines.append("}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="plan/tasks.csv")
    ap.add_argument("--rates", default="plan/rates.csv")
    ap.add_argument("--dot-file", default="plan/network.dot")
    ap.add_argument("--out", default="plan/network.png")
    ap.add_argument("--dot", default=None, help="Graphviz dot.exe path")
    a = ap.parse_args()

    load_rates(a.rates)
    tasks, _ = load_tasks(a.tasks)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    _, finish = cpm(tasks, list(tasks))
    cp = critical_path(tasks, list(tasks))

    source = build_dot(tasks, list(tasks), finish, cp)
    with open(a.dot_file, "w", encoding="utf-8") as f:
        f.write(source)

    dot = find_dot(a.dot)
    subprocess.run([dot, "-Tpng", a.dot_file, "-o", a.out], check=True)
    print("DOT=%s" % a.dot_file)
    print("NETWORK=%s" % a.out)
    print("CRITICAL_PATH=" + " -> ".join(cp))


if __name__ == "__main__":
    main()
