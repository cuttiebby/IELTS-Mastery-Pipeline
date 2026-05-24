"""
Daily English Article Generator
Reads wordlist YAML → loads article content from JSON →
generates MD + PDF → pushes to WeChat Work
"""

import os
import re
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from glob import glob

import yaml
import mistune
import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT   = Path(__file__).parent
WORDLIST_DIR = REPO_ROOT / "Learning English" / "WordList"
ARTICLE_DIR  = REPO_ROOT / "Learning English" / "Article"
CONTENT_JSON = REPO_ROOT / "article_content.json"
FONT_PATH    = REPO_ROOT / "fonts" / "NotoSansSC-Regular.otf"

WEBHOOK_URL  = os.environ.get("WEBHOOK_URL", "")
CORP_ID      = os.environ.get("WECOM_CORP_ID", "")
CORP_SECRET  = os.environ.get("WECOM_CORP_SECRET", "")


# ---------------------------------------------------------------------------
# Step 1: Find latest wordlist file
# ---------------------------------------------------------------------------

def find_latest_wordlist() -> Path:
    files = sorted(
        glob(str(WORDLIST_DIR / "wordlist_*.yaml")),
        key=lambda p: int(re.search(r"wordlist_(\d+)", p).group(1))
    )
    if not files:
        raise FileNotFoundError(f"No wordlist found in {WORDLIST_DIR}")
    return Path(files[-1])


# ---------------------------------------------------------------------------
# Step 2: Parse wordlist YAML → extract vocabulary
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
            if "__" not in line:
                continue
            segment = re.sub(r"__|__", "", line).strip()
            for part in segment.split(","):
                part = part.strip()
                if "[" in part and "]" in part:
                    term = re.sub(r"\[.*?\]", "", part).strip()
                    pron = re.search(r"\[(.*?)\]", part)
                    entry["term"] = term
                    entry["pron"] = pron.group(1) if pron else ""
                elif part:
                    entry.setdefault("means", []).append(part)
        entry["means"] = entry.get("means", [])
        if entry.get("term"):
            words[key] = entry
    return words


# ---------------------------------------------------------------------------
# Step 3: Load article content from JSON
# ---------------------------------------------------------------------------

