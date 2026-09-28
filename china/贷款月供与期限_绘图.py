# -*- coding: utf-8 -*-
"""
绘制《贷款月供和总年限的数学关系》的附图。

设定：贷款本金 P = 1,000,000 元，年利率 4%（月利率 r = 0.04/12），等额本息、按月还款。
月供：  M(T) = P * r / (1 - (1 + r) ** (-12 * T))
总利息： I(T) = M(T) * 12 * T - P

左侧子图：月供 vs 期限,并画出理论渐进线 Pr ≈ 3333 元/月。
右侧子图：总利息 vs 期限,反映 "月供趋平但总利息持续上升"。

输出：notes/china/imgs/贷款月供与期限.png
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---- 中文字体（Windows 常见 CJK 字体） ----
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

P = 1_000_000.0
annual_rate = 0.04
r = annual_rate / 12.0


def monthly_payment(T):
    """等额本息月供 M(T)。"""
    return P * r / (1 - (1 + r) ** (-12 * T))


def total_interest(T):
    """总利息 I(T)。"""
    return monthly_payment(T) * 12 * T - P


# 期限从 1 到 50 年，加密采样使曲线平滑
T = np.linspace(1, 50, 800)
M = monthly_payment(T)
I = total_interest(T) / 10_000.0  # 转为"万元"
asymptote = P * r  # 理论月供下限 ≈ 3333 元/月

fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2), dpi=180)

# ---- 左图：月供 vs 期限 ----
ax = axes[0]
ax.plot(T, M, color="#1565c0", linewidth=2.2, label="月供 M(T)")
ax.axhline(asymptote, color="#c62828", linestyle="--", linewidth=1.6,
           label="渐进线 $Pr\\approx¥3{,}333$/月")
# 标注几个关键点
for t, offset in [(1, (0, 8)), (10, (4, 10)), (20, (4, -22)), (30, (-34, 8))]:
    ax.annotate(f"{t}年", xy=(t, monthly_payment(t)),
                xytext=offset, textcoords="offset points", fontsize=9,
                color="#37474f", arrowprops=dict(arrowstyle="-", color="#90a4ae"))
ax.set_title("月供随期限递减并逐渐趋平", fontsize=12)
ax.set_xlabel("贷款期限 T（年）")
ax.set_ylabel("月供（元）")
ax.set_xlim(0, 50)
ax.set_ylim(2500, 96000)
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(fontsize=9, loc="upper right")

# ---- 右图：总利息 vs 期限 ----
ax = axes[1]
ax.plot(T, I, color="#00897b", linewidth=2.2, label="总利息 I(T)")
for t, offset in [(10, (4, 10)), (20, (-50, 8)), (30, (-50, -6)), (40, (4, -20))]:
    ax.annotate(f"{t}年", xy=(t, total_interest(t) / 10_000.0),
                xytext=offset, textcoords="offset points", fontsize=9,
                color="#37474f", arrowprops=dict(arrowstyle="-", color="#90a4ae"))
ax.set_title("总利息随期限持续上升", fontsize=12)
ax.set_xlabel("贷款期限 T（年）")
ax.set_ylabel("总利息（万元）")
ax.set_xlim(0, 50)
ax.set_ylim(0, 150)
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(fontsize=9, loc="upper left")

fig.tight_layout()
out = "d:/Git/stock_mindmap/notes/china/imgs/贷款月供与期限.png"
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("saved:", out)
print("asymptote ≈", asymptote)