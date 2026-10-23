"""Schedule / cost / EVM engine for the DeviceLoan MVP lab.

Single source of truth: plan/tasks.csv
Columns: id, phase, name, resource, person_days, duration_days, predecessors, milestone

Outputs:
  schedule  -> critical path, float table (markdown)
  gantt     -> plan/gantt.png
  xml       -> wbs/wbs.xml (MS Project XML)
  evm       -> PV/EV/AC at a data date
  check     -> role effort and cost rollup, compared with plan/rates.csv
"""

import argparse
import csv
import datetime as dt
import json
import math
import os
import sys
from collections import defaultdict

RATES = {}
DEFAULT_START = dt.date(2026, 11, 2)  # Monday

PHASE_NAMES = {
    "1": "启动", "2": "规划", "3": "执行", "4": "监控", "5": "收尾",
}


# ---------------------------------------------------------------- input
def load_rates(path):
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            RATES[row["role"]] = float(row["daily_rate_cny"])


def load_tasks(path):
    tasks, order = {}, []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t = {
                "id": row["id"].strip(),
                "phase": row["phase"].strip(),
                "name": row["name"].strip(),
                "resource": row["resource"].strip(),
                "person_days": float(row["person_days"] or 0),
                "duration": float(row["duration_days"] or 0),
                "preds": [p.strip() for p in (row.get("predecessors") or "").split(";") if p.strip()],
                "milestone": str(row.get("milestone") or "").strip().lower() in ("1", "true", "yes"),
            }
            t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
            tasks[t["id"]] = t
            order.append(t["id"])
    return tasks, order


# ---------------------------------------------------------------- CPM
def cpm(tasks, order):
    for tid, t in tasks.items():
        for p in t["preds"]:
            if p not in tasks:
                sys.exit("未知前置任务 %s (in %s)" % (p, tid))
    indeg = {tid: len(tasks[tid]["preds"]) for tid in order}
    succ = defaultdict(list)
    for tid in order:
        for p in tasks[tid]["preds"]:
            succ[p].append(tid)
    queue = [tid for tid in order if indeg[tid] == 0]
    topo = []
    while queue:
        tid = queue.pop(0)
        topo.append(tid)
        for s in succ[tid]:
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)
    if len(topo) != len(order):
        sys.exit("依赖存在环")

    for tid in topo:
        t = tasks[tid]
        t["es"] = max([tasks[p]["ef"] for p in t["preds"]], default=0.0)
        t["ef"] = t["es"] + t["duration"]
    finish = max(t["ef"] for t in tasks.values())
    for tid in reversed(topo):
        t = tasks[tid]
        t["lf"] = min([tasks[s]["ls"] for s in succ[tid]], default=finish)
        t["ls"] = t["lf"] - t["duration"]
        t["float"] = round(t["ls"] - t["es"], 4)
        t["critical"] = abs(t["float"]) < 1e-9
    return topo, finish


def critical_path(tasks, order):
    cur = [t for t in order if tasks[t]["critical"]]
    # walk the chain from the earliest critical task
    start = min(cur, key=lambda x: tasks[x]["es"])
    path, tid = [start], start
    while True:
        nxt = [s for s in order if tid in tasks[s]["preds"] and tasks[s]["critical"]]
        if not nxt:
            break
        tid = nxt[0]
        path.append(tid)
    return path


# ---------------------------------------------------------------- calendar
def day_to_date(start, d):
    """d = working-day offset (float) -> (date, hour within 08:00-16:00 workday)."""
    whole = int(math.floor(d + 1e-9))
    frac = d - whole
    cur = start
    added = 0
    while added < whole:
        cur += dt.timedelta(days=1)
        if cur.weekday() < 5:
            added += 1
    return cur, 8 + frac * 8


def fmt_date(start, d):
    day, hour = day_to_date(start, d)
    return "%s %02d:%02d" % (day.isoformat(), int(hour), int(round((hour % 1) * 60)))


