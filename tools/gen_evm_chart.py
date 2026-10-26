"""Draw the EVM trend chart used in the lab report."""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "plan", "evm.png")

DATES = [9.25, 10.50, 12.75, 14.00, 17.25, 18.75]
PV = [7162.50, 8712.50, 10625.00, 11775.00, 14300.00, 15800.00]
EV = [6675.00, 7825.00, 9575.00, 10887.50, 13900.00, 15800.00]
AC = [6982.00, 8429.00, 11035.50, 13045.50, 16394.90, 17974.90]

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(DATES, PV, marker="o", color="#5b8db8", linewidth=2, label="PV 计划价值")
ax.plot(DATES, EV, marker="s", color="#2e8b57", linewidth=2, label="EV 挣值")
ax.plot(DATES, AC, marker="^", color="#c0392b", linewidth=2, label="AC 实际成本")
ax.axvline(18.75, color="#7f8c8d", linestyle=":", linewidth=1)
ax.set_xlabel("数据日期（工作日）", fontsize=9)
ax.set_ylabel("金额（元）", fontsize=9)
ax.set_title("DeviceLoan MVP 挣值趋势：EV=PV=15,800；AC=17,974.90；CPI=0.879；SPI=1.000",
             fontsize=10)
ax.grid(linestyle=":", alpha=0.5)
ax.legend(loc="upper left", fontsize=8)
fig.tight_layout()
fig.savefig(OUT, dpi=170)
print("EVM=%s" % OUT)
