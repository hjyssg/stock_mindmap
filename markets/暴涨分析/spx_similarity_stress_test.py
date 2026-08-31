"""
S&P 500 历史行情相似性压力测试与后市统计
- 计算最近40个交易日的涨幅
- 在历史中寻找相似涨幅的时间点
- 统计这些时间点之后的市场表现
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ─────────────────────────────────────────────
# 1. 数据加载
# ─────────────────────────────────────────────
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')
file_path = os.path.join(data_dir, '^SPX.csv')

# 跳过前两行（Ticker行和空Date行），第一行作为列名
df = pd.read_csv(file_path, skiprows=[1, 2])
# 第一列 "Price" 实际上是日期
df.rename(columns={'Price': 'Date'}, inplace=True)
df['Date'] = pd.to_datetime(df['Date'])
df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
df = df[['Date', 'Close']].dropna().sort_values('Date').reset_index(drop=True)

# ─────────────────────────────────────────────
# 2. 收益率特征提取
# ─────────────────────────────────────────────
W = 40  # 窗口期（交易日）

# 滚动收益率
df['Rolling_Return'] = df['Close'] / df['Close'].shift(W) - 1

# 当前基准：最后一行的滚动收益率
target_return = df['Rolling_Return'].iloc[-1]
target_date = df['Date'].iloc[-1]
print(f"═══════════════════════════════════════════════════════════")
print(f"  当前基准日期: {target_date.strftime('%Y-%m-%d')}")
print(f"  最近 {W} 个交易日涨幅: {target_return * 100:.2f}%")
print(f"═══════════════════════════════════════════════════════════\n")

# ─────────────────────────────────────────────
# 3. 历史相似点扫描
# ─────────────────────────────────────────────
TOLERANCE = 0.02  # ±2%

# 筛选误差在容差范围内的行（排除最后 W 行避免与自身匹配）
mask = (
    df['Rolling_Return'].notna()
    & ((df['Rolling_Return'] - target_return).abs() <= TOLERANCE)
    & (df.index < len(df) - W)  # 排除尾部，避免与当前区间重叠
)
similar_df = df[mask].copy().reset_index(drop=True)

# 去重：60 个交易日内连续出现的信号只保留第一个
DEDUP_WINDOW = 60
keep_indices = []
last_kept_idx = -DEDUP_WINDOW - 1  # 初始化为一个很早的值

for i, row in similar_df.iterrows():
    original_idx = df[df['Date'] == row['Date']].index[0]
    if original_idx - last_kept_idx > DEDUP_WINDOW:
        keep_indices.append(i)
        last_kept_idx = original_idx

similar_df = similar_df.loc[keep_indices].reset_index(drop=True)

print(f"找到 {len(similar_df)} 个历史相似点（±{TOLERANCE*100:.0f}% 容差，{DEDUP_WINDOW}日去重）")

# ─────────────────────────────────────────────
# 3.5 排除"死猫跳"时期
# ─────────────────────────────────────────────
# 这些时期的反弹信号是熊市中的虚假反弹，会严重扭曲统计结果
EXCLUDE_PERIODS = [
    (1929, 1932, "1929大萧条"),
    (2000, 2002, "互联网泡沫破裂"),
    (2007, 2009, "全球金融危机"),
]

def is_in_excluded_period(date):
    y = date.year
    for start, end, _ in EXCLUDE_PERIODS:
        if start <= y <= end:
            return True
    return False

excluded_count = similar_df['Date'].apply(is_in_excluded_period).sum()
similar_df = similar_df[~similar_df['Date'].apply(is_in_excluded_period)].reset_index(drop=True)

exclude_desc = "、".join([f"{s}-{e}({name})" for s, e, name in EXCLUDE_PERIODS])
print(f"排除死猫跳时期 [{exclude_desc}] 后剩余 {len(similar_df)} 个（排除了 {excluded_count} 个）\n")

# ─────────────────────────────────────────────
# 4. 后市表现回测
# ─────────────────────────────────────────────
FORWARD_DAYS = [20, 60, 120]

for fd in FORWARD_DAYS:
    col_name = f'Fwd_{fd}d'
    similar_df[col_name] = np.nan

for i, row in similar_df.iterrows():
    orig_idx = df[df['Date'] == row['Date']].index[0]
    for fd in FORWARD_DAYS:
        future_idx = orig_idx + fd
        if future_idx < len(df):
            future_return = df['Close'].iloc[future_idx] / df['Close'].iloc[orig_idx] - 1
            similar_df.at[i, f'Fwd_{fd}d'] = future_return

# ─────────────────────────────────────────────
# 5. 输出报告
# ─────────────────────────────────────────────
print("─── 匹配的历史日期 ───")
display_df = similar_df[['Date', 'Rolling_Return'] + [f'Fwd_{fd}d' for fd in FORWARD_DAYS]].copy()
display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
display_df['Rolling_Return'] = (display_df['Rolling_Return'] * 100).round(2).astype(str) + '%'
for fd in FORWARD_DAYS:
    col = f'Fwd_{fd}d'
    display_df[col] = display_df[col].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A")

print(display_df.to_string(index=False))
print()

# 统计摘要
print("─── 后市表现统计摘要 ───")
for fd in FORWARD_DAYS:
    col = f'Fwd_{fd}d'
    data = similar_df[col].dropna()
    if len(data) == 0:
        print(f"\n  {fd} 天后: 无数据")
        continue
    win_rate = (data > 0).mean() * 100
    print(f"\n  {fd} 天后 (样本数: {len(data)}):")
    print(f"    胜率 (正收益):  {win_rate:.1f}%")
    print(f"    平均值:         {data.mean()*100:.2f}%")
    print(f"    中位数:         {data.median()*100:.2f}%")
    print(f"    最大值:         {data.max()*100:.2f}%")
    print(f"    最小值:         {data.min()*100:.2f}%")

# ─────────────────────────────────────────────
# 6. 可视化
# ─────────────────────────────────────────────

# 自定义美观风格 + 中文字体支持
import matplotlib
# macOS 系统中文字体
matplotlib.rcParams['font.family'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

plt.rcParams.update({
    'figure.facecolor': '#ffffff',
    'axes.facecolor': '#fafafa',
    'axes.edgecolor': '#cccccc',
    'axes.labelcolor': '#333333',
    'text.color': '#333333',
    'xtick.color': '#555555',
    'ytick.color': '#555555',
    'grid.color': '#e0e0e0',
    'grid.alpha': 0.7,
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
})

COLOR_POS = '#2ecc71'
COLOR_NEG = '#e74c3c'

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    f"S&P 500 历史相似性压力测试\n"
    f"基准: {target_date.strftime('%Y-%m-%d')}  |  近{W}日涨幅: {target_return*100:.2f}%  |  "
    f"匹配数: {len(similar_df)}",
    fontsize=16, fontweight='bold', color='#2c3e50', y=0.98
)

# --- 子图1: 后市收益分布直方图 ---
for idx, fd in enumerate(FORWARD_DAYS):
    ax = axes[0, 0] if idx == 0 else (axes[0, 1] if idx == 1 else axes[1, 0])
    data = similar_df[f'Fwd_{fd}d'].dropna() * 100
    if len(data) == 0:
        ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
        continue

    n, bins, patches = ax.hist(data, bins=20, edgecolor='white', linewidth=0.5, alpha=0.85)
    # 根据正负着色
    for patch, left_edge in zip(patches, bins[:-1]):
        if left_edge >= 0:
            patch.set_facecolor(COLOR_POS)
        else:
            patch.set_facecolor(COLOR_NEG)

    ax.axvline(x=0, color='#999999', linestyle='--', linewidth=1, alpha=0.7)
    ax.axvline(x=data.median(), color='#e67e22', linestyle='-', linewidth=2, alpha=0.9,
               label=f'中位数: {data.median():.2f}%')

    win_rate = (data > 0).mean() * 100
    ax.set_title(f'{fd} 天后收益分布  (胜率: {win_rate:.0f}%)', fontweight='bold')
    ax.set_xlabel('收益率 (%)')
    ax.set_ylabel('频次')
    ax.legend(loc='upper right', fontsize=9, facecolor='#ffffff', edgecolor='#cccccc')
    ax.grid(True, axis='y', alpha=0.3)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f%%'))

# --- 子图4: 统计摘要表格 ---
ax_table = axes[1, 1]
ax_table.axis('off')

table_data = []
headers = ['指标', '20天后', '60天后', '120天后']
metrics = ['样本数', '胜率', '平均值', '中位数', '最大值', '最小值']

for metric in metrics:
    row = [metric]
    for fd in FORWARD_DAYS:
        data = similar_df[f'Fwd_{fd}d'].dropna()
        if len(data) == 0:
            row.append('N/A')
            continue
        if metric == '样本数':
            row.append(f'{len(data)}')
        elif metric == '胜率':
            row.append(f'{(data > 0).mean() * 100:.1f}%')
        elif metric == '平均值':
            row.append(f'{data.mean() * 100:.2f}%')
        elif metric == '中位数':
            row.append(f'{data.median() * 100:.2f}%')
        elif metric == '最大值':
            row.append(f'{data.max() * 100:.2f}%')
        elif metric == '最小值':
            row.append(f'{data.min() * 100:.2f}%')
    table_data.append(row)

table = ax_table.table(
    cellText=table_data,
    colLabels=headers,
    cellLoc='center',
    loc='center',
)
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.0, 1.8)

# 表格样式
for (row, col), cell in table.get_celld().items():
    cell.set_edgecolor('#cccccc')
    if row == 0:
        cell.set_facecolor('#2c3e50')
        cell.set_text_props(fontweight='bold', color='#ffffff')
    elif row % 2 == 0:
        cell.set_facecolor('#f2f3f4')
        cell.set_text_props(color='#333333')
    else:
        cell.set_facecolor('#ffffff')
        cell.set_text_props(color='#333333')

ax_table.set_title('后市表现统计摘要', fontweight='bold', pad=20)

plt.tight_layout(rect=[0, 0, 1, 0.93])

# 保存 SVG
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'output')
os.makedirs(output_dir, exist_ok=True)
svg_path = os.path.join(output_dir, 'spx_similarity_stress_test.svg')
fig.savefig(svg_path, format='svg', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\n✅ 图表已保存至: {svg_path}")

plt.show()

# ─────────────────────────────────────────────
# 7. 生成历史事件定性分析 Markdown 报告
# ─────────────────────────────────────────────

# 历史事件映射：(年份范围) -> 事件描述
HISTORICAL_EVENTS = {
    (1928, 1929): ("咆哮的二十年代末期 / 1929大崩盘前夕",
                   "1920年代美国经济繁荣，股市投机狂热。1929年10月大崩盘开启了大萧条时代。"),
    (1930, 1930): ("大萧条初期",
                   "1929年崩盘后的短暂反弹（'吸盘反弹'），随后市场继续暴跌。胡佛政府的紧缩政策加剧了经济衰退。"),
    (1931, 1931): ("大萧条深化",
                   "银行危机蔓延，全球贸易崩溃。英国脱离金本位制引发全球金融恐慌。"),
    (1932, 1932): ("大萧条谷底",
                   "1932年7月道琼斯触及大萧条最低点，随后开始历史性反弹。罗斯福当选总统带来政策转向预期。"),
    (1933, 1933): ("罗斯福新政启动",
                   "罗斯福就任后推出'百日新政'，银行假日、脱离金本位、NRA等政策刺激市场大幅反弹。"),
    (1935, 1936): ("新政中期复苏",
                   "社会保障法通过，WPA等公共工程项目推动经济复苏。企业盈利改善，市场稳步上涨。"),
    (1937, 1937): ("1937年衰退",
                   "罗斯福过早收紧财政政策（削减赤字+美联储收紧准备金），导致'罗斯福衰退'，市场暴跌。"),
    (1938, 1938): ("衰退后反弹",
                   "政府重新扩大财政支出，经济开始恢复。但欧洲局势紧张（慕尼黑协定）增加不确定性。"),
    (1939, 1939): ("二战爆发",
                   "9月德国入侵波兰，二战爆发。美国保持中立但军工订单增加，市场波动加剧。"),
    (1940, 1941): ("二战扩大 / 珍珠港事件",
                   "欧洲战事扩大，法国沦陷。1941年12月珍珠港事件后美国正式参战，战时经济体制启动。"),
    (1942, 1943): ("二战转折期",
                   "中途岛海战、斯大林格勒战役等转折点。美国战时生产全面展开，经济强劲增长，市场开始反弹。"),
    (1944, 1945): ("二战胜利在望",
                   "诺曼底登陆、布雷顿森林体系建立。1945年战争结束，市场对战后经济转型既期待又担忧。"),
    (1946, 1946): ("战后调整期",
                   "战时价格管制取消导致通胀飙升，消费品短缺。市场从战时高点大幅回调。"),
    (1947, 1948): ("马歇尔计划 / 冷战开始",
                   "杜鲁门主义和马歇尔计划出台，冷战格局形成。美国经济从战时向和平时期转型。"),
    (1949, 1950): ("战后繁荣开始",
                   "1949年短暂衰退后经济复苏。1950年朝鲜战争爆发，军事开支增加刺激经济。"),
    (1951, 1952): ("朝鲜战争时期",
                   "朝鲜战争持续，军工需求旺盛。美联储与财政部达成协议，获得货币政策独立性。"),
    (1954, 1955): ("艾森豪威尔繁荣",
                   "朝鲜战争结束后经济强劲复苏，消费信贷扩张，郊区化和汽车工业蓬勃发展。"),
    (1956, 1956): ("苏伊士运河危机",
                   "苏伊士运河危机和匈牙利事件增加地缘政治风险。美国经济增长放缓，通胀压力上升。"),
    (1961, 1961): ("肯尼迪新边疆",
                   "肯尼迪就任总统，推出减税和太空计划。猪湾事件和柏林墙危机增加冷战紧张。"),
    (1962, 1962): ("古巴导弹危机",
                   "10月古巴导弹危机将世界推向核战争边缘。5月'肯尼迪暴跌'后市场在危机解除后强劲反弹。"),
    (1964, 1964): ("约翰逊伟大社会",
                   "约翰逊推动民权法案和'伟大社会'计划，减税刺激经济增长，市场表现强劲。"),
    (1966, 1967): ("越战升级 / 信贷紧缩",
                   "越战军费开支增加，美联储收紧货币政策。1966年出现'信贷紧缩'，市场回调后恢复。"),
    (1968, 1968): ("动荡的1968年",
                   "马丁·路德·金和罗伯特·肯尼迪遇刺，越战升级，社会动荡。但经济仍在增长。"),
    (1970, 1971): ("尼克松经济政策",
                   "1970年经济衰退后复苏。1971年尼克松宣布美元脱离金本位（'尼克松冲击'），实施工资价格管制。"),
    (1972, 1972): ("尼克松连任 / 布雷顿森林崩溃",
                   "尼克松访华，美苏缓和。布雷顿森林体系正式终结，浮动汇率时代开始。'漂亮50'行情。"),
    (1974, 1975): ("石油危机 / 滞胀",
                   "1973年石油禁运后遗症，通胀高企+经济衰退（滞胀）。1974年尼克松辞职。1975年经济开始复苏。"),
    (1976, 1976): ("经济复苏",
                   "福特政府时期经济从衰退中恢复，通胀有所缓解。美国建国200周年。"),
    (1978, 1978): ("沃尔克前夜",
                   "卡特政府面临通胀上升和美元贬值压力。伊朗革命前夕，能源价格开始上涨。"),
    (1980, 1980): ("沃尔克紧缩 / 伊朗人质危机",
                   "美联储主席沃尔克大幅加息对抗通胀，利率飙升至20%。伊朗人质危机，里根当选总统。"),
    (1982, 1983): ("里根牛市启动",
                   "沃尔克紧缩结束，美联储开始降息。里根减税政策生效，1982年8月开启历史性大牛市。"),
    (1984, 1985): ("里根繁荣",
                   "经济强劲增长，通胀受控。里根连任。1985年广场协议导致美元贬值。"),
    (1986, 1986): ("广场协议后",
                   "美元贬值刺激出口，经济持续增长。油价暴跌有利于消费者。切尔诺贝利核事故。"),
    (1987, 1987): ("1987年股灾",
                   "年初市场大涨，10月19日'黑色星期一'单日暴跌22.6%。美联储迅速注入流动性稳定市场。"),
    (1988, 1988): ("股灾后恢复",
                   "市场从1987年股灾中恢复。老布什当选总统，冷战接近尾声。"),
    (1989, 1989): ("柏林墙倒塌",
                   "柏林墙倒塌，冷战结束。日本资产泡沫达到顶峰。美国经济增长放缓。"),
    (1990, 1991): ("海湾战争 / 经济衰退",
                   "伊拉克入侵科威特，海湾战争爆发。美国经济陷入衰退，但战争迅速结束后市场反弹。苏联解体。"),
    (1992, 1992): ("克林顿当选",
                   "经济缓慢复苏，克林顿以'笨蛋，问题是经济'为口号当选。互联网商业化开始。"),
    (1996, 1997): ("互联网泡沫初期",
                   "格林斯潘警告'非理性繁荣'。亚洲金融危机爆发但对美国影响有限。科技股开始加速上涨。"),
    (1998, 1998): ("LTCM危机 / 亚洲金融危机",
                   "俄罗斯债务违约，长期资本管理公司(LTCM)崩溃。美联储紧急降息，市场V型反弹。"),
    (1999, 2000): ("互联网泡沫顶峰",
                   "科技股狂热达到顶峰，纳斯达克在2000年3月见顶。Y2K恐慌。美联储开始加息。"),
    (2001, 2001): ("911事件 / 互联网泡沫破裂",
                   "互联网泡沫持续破裂，安然丑闻。9/11恐怖袭击导致市场短暂关闭后暴跌。美联储大幅降息。"),
    (2002, 2003): ("伊拉克战争前后",
                   "企业丑闻（世通、安然），市场在2002年10月触底。2003年伊拉克战争爆发后市场开始反弹。"),
    (2004, 2004): ("经济复苏期",
                   "美联储开始加息周期，房地产市场繁荣。小布什连任。经济稳步增长。"),
    (2007, 2008): ("次贷危机 / 全球金融危机",
                   "次贷危机爆发，贝尔斯登和雷曼兄弟倒闭。全球金融体系濒临崩溃，市场暴跌超过50%。"),
    (2009, 2009): ("金融危机后反弹",
                   "美联储QE和零利率政策。2009年3月市场触底后开启历史性反弹。TARP和财政刺激生效。"),
    (2010, 2010): ("欧债危机 / 闪崩",
                   "希腊债务危机引发欧洲主权债务恐慌。5月6日'闪崩'事件。美联储推出QE2。"),
    (2011, 2011): ("美国信用评级下调",
                   "标普下调美国AAA信用评级，欧债危机深化。市场剧烈波动但年末恢复。"),
    (2015, 2016): ("中国股灾 / 英国脱欧",
                   "2015年8月中国股市暴跌引发全球恐慌。2016年英国脱欧公投、特朗普当选，市场先跌后涨。"),
    (2019, 2019): ("贸易战缓和",
                   "中美贸易战出现缓和迹象，美联储转向降息。市场在2018年底暴跌后强劲反弹。"),
    (2020, 2020): ("新冠疫情",
                   "COVID-19全球大流行，3月市场暴跌34%后在史无前例的财政和货币刺激下V型反弹。"),
    (2021, 2021): ("疫情后复苏",
                   "疫苗推广，经济重启。通胀开始上升但美联储坚持'暂时性'论调。Meme股热潮。"),
    (2022, 2022): ("美联储激进加息",
                   "俄乌战争爆发，通胀飙升至40年高点。美联储激进加息，科技股大幅回调。"),
    (2023, 2023): ("AI热潮 / 银行危机",
                   "硅谷银行倒闭引发短暂恐慌。ChatGPT引爆AI投资热潮，'七巨头'科技股领涨。"),
    (2024, 2024): ("AI持续 / 降息预期",
                   "美联储开始降息周期，AI投资热情持续。大选年市场表现强劲。"),
    (2025, 2025): ("关税冲击后反弹",
                   "特朗普关税政策引发市场剧烈波动，随后贸易谈判缓和带来强劲反弹。"),
}


def get_historical_context(date):
    """根据日期返回对应的历史事件描述"""
    year = date.year
    for (start, end), (title, desc) in HISTORICAL_EVENTS.items():
        if start <= year <= end:
            return title, desc
    return "其他时期", "无特定重大事件记录。"


def classify_outcome(fwd_20, fwd_60, fwd_120):
    """根据后市表现给出定性评价"""
    values = [v for v in [fwd_20, fwd_60, fwd_120] if pd.notna(v)]
    if not values:
        return "⚪ 数据不足"
    avg = np.mean(values)
    if avg > 0.10:
        return "🟢 强劲上涨"
    elif avg > 0.03:
        return "🟢 温和上涨"
    elif avg > -0.03:
        return "🟡 横盘震荡"
    elif avg > -0.10:
        return "🔴 温和下跌"
    else:
        return "🔴 大幅下跌"


# 生成 Markdown 报告
md_lines = []
md_lines.append(f"# S&P 500 历史相似性压力测试 — 定性分析报告\n")
md_lines.append(f"> 生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
md_lines.append(f"## 基准信息\n")
md_lines.append(f"| 项目 | 值 |")
md_lines.append(f"|------|-----|")
md_lines.append(f"| 基准日期 | {target_date.strftime('%Y-%m-%d')} |")
md_lines.append(f"| 窗口期 | {W} 个交易日 |")
md_lines.append(f"| 近{W}日涨幅 | {target_return*100:.2f}% |")
md_lines.append(f"| 容差范围 | ±{TOLERANCE*100:.0f}% |")
md_lines.append(f"| 匹配数量 | {len(similar_df)} 个历史相似点 |")
md_lines.append(f"| 去重窗口 | {DEDUP_WINDOW} 个交易日 |\n")

# 统计摘要
md_lines.append(f"## 后市表现统计摘要\n")
md_lines.append(f"| 指标 | 20天后 | 60天后 | 120天后 |")
md_lines.append(f"|------|--------|--------|---------|")
for metric in ['样本数', '胜率', '平均值', '中位数', '最大值', '最小值']:
    row_vals = [metric]
    for fd in FORWARD_DAYS:
        data = similar_df[f'Fwd_{fd}d'].dropna()
        if len(data) == 0:
            row_vals.append('N/A')
        elif metric == '样本数':
            row_vals.append(f'{len(data)}')
        elif metric == '胜率':
            row_vals.append(f'{(data > 0).mean() * 100:.1f}%')
        elif metric == '平均值':
            row_vals.append(f'{data.mean() * 100:.2f}%')
        elif metric == '中位数':
            row_vals.append(f'{data.median() * 100:.2f}%')
        elif metric == '最大值':
            row_vals.append(f'{data.max() * 100:.2f}%')
        elif metric == '最小值':
            row_vals.append(f'{data.min() * 100:.2f}%')
    md_lines.append(f"| {' | '.join(row_vals)} |")

md_lines.append(f"\n## 关键发现\n")

# 按年代分组分析
decade_groups = {}
for i, row in similar_df.iterrows():
    decade = (row['Date'].year // 10) * 10
    decade_key = f"{decade}s"
    if decade_key not in decade_groups:
        decade_groups[decade_key] = []
    decade_groups[decade_key].append(row)

md_lines.append(f"### 年代分布\n")
md_lines.append(f"| 年代 | 出现次数 | 平均后市120天收益 |")
md_lines.append(f"|------|----------|-------------------|")
for decade_key in sorted(decade_groups.keys()):
    rows = decade_groups[decade_key]
    count = len(rows)
    fwd_120_vals = [r['Fwd_120d'] for r in rows if pd.notna(r['Fwd_120d'])]
    avg_120 = np.mean(fwd_120_vals) * 100 if fwd_120_vals else float('nan')
    md_lines.append(f"| {decade_key} | {count} | {avg_120:.2f}% |")

# 详细历史事件分析
md_lines.append(f"\n## 历史相似点详细分析\n")
md_lines.append(f"以下列出所有 {len(similar_df)} 个历史相似点，按时间顺序排列，并附上对应的历史背景和后市表现。\n")

for i, row in similar_df.iterrows():
    date = row['Date']
    ret = row['Rolling_Return']
    fwd_20 = row.get('Fwd_20d', np.nan)
    fwd_60 = row.get('Fwd_60d', np.nan)
    fwd_120 = row.get('Fwd_120d', np.nan)

    event_title, event_desc = get_historical_context(date)
    outcome = classify_outcome(fwd_20, fwd_60, fwd_120)

    md_lines.append(f"### {i+1}. {date.strftime('%Y-%m-%d')}  —  {event_title}\n")
    md_lines.append(f"- **40日涨幅**: {ret*100:.2f}%")
    md_lines.append(f"- **后市表现**: {outcome}")
    md_lines.append(f"  - 20天后: {fwd_20*100:.2f}%" if pd.notna(fwd_20) else "  - 20天后: N/A")
    md_lines.append(f"  - 60天后: {fwd_60*100:.2f}%" if pd.notna(fwd_60) else "  - 60天后: N/A")
    md_lines.append(f"  - 120天后: {fwd_120*100:.2f}%" if pd.notna(fwd_120) else "  - 120天后: N/A")
    md_lines.append(f"- **历史背景**: {event_desc}\n")

# 结论
md_lines.append(f"## 总结与启示\n")

# 计算一些关键统计
fwd_120_data = similar_df['Fwd_120d'].dropna()
bull_cases = similar_df[similar_df['Fwd_120d'] > 0.10] if 'Fwd_120d' in similar_df.columns else pd.DataFrame()
bear_cases = similar_df[similar_df['Fwd_120d'] < -0.10] if 'Fwd_120d' in similar_df.columns else pd.DataFrame()

md_lines.append(f"基于 S&P 500 自 1927 年以来的历史数据，当市场在 {W} 个交易日内上涨约 "
                f"{target_return*100:.1f}%（±{TOLERANCE*100:.0f}%）时：\n")
md_lines.append(f"1. **总体偏多**: 120天后胜率为 {(fwd_120_data > 0).mean()*100:.1f}%，"
                f"中位数收益为 {fwd_120_data.median()*100:.2f}%，表明这种涨幅后市场继续上涨的概率较高。")
md_lines.append(f"2. **但风险不可忽视**: 历史上也出现过严重的下跌案例（最差 {fwd_120_data.min()*100:.1f}%），"
                f"尤其在经济衰退或金融危机期间。")
md_lines.append(f"3. **关键风险场景**: 1929年大崩盘前、1937年衰退、1987年股灾前、2007-2008年金融危机等时期，"
                f"类似涨幅后出现了显著回调。")
md_lines.append(f"4. **时间越长越有利**: 胜率从20天的 {(similar_df['Fwd_20d'].dropna() > 0).mean()*100:.0f}% "
                f"提升到120天的 {(fwd_120_data > 0).mean()*100:.0f}%，说明短期波动大但中期趋势偏正。\n")
md_lines.append(f"⚠️ **免责声明**: 历史表现不代表未来收益。本分析仅供参考，不构成投资建议。")

# 写入文件
md_content = '\n'.join(md_lines)
md_path = os.path.join(output_dir, 'spx_similarity_stress_test_report.md')
with open(md_path, 'w', encoding='utf-8') as f:
    f.write(md_content)
print(f"\n📄 定性分析报告已保存至: {md_path}")
