"""CSV and bilingual static HTML report generation."""

from __future__ import annotations

import csv
import html
from datetime import date
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "source",
    "title",
    "url",
    "date",
    "score",
    "comments",
    "pain_keywords",
    "relevance_keywords",
    "is_product_opportunity",
    "pain_summary",
    "current_workaround",
    "target_user",
    "product_idea",
    "pay_signal",
    "competition",
    "opportunity_score",
    "reason",
]

LEVEL_LABELS = {
    "high": ("high", "高"),
    "medium": ("medium", "中"),
    "low": ("low", "低"),
}


def generate_csv_report(analyzed_posts: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for post in analyzed_posts:
            writer.writerow(post)
    return path


def generate_html_report(
    analyzed_posts: list[dict[str, Any]],
    output_path: str | Path,
    *,
    report_date: str | None = None,
    min_score: int = 6,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = build_report_document(
        analyzed_posts,
        report_date=report_date or date.today().isoformat(),
        min_score=min_score,
        index_href="index.html",
        csv_href="opportunities.csv",
    )
    path.write_text(document, encoding="utf-8")
    print(f"Generated report: {path}")
    return path


def generate_report_site(
    analyzed_posts: list[dict[str, Any]],
    output_dir: str | Path,
    *,
    report_date: str | None = None,
    min_score: int = 6,
    history_limit: int = 30,
) -> dict[str, Path]:
    root = Path(output_dir)
    reports_dir = root / "reports"
    root.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    current_date = report_date or date.today().isoformat()
    report_document = build_report_document(
        analyzed_posts,
        report_date=current_date,
        min_score=min_score,
        index_href="../index.html",
        csv_href="../opportunities.csv",
    )
    archive_path = reports_dir / f"{current_date}.html"
    archive_path.write_text(report_document, encoding="utf-8")

    latest_document = build_report_document(
        analyzed_posts,
        report_date=current_date,
        min_score=min_score,
        index_href="index.html",
        csv_href="opportunities.csv",
    )
    latest_path = root / "latest.html"
    report_path = root / "report.html"
    latest_path.write_text(latest_document, encoding="utf-8")
    report_path.write_text(latest_document, encoding="utf-8")

    index_path = root / "index.html"
    index_path.write_text(
        build_index_document(root, current_date=current_date, history_limit=history_limit),
        encoding="utf-8",
    )

    print(f"Generated static report site at {root}")
    return {
        "index_path": index_path,
        "latest_path": latest_path,
        "report_path": report_path,
        "archive_path": archive_path,
    }


def build_report_document(
    analyzed_posts: list[dict[str, Any]],
    *,
    report_date: str,
    min_score: int = 6,
    index_href: str = "index.html",
    csv_href: str = "opportunities.csv",
) -> str:
    high_value = [
        post
        for post in analyzed_posts
        if isinstance(post.get("opportunity_score"), int) and post["opportunity_score"] >= min_score
    ]
    high_value.sort(key=lambda item: item.get("opportunity_score", 0), reverse=True)
    cards_html = "\n".join(_render_card(post) for post in high_value)
    if not cards_html:
        cards_html = (
            '<section class="empty">'
            f"{_dual('No high-value opportunities found in this run.', '本次运行未发现高价值机会。')}"
            "</section>"
        )

    stats = _report_stats(high_value, analyzed_posts)
    return f"""<!doctype html>
<html lang="zh-CN" data-lang="zh" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Micro SaaS Radar Report</title>
  {_shared_styles()}
</head>
<body>
  <header class="header">
    <div class="brand">
      <div class="radar-mark" aria-hidden="true">
        <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="15" cy="15" r="12" stroke="currentColor" stroke-width="2"/>
          <circle cx="15" cy="15" r="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 2"/>
          <circle cx="15" cy="15" r="2.5" fill="currentColor"/>
          <path d="M15 3V7M25.4 9L21.9 11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      </div>
      <div>
        <h1>{_dual('Micro SaaS Radar Report', 'Micro SaaS 需求雷达')}</h1>
        <p>{_dual('Automated scan of real user pain signals', '自动扫描真实用户痛点')}</p>
      </div>
    </div>
    <div class="header-actions">
      <span class="updated">{_dual('Updated', '更新于')} {_e(report_date)}</span>
      <a class="header-link" href="{_attr(index_href)}">{_dual('History', '历史')}</a>
      <a class="header-link" href="{_attr(csv_href)}">CSV</a>
      {_language_toggle()}
      <button class="theme-btn" type="button" data-theme-toggle aria-label="Toggle theme">◐</button>
    </div>
  </header>
  <section class="stats-bar" aria-label="Report statistics">
    {_render_stat(stats['signals'], 'Pain signals', '痛点信号')}
    {_render_stat(stats['high_pay'], 'High pay intent', '高付费意愿')}
    {_render_stat(stats['low_comp'], 'Low competition', '低竞争机会')}
    {_render_stat(stats['avg_score'], 'Avg opportunity', '平均机会分')}
    {_render_stat(stats['sources'], 'Sources', '数据来源')}
  </section>
  <section class="filters" aria-label="Opportunity filters">
    <span class="filter-label">{_dual('Filter:', '筛选：')}</span>
    <button class="filter-btn active" type="button" data-filter="all">{_dual('All', '全部')}</button>
    <button class="filter-btn" type="button" data-filter="high-pay">{_dual('High pay intent', '高付费意愿')}</button>
    <button class="filter-btn" type="button" data-filter="low-comp">{_dual('Low competition', '低竞争')}</button>
    <button class="filter-btn" type="button" data-filter="score-8">{_dual('8+ score', '8分以上')}</button>
    <button class="filter-btn" type="button" data-filter="score-6">{_dual('6+ score', '6分以上')}</button>
  </section>
  <main>
    <section class="grid" id="cards-grid">
      {cards_html}
    </section>
  </main>
  <footer class="footer">
    {_dual('Generated by Micro SaaS Radar. Use filters to triage opportunities quickly.', '由 Micro SaaS Radar 生成。使用筛选器快速定位机会。')}
  </footer>
  {_page_script()}
</body>
</html>
"""


def build_index_document(output_dir: Path, *, current_date: str, history_limit: int = 30) -> str:
    reports_dir = output_dir / "reports"
    reports = sorted(reports_dir.glob("*.html"), reverse=True)[:history_limit]
    rows = "\n".join(
        f'<li><a href="reports/{_attr(report.name)}">{_e(report.stem)}</a></li>' for report in reports
    )
    if not rows:
        rows = f'<li class="muted">{_dual("No archived reports yet.", "暂无归档报告。")}</li>'
    return f"""<!doctype html>
<html lang="zh-CN" data-lang="zh" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Micro SaaS Radar</title>
  {_shared_styles(max_width=900)}
</head>
<body>
  <header class="header">
    <div class="brand">
      <div class="radar-mark" aria-hidden="true">
        <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="15" cy="15" r="12" stroke="currentColor" stroke-width="2"/>
          <circle cx="15" cy="15" r="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 2"/>
          <circle cx="15" cy="15" r="2.5" fill="currentColor"/>
        </svg>
      </div>
      <div>
        <h1>Micro SaaS Radar</h1>
        <p>{_dual('Latest report date:', '最新报告日期：')} {_e(current_date)}</p>
      </div>
    </div>
    <div class="header-actions">
      {_language_toggle()}
      <button class="theme-btn" type="button" data-theme-toggle aria-label="Toggle theme">◐</button>
    </div>
  </header>
  <main class="index-main">
    <section class="actions">
      <a class="action-card" href="latest.html">{_dual('Open latest report', '打开最新报告')}</a>
      <a class="action-card" href="opportunities.csv">{_dual('Download CSV', '下载 CSV')}</a>
    </section>
    <h2>{_dual('Daily archive', '日报归档')}</h2>
    <ul class="archive-list">
      {rows}
    </ul>
  </main>
  {_page_script()}
</body>
</html>
"""


def _render_card(post: dict[str, Any]) -> str:
    score = int(post.get("opportunity_score") or 0)
    pay = _level_key(post.get("pay_signal"))
    competition = _level_key(post.get("competition"))
    comments = int(post.get("comments") or 0)
    source_score = int(post.get("score") or 0)
    pain_keywords = _split_keywords(post.get("pain_keywords"))
    relevance_keywords = _split_keywords(post.get("relevance_keywords"))
    title = str(post.get("title", ""))
    date_text = str(post.get("date", ""))
    source = _source_short_name(str(post.get("source", "")))
    workaround = (
        _e(post.get("current_workaround"))
        if post.get("current_workaround")
        else _dual("None identified", "未识别")
    )
    return f"""
      <article class="card" data-score="{score}" data-pay="{_attr(pay)}" data-comp="{_attr(competition)}">
        <div class="card-header">
          <span class="score-badge score-{_score_tier(score)}">{_dual(f'{score}/10', f'{score}/10')}</span>
          <div class="meta-right">
            <span class="source-tag">{_e(source)}</span>
            <span class="date-tag">{_e(date_text)}</span>
          </div>
        </div>
        <h2 class="card-title"><a href="{_attr(post.get("url", "#"))}" target="_blank" rel="noopener noreferrer">{_e(title[:150])}</a></h2>
        <div class="insight-box pain-box">
          <span class="box-icon" aria-hidden="true">!</span>
          <span>{_e(post.get("pain_summary", ""))}</span>
        </div>
        <div class="insight-box product-box">
          <span class="box-icon" aria-hidden="true">↗</span>
          <span>{_e(post.get("product_idea", ""))}</span>
        </div>
        <div class="badges-row">
          {_tag(_dual('Pay:', '付费意愿：') + ' ' + _level_label(pay), f"pay-{pay}")}
          {_tag(_dual('Competition:', '竞争：') + ' ' + _level_label(competition), f"comp-{competition}")}
          {_tag(_dual(f'{comments} comments', f'{comments} 条评论'), 'neutral')}
          {_tag(_dual(f'{source_score} source score', f'{source_score} 原站分'), 'neutral')}
          {_tag(_dual('User:', '用户：') + ' ' + _e(post.get("target_user", "")), 'neutral wide')}
          {_tag(_dual('Workaround:', '替代方案：') + ' ' + workaround, 'neutral wide')}
        </div>
        {_keyword_row('Pain keywords', '痛点信号词', pain_keywords)}
        {_keyword_row('Relevance keywords', '相关词', relevance_keywords)}
        <div class="reason-row"><strong>{_dual('Reason:', '评分理由：')}</strong> {_e(post.get("reason", ""))}</div>
      </article>
    """


def _render_stat(value: object, en_label: str, zh_label: str) -> str:
    return f"""
    <div class="stat">
      <span class="stat-num">{_e(value)}</span>
      <span class="stat-label">{_dual(en_label, zh_label)}</span>
    </div>
    """


def _report_stats(high_value: list[dict[str, Any]], analyzed_posts: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [int(post.get("opportunity_score") or 0) for post in high_value]
    sources = sorted(
        {
            _source_short_name(str(post.get("source") or ""))
            for post in high_value
            if post.get("source")
        }
    )
    return {
        "signals": len(analyzed_posts),
        "high_pay": sum(1 for post in high_value if _level_key(post.get("pay_signal")) == "high"),
        "low_comp": sum(1 for post in high_value if _level_key(post.get("competition")) == "low"),
        "avg_score": f"{(sum(scores) / len(scores)):.1f}" if scores else "0.0",
        "sources": ", ".join(sources) or "-",
    }


def _shared_styles(*, max_width: int = 1400) -> str:
    return f"""<style>
    :root {{
      color-scheme: light dark;
      --bg: #f7f6f2;
      --surface: #f9f8f5;
      --surface2: #ffffff;
      --border: #dcd9d5;
      --text: #28251d;
      --muted: #77746d;
      --faint: #aaa7a0;
      --primary: #01696f;
      --primary-strong: #0c4e54;
      --shadow: 0 1px 3px rgb(40 37 29 / 0.07), 0 4px 16px rgb(40 37 29 / 0.05);
      --r: 8px;
    }}
    html[data-theme="dark"] {{
      --bg: #171614;
      --surface: #1c1b19;
      --surface2: #242321;
      --border: #3b3936;
      --text: #e4e2de;
      --muted: #97938d;
      --faint: #67625e;
      --primary: #4f98a3;
      --primary-strong: #74c8d2;
      --shadow: 0 1px 3px rgb(0 0 0 / 0.34), 0 4px 20px rgb(0 0 0 / 0.22);
    }}
    html[data-lang="zh"] .lang-en,
    html[data-lang="en"] .lang-zh {{
      display: none;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    a {{
      color: var(--primary-strong);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .header {{
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 18px max(20px, calc((100vw - {max_width}px) / 2));
      background: color-mix(in srgb, var(--surface) 94%, transparent);
      border-bottom: 1px solid var(--border);
      backdrop-filter: blur(12px);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 250px;
    }}
    .radar-mark {{
      color: var(--primary);
      display: grid;
      place-items: center;
      flex: 0 0 auto;
    }}
    h1 {{
      margin: 0;
      color: var(--text);
      font-size: 18px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .brand p {{
      margin: 3px 0 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .header-actions {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .updated {{
      color: var(--faint);
      font-size: 12px;
    }}
    .header-link {{
      color: var(--muted);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
    }}
    .header-link:hover {{
      border-color: var(--primary);
      color: var(--primary-strong);
      text-decoration: none;
    }}
    .language-toggle {{
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--border);
      border-radius: var(--r);
      overflow: hidden;
    }}
    .language-toggle button,
    .theme-btn,
    .filter-btn {{
      appearance: none;
      border: 0;
      font: inherit;
      cursor: pointer;
    }}
    .language-toggle button {{
      background: transparent;
      color: var(--muted);
      padding: 6px 10px;
      font-size: 12px;
    }}
    .language-toggle button[aria-pressed="true"] {{
      background: var(--primary);
      color: white;
      font-weight: 800;
    }}
    .theme-btn {{
      background: transparent;
      color: var(--muted);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 6px 10px;
    }}
    .stats-bar {{
      display: flex;
      gap: clamp(20px, 4vw, 58px);
      flex-wrap: wrap;
      padding: 14px max(20px, calc((100vw - {max_width}px) / 2));
      background: var(--primary);
      color: white;
    }}
    .stat {{
      min-width: 90px;
      display: grid;
      gap: 1px;
    }}
    .stat-num {{
      font-size: 22px;
      font-weight: 850;
      line-height: 1.1;
      letter-spacing: 0;
    }}
    .stat-label {{
      font-size: 12px;
      opacity: 0.8;
      font-weight: 700;
    }}
    .filters {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      padding: 14px max(20px, calc((100vw - {max_width}px) / 2));
      background: var(--surface);
      border-bottom: 1px solid var(--border);
    }}
    .filter-label {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    .filter-btn {{
      padding: 7px 14px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--muted);
      font-size: 13px;
      transition: background 0.18s, color 0.18s, border-color 0.18s;
    }}
    .filter-btn:hover,
    .filter-btn.active {{
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }}
    main {{
      max-width: {max_width}px;
      margin: 0 auto;
      padding: 24px 20px 10px;
    }}
    .index-main {{
      max-width: 900px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(390px, 100%), 1fr));
      gap: 20px;
    }}
    .card {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 100%;
      padding: 20px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: var(--r);
      box-shadow: var(--shadow);
      transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
    }}
    .card:hover {{
      border-color: color-mix(in srgb, var(--primary) 52%, var(--border));
      box-shadow: 0 8px 26px rgb(1 105 111 / 0.16);
      transform: translateY(-1px);
    }}
    .card.is-hidden {{
      display: none;
    }}
    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .score-badge,
    .source-tag,
    .date-tag,
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      white-space: nowrap;
    }}
    .score-badge {{
      padding: 5px 10px;
      font-size: 14px;
      font-weight: 850;
      border: 1px solid;
    }}
    .score-high {{
      color: #22c55e;
      background: rgb(34 197 94 / 0.13);
      border-color: rgb(34 197 94 / 0.35);
    }}
    .score-mid {{
      color: #f59e0b;
      background: rgb(245 158 11 / 0.13);
      border-color: rgb(245 158 11 / 0.35);
    }}
    .score-low {{
      color: #ef4444;
      background: rgb(239 68 68 / 0.12);
      border-color: rgb(239 68 68 / 0.32);
    }}
    .meta-right {{
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .source-tag {{
      padding: 4px 10px;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--muted);
      font-size: 12px;
    }}
    .date-tag {{
      color: var(--faint);
      font-size: 12px;
    }}
    .card-title {{
      margin: 0;
      font-size: 17px;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    .card-title a {{
      color: var(--text);
    }}
    .card-title a:hover {{
      color: var(--primary-strong);
      text-decoration: none;
    }}
    .insight-box {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 11px 12px;
      border-radius: 6px;
      background: var(--bg);
      color: var(--muted);
      font-size: 14px;
    }}
    .box-icon {{
      display: grid;
      place-items: center;
      width: 20px;
      height: 20px;
      flex: 0 0 auto;
      border-radius: 50%;
      background: color-mix(in srgb, var(--primary) 18%, transparent);
      color: var(--primary-strong);
      font-weight: 900;
      line-height: 1;
    }}
    .badges-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .badge {{
      max-width: 100%;
      padding: 5px 10px;
      border: 1px solid var(--border);
      font-size: 12px;
      font-weight: 750;
      color: var(--muted);
      background: var(--bg);
    }}
    .badge.wide {{
      white-space: normal;
    }}
    .pay-high,
    .comp-low {{
      color: #22c55e;
      background: rgb(34 197 94 / 0.12);
      border-color: rgb(34 197 94 / 0.30);
    }}
    .pay-medium,
    .comp-medium {{
      color: #f59e0b;
      background: rgb(245 158 11 / 0.12);
      border-color: rgb(245 158 11 / 0.30);
    }}
    .pay-low,
    .comp-high {{
      color: #ef4444;
      background: rgb(239 68 68 / 0.11);
      border-color: rgb(239 68 68 / 0.28);
    }}
    .keyword-row,
    .reason-row {{
      color: var(--faint);
      font-size: 12px;
    }}
    .keyword-row em {{
      color: var(--muted);
      font-style: normal;
    }}
    .reason-row {{
      border-top: 1px solid var(--border);
      padding-top: 10px;
      line-height: 1.5;
    }}
    .empty {{
      grid-column: 1 / -1;
      padding: 60px 24px;
      text-align: center;
      color: var(--muted);
      border: 1px solid var(--border);
      border-radius: var(--r);
      background: var(--surface2);
    }}
    .footer {{
      padding: 28px 20px 34px;
      text-align: center;
      color: var(--faint);
      font-size: 13px;
    }}
    .actions {{
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      margin: 24px 0;
    }}
    .action-card,
    .archive-list li {{
      display: block;
      padding: 14px 16px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: var(--r);
      box-shadow: var(--shadow);
    }}
    .archive-list {{
      list-style: none;
      padding: 0;
      display: grid;
      gap: 10px;
    }}
    .muted {{
      color: var(--muted);
    }}
    @media (max-width: 720px) {{
      .header {{
        position: static;
        align-items: flex-start;
      }}
      .header-actions {{
        justify-content: flex-start;
      }}
      .stats-bar {{
        gap: 18px;
      }}
      .stat {{
        min-width: 120px;
      }}
    }}
  </style>"""


def _page_script() -> str:
    return """<script>
    (() => {
      const root = document.documentElement;
      const languageButtons = Array.from(document.querySelectorAll("[data-set-lang]"));
      const themeButton = document.querySelector("[data-theme-toggle]");
      const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
      const cards = Array.from(document.querySelectorAll(".card[data-score]"));

      const setLanguage = (lang) => {
        const normalized = lang === "en" ? "en" : "zh";
        root.dataset.lang = normalized;
        root.lang = normalized === "zh" ? "zh-CN" : "en";
        languageButtons.forEach((button) => {
          button.setAttribute("aria-pressed", String(button.dataset.setLang === normalized));
        });
        try {
          localStorage.setItem("microsaas-radar-language", normalized);
        } catch (error) {}
      };

      const setTheme = (theme) => {
        const normalized = theme === "light" ? "light" : "dark";
        root.dataset.theme = normalized;
        if (themeButton) {
          themeButton.textContent = normalized === "dark" ? "☀" : "◐";
        }
        try {
          localStorage.setItem("microsaas-radar-theme", normalized);
        } catch (error) {}
      };

      const applyFilter = (filter) => {
        cards.forEach((card) => {
          const score = Number(card.dataset.score || "0");
          const pay = card.dataset.pay;
          const comp = card.dataset.comp;
          const visible =
            filter === "all" ||
            (filter === "high-pay" && pay === "high") ||
            (filter === "low-comp" && comp === "low") ||
            (filter === "score-8" && score >= 8) ||
            (filter === "score-6" && score >= 6);
          card.classList.toggle("is-hidden", !visible);
        });
        filterButtons.forEach((button) => {
          button.classList.toggle("active", button.dataset.filter === filter);
        });
      };

      languageButtons.forEach((button) => {
        button.addEventListener("click", () => setLanguage(button.dataset.setLang));
      });
      if (themeButton) {
        themeButton.addEventListener("click", () => {
          setTheme(root.dataset.theme === "dark" ? "light" : "dark");
        });
      }
      filterButtons.forEach((button) => {
        button.addEventListener("click", () => applyFilter(button.dataset.filter || "all"));
      });

      let savedLanguage = "zh";
      let savedTheme = "dark";
      try {
        savedLanguage = localStorage.getItem("microsaas-radar-language") || "zh";
        savedTheme = localStorage.getItem("microsaas-radar-theme") || "dark";
      } catch (error) {}
      setLanguage(savedLanguage);
      setTheme(savedTheme);
      applyFilter("all");
    })();
  </script>"""


def _language_toggle() -> str:
    return """<div class="language-toggle" aria-label="Language">
        <button type="button" data-set-lang="zh" aria-pressed="true">中文</button>
        <button type="button" data-set-lang="en" aria-pressed="false">English</button>
      </div>"""


def _tag(content: str, class_name: str) -> str:
    classes = " ".join(f"badge {class_name}".split())
    return f'<span class="{_attr(classes)}">{content}</span>'


def _keyword_row(en_label: str, zh_label: str, keywords: list[str]) -> str:
    if not keywords:
        return ""
    keyword_text = ", ".join(keywords)
    return (
        '<div class="keyword-row">'
        f"{_dual(en_label + ':', zh_label + '：')} <em>{_e(keyword_text)}</em>"
        "</div>"
    )


def _level_label(value: str) -> str:
    en, zh = LEVEL_LABELS.get(value, (value or "unknown", value or "未知"))
    return _dual(en, zh)


def _level_key(value: object) -> str:
    text = str(value or "").lower()
    if "high" in text:
        return "high"
    if "medium" in text:
        return "medium"
    if "low" in text:
        return "low"
    return "unknown"


def _score_tier(score: int) -> str:
    if score >= 8:
        return "high"
    if score >= 6:
        return "mid"
    return "low"


def _split_keywords(value: object) -> list[str]:
    return [keyword.strip() for keyword in str(value or "").split(",") if keyword.strip()]


def _source_short_name(source: str) -> str:
    normalized = source.lower()
    if source == "HackerNews" or normalized.startswith("hn"):
        return "HN"
    if normalized.startswith("reddit") or normalized.startswith("anysearch/reddit"):
        return "Reddit"
    if normalized.startswith("anysearch/x") or normalized.startswith("x/") or normalized.startswith("twitter"):
        return "X"
    if normalized.startswith("github") or normalized.startswith("anysearch/github"):
        return "GitHub"
    if normalized.startswith("trustmrr"):
        return "TrustMRR"
    return source


def _dual(en: str, zh: str) -> str:
    return f'<span class="lang-zh">{_e(zh)}</span><span class="lang-en">{_e(en)}</span>'


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=False)


def _attr(value: object) -> str:
    return html.escape(str(value or ""), quote=True)
