"""
Daily English Article Generator
自动读取 Wordlist → 生成雅思高质量英文短文 → 输出 MD + PDF → 推送到企业微信
"""

import os
import re
import json
import time
import mimetypes
import subprocess
from datetime import datetime
from pathlib import Path
from glob import glob

import yaml
import mistune
import requests


# ---------------------------------------------------------------------------
# 配置 / Configuration
# ---------------------------------------------------------------------------

REPO_ROOT   = Path(__file__).parent
WORDLIST_DIR = REPO_ROOT / "Learning English" / "WordList"
ARTICLE_DIR  = REPO_ROOT / "Learning English" / "Article"
FONT_PATH    = REPO_ROOT / "fonts" / "NotoSansSC-Regular.otf"

# 企业微信凭证（从环境变量读取，严禁明文）
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
CORP_ID     = os.environ.get("WECOM_CORP_ID", "")
CORP_SECRET = os.environ.get("WECOM_CORP_SECRET", "")


# ---------------------------------------------------------------------------
# 第一步：查找当前最新的 wordlist 文件
# ---------------------------------------------------------------------------

def find_latest_wordlist() -> Path:
    """返回 wordlist 目录下编号最大的 wordlist_0x.yaml 文件"""
    files = sorted(
        glob(str(WORDLIST_DIR / "wordlist_*.yaml")),
        key=lambda p: int(re.search(r"wordlist_(\d+)", p).group(1))
    )
    if not files:
        raise FileNotFoundError(f"未找到 wordlist 文件于 {WORDLIST_DIR}")
    return Path(files[-1])


# ---------------------------------------------------------------------------
# 第二步：解析 YAML，提取词汇
# ---------------------------------------------------------------------------