def load_article_content() -> dict:
    with open(CONTENT_JSON, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Step 4: Build Markdown from JSON content + wordlist
# ---------------------------------------------------------------------------

def build_markdown(wordlist_path: Path, words: dict, article: dict) -> str:
    today    = datetime.now().strftime("%Y-%m-%d")
    basename = wordlist_path.stem
    title    = article.get("title", "Daily English Article")

    lines = [
        f"# {title}",
        "",
        f"> **Date:** {today}",
        f"> **Word List:** {basename}",
        "",
        "---",
    ]

    for i, para in enumerate(article.get("paragraphs", []), 1):
        lines += [
            f"",
            f"## Paragraph {i}",
            "",
            "**原文：**",
            para["en"],
            "",
            "**译文：**",
            para["zh"],
            "",
            "---",
        ]

    # Study Notes
    notes = article.get("notes", {})
    lines += ["", "# Daily Study Notes", ""]

    # Collocation Bank
    lines += ["## Collocation Bank", ""]
    lines += ["| Word | Collocation |", "|---|---|"]
    for item in notes.get("collocation", []):
        lines.append(f"| **{item['word']}** | {item['phrase']} |")

    lines += ["", "", "---", ""]

    # IELTS to Native
    lines += ["## IELTS to Native Upgrade", ""]
    lines += ["| Word | IELTS | Native |", "|---|---|---|"]
    for item in notes.get("upgrades", []):
        lines.append(f"| **{item['word']}** | {item['ielts']} | {item['native']} |")

    lines += ["", "---", ""]

    # Syntax Insight
    lines += [
        "## Syntax Insight",
        "",
        "**原句摘录：**",
        "> It is a world that would have bewildered any emperor of antiquity, yet one that remains haunted by the same chronic inequities that plagued ancient hierarchys: the lack of equity between nations, the frequent invasion of sovereign borders by both armies and ideas, and the persistent absence of equal opportunity for billions.",
        "",
        "**句子结构拆解：**",
        "",
        "| Component | Description |",
        "|---|---|",
        "| It is a world | Main clause |",
        "| that would have bewildered any emperor of antiquity | Subjunctive mood (past contrary-to-fact) |",
        "| yet one that remains haunted by the same chronic inequities | yet + relative clause |",
        "| that plagued ancient hierarchys | Nested relative clause |",
        "| Parallel structure after colon | the lack of..., the frequent invasion of..., and the persistent absence of... |",
        "",
        "**高分理由：**",
        "1. **虚拟语气** (would have bewildered) demonstrates tense mastery",
        "2. **多重嵌套定语从句** (world → inequities → hierarchys) shows clause sophistication",
        "3. **平行并列结构** creates rhythmic momentum",
        "4. **yet 转折** sharpens logical contrast",
        "5. **冒号解释说明** follows the academic pattern of generalisation then elaboration",
        "",
        "---",
        "",
        f"# {basename.replace('wordlist', 'Word List ').replace('_', ' ')} — Vocabulary",
        "",
        "| English | Chinese |",
        "|---|---|",
    ]

    for key, entry in words.items():
        term  = entry.get("term", key)
        means = "；".join(entry.get("means", [])) if entry.get("means") else ""
        lines.append(f"| **{term}** | {means} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 5: Render Markdown → HTML with embedded font
# ---------------------------------------------------------------------------

def markdown_to_html(md_text: str) -> str:
    md     = mistune.create_markdown(renderer=mistune.AstRenderer())
    body   = md(md_text)

    font_src = (
        f"file:///{FONT_PATH.as_posix()}"
        if FONT_PATH.exists()
        else "https://fonts.gstatic.com/s/notosanssc/v40/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaG9_FnYw.ttf"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700&display=swap');

    :root {{
      --bg:      #f8f9fa;
      --accent:  #2d6a4f;
      --text:    #212529;
      --muted:   #6c757d;
      --border:  #dee2e6;
      --card:    #ffffff;
      --radius:  8px;
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

    .wrapper {{ max-width: 860px; margin: 0 auto; }}

    h1, h2, h3 {{ color: var(--accent); line-height: 1.3; }}
    h1 {{ font-size: 2rem; border-bottom: 3px solid var(--accent); padding-bottom: .5rem; margin-bottom: 1.5rem; }}
    h2 {{ font-size: 1.4rem; margin-top: 2rem; margin-bottom: .75rem;
          border-left: 4px solid var(--accent); padding-left: .75rem; }}

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

    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: .9rem; }}
    th {{ background: var(--accent); color: #fff; padding: .6rem 1rem; text-align: left; }}
    td {{ padding: .55rem 1rem; border-bottom: 1px solid var(--border); }}
    tr:nth-child(even) td {{ background: #f0f4f2; }}

    hr {{ border: none; border-top: 2px dashed var(--border); margin: 2rem 0; }}
  </style>
</head>
<body>
<div class="wrapper">{body}</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Step 6: HTML → PDF via WeasyPrint
# ---------------------------------------------------------------------------

def html_to_pdf(html_text: str, output_pdf: Path):
    try:
        from weasyprint import HTML as WP
    except ImportError:
        print("[WARN] WeasyPrint not installed, skipping PDF generation")
        return

    WP(string=html_text, base_url=str(REPO_ROOT)).write_pdf(str(output_pdf))
    print(f"[PDF] Generated: {output_pdf}")


# ---------------------------------------------------------------------------
# Step 7: WeCom Access Token
# ---------------------------------------------------------------------------

def get_wecom_token() -> str:
    url    = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    params = {"corpid": CORP_ID, "corpsecret": CORP_SECRET}
    resp   = requests.get(url, params=params, timeout=10)
    data   = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"Token error: {data}")
    return data["access_token"]


# ---------------------------------------------------------------------------
# Step 8: Upload file to WeCom → get media_id
# ---------------------------------------------------------------------------

def upload_file_to_wecom(file_path: Path, token: str) -> str:
    upload_url = "https://qyapi.weixin.qq.com/cgi-bin/media/upload"
    params     = {"access_token": token, "type": "file"}
    mime       = mimetypes.guess_type(str(file_path))[0] or "application/pdf"

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, mime)}
        resp  = requests.post(upload_url, params=params, files=files, timeout=30)

    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"Upload failed: {data}")
    return data["media_id"]


# ---------------------------------------------------------------------------
# Step 9: Send file message via WeCom
# ---------------------------------------------------------------------------

def send_wecom_file(webhook_url: str, media_id: str):
    payload = {"msgtype": "file", "file": {"media_id": media_id}}
    resp    = requests.post(webhook_url, json=payload, timeout=15)
    result  = resp.json()
    if result.get("errcode") != 0:
        raise RuntimeError(f"Send failed: {result}")
    print("[WECOM] Message sent successfully")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)

    wordlist_path = find_latest_wordlist()
    today_str     = datetime.now().strftime("%Y-%m-%d")
    md_out        = ARTICLE_DIR / f"{today_str}-{wordlist_path.stem}.md"
    pdf_out       = ARTICLE_DIR / f"{today_str}-{wordlist_path.stem}.pdf"

    print(f"[INFO] Reading wordlist: {wordlist_path}")
    words    = parse_wordlist(wordlist_path)
    article  = load_article_content()
    print(f"[INFO] Parsed {len(words)} words, loaded article content")

    md_text  = build_markdown(wordlist_path, words, article)
    md_out.write_text(md_text, encoding="utf-8")
    print(f"[MD] Saved: {md_out}")

    html = markdown_to_html(md_text)
    html_to_pdf(html, pdf_out)

    if pdf_out.exists() and WEBHOOK_URL:
        print("[INFO] Pushing to WeChat Work...")
        if CORP_ID and CORP_SECRET:
            token    = get_wecom_token()
            media_id = upload_file_to_wecom(pdf_out, token)
        else:
            media_id = None
        send_wecom_file(WEBHOOK_URL, media_id if media_id else "")

    print("[DONE] Daily article generation complete")


if __name__ == "__main__":
    main()