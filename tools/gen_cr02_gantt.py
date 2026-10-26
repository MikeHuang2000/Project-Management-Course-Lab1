"""Draw a combined Gantt chart: phase 1 (frozen) + phase 2 CR-02 increment.

Phase 2 starts on 2026-11-30 08:00, which is workday 20.0 from the phase-1
start (2026-11-02).  The gap between phase-1 finish (18.75) and phase-2 start
is shown explicitly; phase-1 bars and dates are not changed.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pm_metrics as pm

OUT = os.path.join(BASE, "plan", "gantt-cr02.png")
P1 = os.path.join(BASE, "plan", "tasks.csv")
P2 = os.path.join(BASE, "plan", "tasks-cr02.csv")


def load(path):
    tasks, order = pm.load_tasks(path)
    pm.cpm(tasks, order)
    return tasks, order


def main():
    pm.load_rates(os.path.join(BASE, "plan", "rates.csv"))
    p1, o1 = load(P1)
    p2, o2 = load(P2)
    f1 = max(t["ef"] for t in p1.values())
    f2 = max(t["ef"] for t in p2.values())
    offset = 20.0  # 2026-11-30 08:00, first workday after phase-1 acceptance
    total = offset + f2

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(11, 10))
    labels = []

    for i, tid in enumerate(o1):
        t = p1[tid]
        color = "#c0392b" if t["critical"] else "#5b8db8"
        ax.barh(i, t["duration"], left=t["es"], height=0.55, color=color, alpha=0.9)
        ax.text(t["es"] + t["duration"] + 0.08, i, "%.2f" % t["duration"],
                va="center", fontsize=6.5, color="#444")
        labels.append("%s %s" % (tid, t["name"]))

    sep = len(o1) - 0.5
    ax.axhline(sep, color="#7f8c8d", linewidth=1.0, linestyle="-")

    for j, tid in enumerate(o2):
        t = p2[tid]
        i = len(o1) + j
        left = offset + t["es"]
        ax.barh(i, t["duration"], left=left, height=0.55, color="#2e8b57", alpha=0.95)
        ax.text(left + t["duration"] + 0.08, i, "%.2f" % t["duration"],
                va="center", fontsize=6.5, color="#1e6b42")
        labels.append("%s %s" % (tid, t["name"]))

    ax.axvspan(f1, offset, color="#f2f2f2", alpha=0.8, zorder=0)
    ax.axvline(f1, color="#c0392b", linestyle="-.", linewidth=1.1)
    ax.axvline(offset, color="#2e8b57", linestyle="-.", linewidth=1.1)
    ax.text(f1 - 0.15, -1.0, "一期验收\n11/26 15:00", ha="right", va="top",
            fontsize=7.5, color="#c0392b")
    ax.text(offset + 0.15, -1.0, "二期启动\n11/30 08:00", ha="left", va="top",
            fontsize=7.5, color="#2e8b57")

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_ylim(len(labels) - 0.4, -1.5)
    ax.set_xlim(0, total + 1.2)
    ax.set_xlabel("工作日（自 2026-11-02 开始）", fontsize=9)
    ax.set_title("DeviceLoan MVP 甘特图：一期 %.2f 天 + 二期 CR-02 %.2f 天（验收后增量）"
                 % (f1, f2), fontsize=11)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend(handles=[
        Patch(color="#c0392b", label="一期关键路径"),
        Patch(color="#5b8db8", label="一期非关键"),
        Patch(color="#2e8b57", label="二期 CR-02（2.5 天）"),
    ], loc="lower left", fontsize=8)

    ax2 = ax.twiny()
    ticks = [0, 5, 10, 15, f1, offset, total]
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(ticks)
    ax2.set_xticklabels([
        "11-02", "11-09", "11-16", "11-23", "11-26", "11-30", "12-02"
    ], fontsize=7)
    ax2.tick_params(axis="x", length=2, pad=1)
    ax2.set_xlabel("日历（关键节点）", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT, dpi=170)
    print("GANTT=%s phase1=%.2f phase2=%.2f total=%.2f" % (OUT, f1, f2, total))


if __name__ == "__main__":
    main()