# ---------------------------------------------------------------- report
def cmd_schedule(a):
    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    topo, finish = cpm(tasks, order)
    cp = critical_path(tasks, order)
    print("| WBS | 任务 | 资源 | 工期 | ES | EF | LS | LF | 浮动 | 关键 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for tid in order:
        t = tasks[tid]
        print("| %s | %s | %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %s |" % (
            tid, t["name"], t["resource"], t["duration"], t["es"], t["ef"],
            t["ls"], t["lf"], t["float"], "★" if t["critical"] else ""))
    print()
    print("PROJECT_DURATION=%.2f" % finish)
    print("CRITICAL_PATH=" + " -> ".join(cp))
    print("CRITICAL_SUM=%.2f" % sum(tasks[x]["duration"] for x in cp))
    # CCPM: cut 50% of duration as safety, aggregate into buffers
    chain = sum(tasks[x]["duration"] * 0.5 for x in cp)
    pb = chain * 0.5
    print("CCPM_CHAIN=%.2f" % chain)
    print("CCPM_PB=%.2f" % pb)
    print("CCPM_TOTAL=%.2f" % (chain + pb))


def cmd_check(a):
    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    days = defaultdict(float)
    cost = defaultdict(float)
    for t in tasks.values():
        days[t["resource"]] += t["person_days"]
        cost[t["resource"]] += t["person_days"] * RATES[t["resource"]]
    print("| 角色 | 人日 | 日薪 | 金额 |")
    print("|---|---|---|---|")
    for r in sorted(days):
        print("| %s | %.2f | %.0f | %.2f |" % (r, days[r], RATES[r], cost[r]))
    print("| 合计 | %.2f | — | %.2f |" % (sum(days.values()), sum(cost.values())))


def cmd_gantt(a):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    _, finish = cpm(tasks, order)

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(11, 9))
    labels = []
    for i, tid in enumerate(order):
        t = tasks[tid]
        left = t["es"]
        h = t["duration"]
        color = "#c0392b" if t["critical"] else "#5b8db8"
        ax.barh(i, h, left=left, height=0.55, color=color, alpha=0.9)
        ax.text(t["es"] + h + 0.08, i, "%.2f" % h, va="center", fontsize=7, color="#444")
        labels.append("%s %s" % (tid, t["name"]))
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, finish + 1.2)
    ax.set_xlabel("工作日（自项目开始）", fontsize=9)
    ax.set_title("DeviceLoan MVP 甘特图（红=关键路径，共 %.2f 个工作日）" % finish, fontsize=11)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend(handles=[Patch(color="#c0392b", label="关键路径"),
                       Patch(color="#5b8db8", label="非关键活动")],
              loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(a.out, dpi=160)
    print("GANTT=%s" % a.out)


def cmd_network(a):
    """PDM (activity-on-node) network: layered by dependency depth."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Rectangle

    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    topo, finish = cpm(tasks, order)

    depth = {}
    for tid in topo:
        preds = tasks[tid]["preds"]
        depth[tid] = 0 if not preds else max(depth[p] for p in preds) + 1

    # vertical layout: y = dependency depth, x = lane (critical path in the middle)
    W, H, XPITCH, YPITCH = 3.0, 0.90, 3.2, 1.12
    pos = {}
    for tid in order:
        if tasks[tid]["critical"]:
            lane = 0
        elif tasks[tid]["resource"] == "QA":
            lane = 1
        else:
            lane = -1
        pos[tid] = [lane * XPITCH, -depth[tid] * YPITCH]

    # spread nodes that share a lane and a depth (e.g. 5.2 and 5.3 are both critical)
    groups = defaultdict(list)
    for tid in order:
        groups[(round(pos[tid][0], 2), round(pos[tid][1], 2))].append(tid)
    for ids in groups.values():
        if len(ids) > 1:
            step = 1.1
            for i, tid in enumerate(ids):
                pos[tid][0] += (i - (len(ids) - 1) / 2) * (W / 2 + 0.25) * 2

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    rows = max(depth.values()) + 1
    fig, ax = plt.subplots(figsize=(7.2, rows * 0.43))

    for tid in order:
        t = tasks[tid]
        x, y = pos[tid]
        edge = "#c0392b" if t["critical"] else "#5b8db8"
        ax.add_patch(Rectangle((x - W / 2, y - H / 2), W, H, facecolor="white",
                               edgecolor=edge, linewidth=1.7 if t["critical"] else 0.9,
                               zorder=3))
        label = t["name"]
        if len(label) > 12:
            cut = label[:12]
            ax.text(x, y + 0.26, "%s %s" % (tid, cut), ha="center", va="center",
                    fontsize=6.0, zorder=4)
            ax.text(x, y + 0.05, label[12:24], ha="center", va="center",
                    fontsize=6.0, zorder=4)
            ty = -0.28
        else:
            ax.text(x, y + 0.16, "%s %s" % (tid, label), ha="center", va="center",
                    fontsize=6.0, zorder=4)
            ty = -0.22
        ax.text(x, y + ty, "%.2fd  ES %.2f  TF %.2f" % (t["duration"], t["es"], t["float"]),
                ha="center", va="center", fontsize=5.6,
                color="#c0392b" if t["critical"] else "#555", zorder=4)

    for tid in order:
        for p in tasks[tid]["preds"]:
            x1, y1 = pos[p]
            x2, y2 = pos[tid]
            both = tasks[p]["critical"] and tasks[tid]["critical"]
            ax.add_patch(FancyArrowPatch((x1, y1 - H / 2), (x2, y2 + H / 2),
                                         arrowstyle="-|>", mutation_scale=8,
                                         linewidth=1.4 if both else 0.8,
                                         color="#c0392b" if both else "#9bb4c9",
                                         connectionstyle="arc3,rad=%.2f" % (0.12 if x1 != x2 else 0),
                                         shrinkA=1, shrinkB=1, zorder=2))
    ax.set_xlim(-XPITCH - W / 2 - 0.3, XPITCH + W / 2 + 0.3)
    ax.set_ylim(-rows * YPITCH + 0.4, 0.9)
    ax.axis("off")
    ax.text(0, 0.55, "DeviceLoan MVP 前导图（PDM/AON）：红线为关键路径，共 %.2f 个工作日" % finish,
            ha="center", va="center", fontsize=9.5)
    ax.text(-XPITCH, 0.15, "旁支（PM/BA/CCB）", ha="center", fontsize=7, color="#5b8db8")
    ax.text(0, 0.15, "关键路径", ha="center", fontsize=7, color="#c0392b")
    ax.text(XPITCH, 0.15, "QA 验证", ha="center", fontsize=7, color="#5b8db8")
    fig.tight_layout()
    fig.savefig(a.out, dpi=170)
    print("NETWORK=%s" % a.out)


def cmd_xml(a):
    import xml.etree.ElementTree as ET

    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    cpm(tasks, order)
    start = dt.date.fromisoformat(a.start)

    def dur_str(days):
        h = days * 8
        return "PT%sH0M0S" % (("%.2f" % h).rstrip("0").rstrip("."))

    root = ET.Element("Project", xmlns="http://schemas.microsoft.com/project")
    ET.SubElement(root, "Name").text = "实验室设备借用管理系统（DeviceLoan MVP）"
    ET.SubElement(root, "Title").text = "DeviceLoan MVP WBS"
    ET.SubElement(root, "ScheduleFromStart").text = "1"
    ET.SubElement(root, "StartDate").text = start.isoformat() + "T08:00:00"
    ET.SubElement(root, "FinishDate").text = (
        dt.date.fromisoformat(fmt_date(start, max(t["ef"] for t in tasks.values())).split(" ")[0]).isoformat()
        + "T17:00:00")
    ET.SubElement(root, "CurrencyDigits").text = "0"
    ET.SubElement(root, "CurrencySymbol").text = "¥"

    tks = ET.SubElement(root, "Tasks")
    uid_of, uid = {}, 1
    # summary rows per phase
    phases = []
    for tid in order:
        ph = tasks[tid]["id"].split(".")[0]
        if ph not in phases:
            phases.append(ph)
    for ph in phases:
        kids = [tasks[x] for x in order if x.split(".")[0] == ph]
        s = ET.SubElement(tks, "Task")
        ET.SubElement(s, "UID").text = str(uid)
        ET.SubElement(s, "ID").text = str(uid)
        ET.SubElement(s, "Name").text = "%s %s" % (ph, PHASE_NAMES.get(ph, ""))
        ET.SubElement(s, "Type").text = "1"
        ET.SubElement(s, "IsNull").text = "0"
        ET.SubElement(s, "WBS").text = ph
        ET.SubElement(s, "OutlineNumber").text = ph
        ET.SubElement(s, "OutlineLevel").text = "1"
        ET.SubElement(s, "Start").text = start.isoformat() + "T08:00:00"
        ET.SubElement(s, "Finish").text = start.isoformat() + "T17:00:00"
        ET.SubElement(s, "Duration").text = dur_str(max(k["ef"] for k in kids) - min(k["es"] for k in kids))
        ET.SubElement(s, "DurationFormat").text = "7"
        ET.SubElement(s, "Milestone").text = "0"
        ET.SubElement(s, "Summary").text = "1"
        uid_of["phase:" + ph] = uid
        uid += 1

    for tid in order:
        t = tasks[tid]
        e = ET.SubElement(tks, "Task")
        ET.SubElement(e, "UID").text = str(uid)
        ET.SubElement(e, "ID").text = str(uid)
        ET.SubElement(e, "Name").text = t["name"]
        ET.SubElement(e, "Type").text = "1"
        ET.SubElement(e, "IsNull").text = "0"
        ET.SubElement(e, "WBS").text = tid
        ET.SubElement(e, "OutlineNumber").text = tid
        ET.SubElement(e, "OutlineLevel").text = "2"
        ET.SubElement(e, "Start").text = fmt_date(start, t["es"]).replace(" ", "T") + ":00"
        ET.SubElement(e, "Finish").text = fmt_date(start, t["ef"]).replace(" ", "T") + ":00"
        ET.SubElement(e, "Duration").text = dur_str(t["duration"])
        ET.SubElement(e, "DurationFormat").text = "7"
        ET.SubElement(e, "Work").text = dur_str(t["duration"])
        ET.SubElement(e, "Milestone").text = "1" if t["milestone"] else "0"
        ET.SubElement(e, "Summary").text = "0"
        ET.SubElement(e, "Cost").text = "%.2f" % t["budget"]
        ET.SubElement(e, "ResourceNames").text = t["resource"]
        for p in t["preds"]:
            link = ET.SubElement(e, "PredecessorLink")
            ET.SubElement(link, "PredecessorUID").text = str(uid_of[p])
            ET.SubElement(link, "Type").text = "1"
            ET.SubElement(link, "LinkLag").text = "0"
            ET.SubElement(link, "LagFormat").text = "7"
        uid_of[t["id"]] = uid
        uid += 1

    res = ET.SubElement(root, "Resources")
    for i, role in enumerate(sorted(RATES), start=1):
        r = ET.SubElement(res, "Resource")
        ET.SubElement(r, "UID").text = str(i)
        ET.SubElement(r, "ID").text = str(i)
        ET.SubElement(r, "Name").text = role
        ET.SubElement(r, "Type").text = "1"
        ET.SubElement(r, "StandardRate").text = "%.0f" % RATES[role]
        ET.SubElement(r, "StandardRateFormat").text = "3"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    tree.write(a.out, encoding="utf-8", xml_declaration=True)
    print("XML=%s tasks=%d" % (a.out, len(order)))


def load_progress(path):
    out = {}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                out[row["id"].strip()] = float(row.get("pct") or 0) / 100.0
    return out


def load_actuals(path):
    out = {}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                out[row["id"].strip()] = float(row.get("actual_days") or 0)
    return out


def load_adjust(path):
    rows = []
    if path and os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rows.append((row["role"].strip(), float(row["days"])))
    return rows


def evm_numbers(tasks, dd, progress, actuals, adjust):
    pv = 0.0
    for t in tasks.values():
        lo, hi = t["es"], t["ef"]
        frac = max(0.0, min(dd, hi) - lo) / (hi - lo) if hi > lo else (1.0 if dd >= hi else 0.0)
        pv += t["budget"] * max(0.0, min(frac, 1.0))
    ev = sum(t["budget"] * progress.get(tid, 0.0) for tid, t in tasks.items())
    ac = sum(actuals.get(tid, 0.0) * RATES[t["resource"]] for tid, t in tasks.items())
    ac += sum(days * RATES[role] for role, days in adjust)
    bac = sum(t["budget"] for t in tasks.values())
    cpi = ev / ac if ac else 0.0
    spi = ev / pv if pv else 0.0
    return {
        "data_date": round(dd, 2), "BAC": round(bac, 2), "PV": round(pv, 2),
        "EV": round(ev, 2), "AC": round(ac, 2), "CV": round(ev - ac, 2),
        "SV": round(ev - pv, 2), "CPI": round(cpi, 3), "SPI": round(spi, 3),
        "EAC": round(bac / cpi, 2) if cpi else 0.0,
        "VAC": round(bac - bac / cpi, 2) if cpi else 0.0,
    }


def cmd_evm(a):
    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    cpm(tasks, order)
    out = evm_numbers(tasks, float(a.date), load_progress(a.progress),
                      load_actuals(a.actuals), load_adjust(a.adjust))
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_status(a):
    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    cpm(tasks, order)
    progress = load_progress(a.progress)
    actuals = load_actuals(a.actuals)

    print("| WBS | 任务 | 负责 | 计划人日 | 实际人日 | 偏差 | 状态 | 预算 |")
    print("|---|---|---|---|---|---|---|---|")
    for tid in order:
        t = tasks[tid]
        pct = progress.get(tid, 0.0)
        act = actuals.get(tid)
        dev = "" if act is None else "%+.2f" % (act - t["person_days"])
        state = "完成" if pct >= 1 else ("进行中" if pct > 0 else "未开始")
        print("| %s | %s | %s | %.2f | %s | %s | %s | %.2f |" % (
            tid, t["name"], t["resource"], t["person_days"],
            "" if act is None else "%.2f" % act, dev, state, t["budget"]))
    print()
    done = sum(1 for tid in order if progress.get(tid, 0) >= 1)
    spent = sum(actuals.get(tid, 0) * RATES[tasks[tid]["resource"]] for tid in order)
    print("TASKS_DONE=%d/%d" % (done, len(order)))
    print("ACTUAL_COST=%.2f" % spent)
    for ph in ["1", "2", "3", "4", "5"]:
        ids = [x for x in order if x.split(".")[0] == ph]
        print("PHASE %s: %d/%d done" % (ph, sum(1 for x in ids if progress.get(x, 0) >= 1), len(ids)))


def cmd_track(a):
    """Tracking Gantt: baseline bar (dashed outline) vs actual days (filled), plus data date."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    tasks, order = load_tasks(a.tasks)
    load_rates(a.rates)
    for t in tasks.values():
        t["budget"] = round(t["person_days"] * RATES[t["resource"]], 2)
    _, finish = cpm(tasks, order)
    progress = load_progress(a.progress)
    actuals = load_actuals(a.actuals)
    adjust = load_adjust(a.adjust)
    done_ef = [t["ef"] for tid, t in tasks.items() if progress.get(tid, 0) >= 1.0]
    dd = float(a.date) if a.date not in (None, "", "0") else (max(done_ef) if done_ef else 0.0)
    evm = evm_numbers(tasks, dd, progress, actuals, adjust)

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(11, 9))
    labels = []
    for i, tid in enumerate(order):
        t = tasks[tid]
        pct = progress.get(tid, 0.0)
        ax.barh(i, t["duration"], left=t["es"], height=0.64, facecolor="none",
                edgecolor="#9aa5ad", linestyle="--", linewidth=0.8)
        act = actuals.get(tid)
        if act is not None:
            color = "#2e8b57" if pct >= 1.0 else ("#d68910" if pct > 0 else "#5b8db8")
            ax.barh(i, act, left=t["es"], height=0.40, color=color, alpha=0.95)
            if abs(act - t["duration"]) > 1e-9:
                ax.text(t["es"] + max(act, t["duration"]) + 0.12, i, "%+.2f" % (act - t["duration"]),
                        va="center", fontsize=6.5, color="#c0392b")
        labels.append("%s %s" % (tid, t["name"]))
    ax.axvline(dd, color="#c0392b", linestyle="-.", linewidth=1.2)
    ax.text(dd + 0.08, -0.9, "数据日期 %.2f" % dd, color="#c0392b", fontsize=8, va="top")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_ylim(len(order) - 0.4, -1.4)
    ax.set_xlim(0, finish + 1.2)
    ax.set_xlabel("工作日（自项目开始）", fontsize=9)
    ax.set_title("追踪甘特图：计划 %.2f 天 / 数据日期 %.2f 天，CPI %.2f，SPI %.2f"
                 % (finish, dd, evm["CPI"], evm["SPI"]), fontsize=10.5)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend(handles=[Patch(facecolor="none", edgecolor="#9aa5ad", linestyle="--", label="计划工期"),
                       Patch(color="#2e8b57", label="已完成"),
                       Patch(color="#d68910", label="进行中")],
              loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(a.out, dpi=160)
    print(json.dumps(evm, ensure_ascii=False, indent=2))
    print("TRACK=%s" % a.out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["schedule", "check", "gantt", "network", "xml", "evm", "track", "status"])
    ap.add_argument("--tasks", default="plan/tasks.csv")
    ap.add_argument("--rates", default="plan/rates.csv")
    ap.add_argument("--out", default=None)
    ap.add_argument("--start", default=DEFAULT_START.isoformat())
    ap.add_argument("--date", default="0")
    ap.add_argument("--progress", default="plan/progress.csv")
    ap.add_argument("--actuals", default="plan/actuals.csv")
    ap.add_argument("--adjust", default="plan/adjust.csv")
    a = ap.parse_args()
    if a.out is None:
        a.out = {"xml": "wbs/wbs.xml", "network": "plan/network.png",
                 "track": "plan/track.png"}.get(a.cmd, "plan/gantt.png")
    load_rates(a.rates)
    {"schedule": cmd_schedule, "check": cmd_check, "gantt": cmd_gantt,
     "network": cmd_network, "xml": cmd_xml, "evm": cmd_evm, "track": cmd_track,
     "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