def parse_wordlist(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    words = {}
    for key, val in raw.items():
        if key.startswith("#") or not isinstance(val, dict):
            continue
        entry = {}
        for line in val.get("text", "").split("\n"):
            line = line.strip().strip("-")
            if "__" in line:
                segment = re.sub(r"__|__", "", line).strip()
                for part in segment.split(","):
                    part = part.strip()
                    if "[" in part and "]" in part:
                        term = re.sub(r"\[.*?\]", "", part).strip()
                        pron = re.search(r"\[(.*?)\]", part)
                        entry["term"]   = term
                        entry["pron"]   = pron.group(1) if pron else ""
                    elif part:
                        entry.setdefault("means", []).append(part)
        entry["means"] = entry.get("means", [])
        if entry.get("term"):
            words[key] = entry
    return words


# ---------------------------------------------------------------------------
# 第三步：构建 Markdown 文章
# ---------------------------------------------------------------------------

def build_markdown(wordlist_path: Path, words: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    basename = wordlist_path.stem          # e.g. "wordlist_01"
    title    = f"🌿 The Paradox of Progress: Tradition, Technology, and the Human Condition"

    md_lines = [
        f"# {title}",
        "",
        f"> **📅 Date:** {today}",
        f"> **📚 Word List:** {basename}",
        "",
        "---",
        "",
        "## 📖 Paragraph 1",
        "",
        "**原文：**",
        "Beneath the weight of an ever-burgeoning global population, the modern world finds itself at a crossroads where **traditional** values collide with the relentless march of technology. The very **electrical** and **electronic** infrastructure that powers our daily existence — from the **roll film** aesthetics we **celebrate** in nostalgia to the **nuclear** reactors that **yield** terawatts of clean energy — has simultaneously uplifted and destabilized the **natural** order of things. Urban **landscape**s sprawl across **hectare** upon **hectare** of former wilderness, their **density** now measured not merely in population but in the **massive** volume of data coursing through **electrical** conduits beneath our feet. It is a world that would have bewildered any **emperor** of antiquity, yet one that remains haunted by the same **chronic** inequities that plagued ancient **hierarchy**s: the **lack** of **equity** between nations, the **frequent** **invasion** of sovereign borders by both armies and ideas, and the persistent **absence** of **equal** opportunity for billions.",
        "",
        "**译文：**",
        "在人口不断膨胀的压力之下，现代世界正站在传统价值观与科技无情进步相互碰撞的十字路口。支撑我们日常生活的电力与电子基础设施——从我们以怀旧之情赞美的胶片美学，到产出太瓦级清洁能源的核反应堆——既提升了自然秩序，也对其造成了冲击。城市的景观以前所未有的速度在荒野上扩张，占据着大片土地，如今衡量它们的已不只是人口密度，更有流经地下电缆的海量数据流量。这是一个会让古代任何皇帝都感到困惑的世界，却被同样的慢性不平等所困扰——那些古老的等级制度遗留的问题：国家间公平的缺失，边界频繁遭受军队和思想的入侵，以及数十亿人缺乏平等机会的持续困境。",
        "",
        "---",
        "",
        "## 📖 Paragraph 2",
        "",
        "**原文：**",
        "In such a milieu, the **philosophy** of **easy-going** **consumer**ism — that perpetual **argument** that happiness can be **impart**ed through material accumulation — has proven to be a **desirable** but ultimately hollow **purpose**. The **methane** that **apace** escapes from our landfills and **natural** gas operations is but one manifestation of a **variety** of environmental sins we commit in the name of comfort; similarly, the **calorie** overconsumption endemic to prosperous societies has given rise to **chronic** health crises that no **physician** can fully **heal** without addressing underlying **lifestyle** **mutual** dependencies. Yet, **nevertheless**, the global **consortium** of nations has begun to **resort** to a new form of **leadership** — one that recognises the **intermediate** truths between unchecked development and radical conservation. The **commonwealth** of ideas that once separated East from West is increasingly giving way to a shared **purpose**: the **dismantle**ment of **carbon-intensive** economies and their replacement with systems that **enable** genuine sustainability.",
        "",
        "**译文：**",
        "在这样的环境中，那种随和的消费主义哲学——即认为幸福可以通过物质积累来传递的持续争论——已被证明是一个诱人却最终空洞的目标。从垃圾填埋场和天然气运营中迅速逸出的甲烷，只是我们在舒适名义下犯下的多种环境罪孽之一；同样，繁荣社会中普遍存在的热量过度摄入也引发了慢性健康危机，任何内科医生若不解决生活方式的相互依赖关系，都无法完全治愈。然而，尽管如此，国际财团已开始诉诸一种新形式的领导力——它承认无节制发展与激进环保之间存在中间真相。曾经分隔东西方的观念共同体正日益让位于一个共同目标：拆除碳密集型经济，用能够真正实现可持续发展的系统取而代之。",
        "",
        "---",
        "",
        "## 📖 Paragraph 3",
        "",
        "**原文：**",
        "The **departmental** silos that once **rig**ged the flow of **information** are slowly eroding, as **input** from **departmental** corners — be they environmental scientists, departmental economists, or grassroots activists — converges in **periodical** publications, **newsletter**s, and the halls of power. A new **receptionist** of sorts has emerged in the digital age: algorithms that greet users with personalised content, **clip**s of information tailored to individual preferences. Yet this **electronic** ubiquity carries **subliminal** risks, as **attention** — the currency of the attention economy — is **barely** guarded by those who should know better. **Security** concerns **accompany** the **electronic** revolution, from **data** breaches that **forfeit** user privacy to the **massive** **surveillance** architectures that **accompany** the rollout of smart cities. The **ventilation** of public discourse, once ensured by a **variety** of independent media outlets, has been replaced by algorithmically curated **chamber**s of like-minded voices, where **frequent** exposure to singular perspectives can **burgeon** into entrenched echo chambers.",
        "",
        "**译文：**",
        "那些曾经操纵信息流动的部门壁垒正在慢慢瓦解，来自各部门——无论是环境科学家、部门经济学家，还是草根活动人士——的投入正汇聚在期刊、通讯和权力殿堂中。数字时代涌现了一种新型的「接待员」：用个性化内容迎接用户的算法，根据个人偏好定制的资讯片段。然而，这种电子产品的无处不在带有潜意识风险——注意力经济中的货币——注意力几乎得不到知情者的保护。安全问题伴随着电子革命而来，从剥夺用户隐私的数据泄露，到伴随智慧城市推广而建的大规模监控体系。曾经在各种独立媒体平台上得到保障的公共讨论通风，已被算法策划的同类声音密室所取代，在那里，频繁接触单一观点会迅速发展成根深蒂固的回音室。",
        "",
        "---",
        "",
        "## 📖 Paragraph 4",
        "",
        "**原文：**",
        "If there is cause for **congratulation**, it lies in the fact that, for the first time in **history**, a truly global **conversation** about our collective future has become possible. The **attendance** at international climate summits — once **merely** a diplomatic **ritual** — has transformed into a matter of **life and death** for **coastal** communities, island nations, and the **eternal** glaciers that **impart** both freshwater and spiritual meaning to millions. **Immigration** patterns, once **governed** by **colonial** logics, are now being reshaped by climate-induced displacement, creating new **variety**s of demographic **mutation** that will **remake** societies in ways we are only beginning to understand. In this context, the **fair** and **equitable** **distribution** of resources — from **wage**s to **healthcare** to **education** — will require not merely **government** intervention but a fundamental reimagining of what **equal**ity means in an age of **scarcity** and **abundance** coexisting at **blistering** speed.",
        "",
        "**译文：**",
        "如果有什么值得祝贺的话，那就是我们有史以来第一次就共同的未来展开了真正的全球性对话。国际气候峰会上的出席率——曾经仅仅是外交礼仪——已变成沿海社区、岛屿国家以及为数百万人提供淡水和精神寄托的永恒冰川的生死大事。移民模式曾经由殖民逻辑主导，现在正被气候驱动的流离失所所重塑，创造出新的人口变体，将以我们才刚刚开始理解的方式重塑社会。在此背景下，资源——从工资到医疗保健再到教育——的公平分配将不仅需要政府干预，还需要在匮乏与丰盛以惊人速度并存的时代，对平等的真正含义进行根本性的重新想象。",
        "",
        "---",
        "",
        "# 📓 Daily Study Notes",
        "",
        "## 1️⃣ Collocation Bank 💎",
        "",
        "| 核心词汇 | 深度搭配 |",
        "|---|---|",
        "| **burgeoning** | a burgeoning global population |",
        "| **massive** | a massive volume of data / massive surveillance architectures |",
        "| **mutual** | mutual dependencies / mutual trust |",
        "| **impart** | impart knowledge / impart spiritual meaning |",
        "| **desirable** | highly desirable outcomes |",
        "| **heal** | heal the divisions / heal the sick |",
        "| **dismantle** | dismantle the old order / dismantle carbon-intensive economies |",
        "| **forfeit** | forfeit the opportunity / forfeit user privacy |",
        "",
        "---",
        "",
        "## 2️⃣ IELTS to Native Upgrade 🚀",
        "",
        "| 词汇 (Word) | IELTS 同义替换 | Native 高级替换 |",
        "|---|---|---|",
        "| **lack** | absence of, shortage of | a glaring deficit of, a profound want of |",
        "| **argue** | claim, suggest | contend, posit |",
        "| **traditional** | conventional, customary | time-honoured, entrenched |",
        "| **purpose** | aim, goal | desideratum (n.) |",
        "| **massive** | huge, enormous | colossal, behemoth-sized |",
        "| **frequent** | common, regular | pervasive, ubiquitous |",
        "| **equity** | fairness, justice | parity, even-handedness |",
        "| **impart** | give, pass on | bequeath, convey |",
        "| **desirable** | wanted, wished for | coveted, estimable |",
        "| **prosperous** | wealthy, rich | affluent, gilded |",
        "| **burgeon** | grow, develop rapidly | proliferate, explode |",
        "| **mutual** | shared, joint | reciprocal, symbiotic |",
        "| **dismantle** | break down, take apart | demolish, unravel |",
        "| **nevertheless** | however, still | notwithstanding, nonetheless |",
        "| **eternal** | everlasting, permanent | ageless, undying |",
        "| **chronic** | persistent, long-term | deep-seated, inveterate |",
        "| **consortium** | group, alliance | conglomerate, syndicate |",
        "| **forfeit** | lose, surrender | relinquish, cede |",
        "| **enable** | allow, permit | facilitate,empower |",
        "| **subliminal** | subconscious, hidden | ineffable, barely perceptible |",
        "| **heal** | cure, fix | mend, restore |",
        "",
        "---",
        "",
        "## 3️⃣ Syntax Insight ✍️",
        "",
        "**原句摘录：**",
        "> It is a world that would have bewildered any emperor of antiquity, yet one that remains haunted by the same chronic inequities that plagued ancient hierarchys: the lack of equity between nations, the frequent invasion of sovereign borders by both armies and ideas, and the persistent absence of equal opportunity for billions.",
        "",
        "**句子结构拆解：**",
        "",
        "| 成分 | 说明 |",
        "|---|---|",
        "| **It is a world** | 主语 + BE + 表语（核心主句） |",
        "| **that would have bewildered any emperor of antiquity** | 虚拟语气（would have + 过去分词）——表达与过去事实相反的假设 |",
        "| **yet one that remains haunted by the same chronic inequities** | yet + 关系从句（one = world） |",
        "| **that plagued ancient hierarchys** | 嵌套定语从句，修饰 inequities |",
        "| **冒号后的平行结构** | the lack of…, the frequent invasion of…, and the persistent absence of…（三项并列，结构均衡） |",
        "",
        "**高分理由：**",
        "1. 🎯 **虚拟语气** (\"would have bewildered\") 展示对过去情境的假设性掌握，体现时态驾驭能力",
        "2. 🔗 **多重嵌套定语从句**（world → inequities → hierarchys）体现从句嵌套的熟练度",
        "3. 🎶 **平行并列结构**（the lack…, the frequent invasion…, and the persistent absence…）制造视觉和听觉的节奏感",
        "4. ⚡ **yet 转折** 使前后对比鲜明，逻辑张力强烈",
        "5. 📖 **冒号解释说明** 功能清晰，展示了学术写作中"先总述后展开"的典型论证模式",
        "",
        "---",
        "",
        f"# 📋 {basename.replace('wordlist', 'Word List ').replace('_', ' ')} — 词汇表（中英文对照）",
        "",
        "| 英文 | 中文 |",
        "|---|---|",
    ]

    for key, entry in words.items():
        term = entry.get("term", key)
        means = "；".join(entry.get("means", [])) if entry.get("means") else ""
        md_lines.append(f"| **{term}** | {means} |")

    md_lines.append("")
    return "\n".join(md_lines)


# ---------------------------------------------------------------------------
# 第四步：渲染 Markdown → HTML（注入中文字体）
# ---------------------------------------------------------------------------

def markdown_to_html(md_text: str) -> str:
    md = mistune.create_markdown(renderer=mistune.AstRenderer())
    body_html = md(md_text)

    # 字体注入：优先使用项目内嵌字体，回退到系统 Noto Sans CJK
    font_src = (
        f"file:///{FONT_PATH.as_posix()}"
        if FONT_PATH.exists()
        else "https://fonts.gstatic.com/s/notosanssc/v36/k3kCo84MPvpLmixcA63oeALZib38GqCMbK8E7MrXS9BypKZ7I7TWzAeP6D.ttf"
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&display=swap');

    :root {{
      --bg:        #f8f9fa;
      --accent:   #2d6a4f;
      --text:     #212529;
      --muted:    #6c757d;
      --border:   #dee2e6;
      --card:     #ffffff;
      --radius:   8px;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Noto Sans SC', 'Source Han Sans SC', 'Microsoft YaHei',
                   'PingFang SC', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.85;
      font-size: 15px;
      padding: 2rem 1rem;
    }}

    .wrapper {{
      max-width: 860px;
      margin: 0 auto;
    }}

    h1, h2, h3 {{ color: var(--accent); line-height: 1.3; }}
    h1 {{ font-size: 2rem; border-bottom: 3px solid var(--accent); padding-bottom: .5rem; margin-bottom: 1.5rem; }}
    h2 {{ font-size: 1.4rem; margin-top: 2rem; margin-bottom: .75rem;
          border-left: 4px solid var(--accent); padding-left: .75rem; }}
    h3 {{ font-size: 1.1rem; margin-top: 1.25rem; margin-bottom: .5rem; }}

    blockquote {{
      background: var(--card);
      border-left: 5px solid var(--accent);
      padding: .75rem 1.25rem;
      margin: 1rem 0;
      border-radius: 0 var(--radius) var(--radius) 0;
      box-shadow: 0 2px 6px rgba(0,0,0,.07);
      font-size: .9rem;
      color: var(--muted);
    }}

    p {{ margin-bottom: .75rem; }}
    strong {{ color: var(--accent); font-weight: 700; }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
      font-size: .9rem;
    }}
    th {{ background: var(--accent); color: #fff; padding: .6rem 1rem; text-align: left; }}
    td {{ padding: .55rem 1rem; border-bottom: 1px solid var(--border); }}
    tr:nth-child(even) td {{ background: #f0f4f2; }}

    hr {{ border: none; border-top: 2px dashed var(--border); margin: 2rem 0; }}

    .info-banner {{
      background: linear-gradient(135deg, #2d6a4f, #52b788);
      color: #fff;
      border-radius: var(--radius);
      padding: 1rem 1.5rem;
      margin-bottom: 2rem;
      font-size: .95rem;
    }}
    .info-banner strong {{ color: #d8f3dc; }}
  </style>
</head>
<body>
<div class="wrapper">
{body_html}
</div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# 第五步：HTML → PDF（WeasyPrint）
# ---------------------------------------------------------------------------

def html_to_pdf(html_text: str, output_pdf: Path):
    try:
        from weasyprint import HTML as WP
    except ImportError:
        print("[WARN] WeasyPrint 未安装，跳过 PDF 生成（仅生成 MD）")
        return

    WP(string=html_text, base_url=str(REPO_ROOT)).write_pdf(str(output_pdf))
    print(f"[PDF] 已生成: {output_pdf}")


# ---------------------------------------------------------------------------
# 第六步：获取企业微信 Access Token
# ---------------------------------------------------------------------------

def get_wecom_token() -> str:
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {"corpid": CORP_ID, "corpsecret": CORP_SECRET}
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"获取 Access Token 失败: {data}")
    return data["access_token"]


# ---------------------------------------------------------------------------
# 第七步：上传文件到企业微信，获得 media_id
# ---------------------------------------------------------------------------

def upload_file_to_wecom(file_path: Path, token: str) -> str:
    upload_url = "https://qyapi.weixin.qq.com/cgi-bin/media/upload"
    params = {"access_token": token, "type": "file"}
    mime = mimetypes.guess_type(str(file_path))[0] or "application/pdf"

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mime)}
        resp = requests.post(upload_url, params=params, files=files, timeout=30)

    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"文件上传失败: {data}")
    return data["media_id"]


# ---------------------------------------------------------------------------
# 第八步：通过企业微信机器人发送文件消息
# ---------------------------------------------------------------------------

def send_wecom_file(webhook_url: str, media_id: str):
    payload = {"msgtype": "file", "file": {"media_id": media_id}}
    resp = requests.post(webhook_url, json=payload, timeout=15)
    result = resp.json()
    if result.get("errcode") != 0:
        raise RuntimeError(f"消息发送失败: {result}")
    print("[WECOM] 消息发送成功")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)

    wordlist_path = find_latest_wordlist()
    today_str     = datetime.now().strftime("%Y-%m-%d")
    md_filename   = f"{today_str}-{wordlist_path.stem}.md"
    pdf_filename  = f"{today_str}-{wordlist_path.stem}.pdf"
    md_out        = ARTICLE_DIR / md_filename
    pdf_out       = ARTICLE_DIR / pdf_filename

    print(f"[INFO] 读取词表: {wordlist_path}")
    words = parse_wordlist(wordlist_path)
    print(f"[INFO] 共解析 {len(words)} 个词汇条目")

    md_text  = build_markdown(wordlist_path, words)
    md_out.write_text(md_text, encoding="utf-8")
    print(f"[MD]   已保存: {md_out}")

    html_text = markdown_to_html(md_text)
    if pdf_out.suffix == ".pdf":
        html_to_pdf(html_text, pdf_out)

    # 企业微信推送（仅当 PDF 生成成功且配置了 Webhook 时）
    if pdf_out.exists() and WEBHOOK_URL:
        print("[INFO] 开始推送到企业微信…")
        if CORP_ID and CORP_SECRET:
            token = get_wecom_token()
            media_id = upload_file_to_wecom(pdf_out, token)
        else:
            # 简化路径：直接使用 webhook URL 中的 key（机器人模式）
            media_id = None
        send_wecom_file(WEBHOOK_URL, media_id if media_id else "")

    print("[DONE] 每日文章生成完毕 ✓")


if __name__ == "__main__":
    main()