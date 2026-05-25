"""HTML rendering for downloadable reports (M7.1).

Mirrors the inline markdown renderer in ``frontend/src/components/report/ReportPanel.vue``
so the ``.html`` download is visually equivalent to the in-app preview.

Why a hand-rolled renderer instead of ``markdown-it`` / ``markdown2`` / ``mistune``:
the backend already emits a deterministic, narrow markdown subset (headings,
ordered/unordered lists, blockquotes, hr, bold, inline code). Pulling in a full
markdown library would add ~150-300 KB of code we don't use, and forces us to
keep the frontend renderer in sync with it. Two ~70-line renderers are easier
to keep aligned than one external dep with surface-area drift.

The output is a single self-contained HTML document with inlined CSS — users
can save it locally, attach it to email, or open it in a browser and use
"Print → Save as PDF" for a print-quality export. This sidesteps the wheel/GTK
pain of weasyprint and the haskell-binary dependency of pandoc.
"""

from __future__ import annotations

import re

from app.services.reliability_tier import LABEL_TO_SLUG as _LABEL_TO_SLUG

# ---------- inline + block converters ----------------------------------------


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_CODE_RE = re.compile(r"`([^`]+)`")
_LIST_PREFIX_RE = re.compile(r"^\s*-\s+")


def _inline(text: str) -> str:
    out = _escape_html(text)
    out = _BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _CODE_RE.sub(r"<code>\1</code>", out)
    return out


def markdown_to_html_fragment(md: str) -> str:
    """Convert deterministic backend markdown into an HTML fragment.

    Handles: ``# / ## / ###``, ``> ``, ``- ``, ``---``/``***``, ``**bold**``,
    inline code with backticks. Italic (``*x*`` / ``_x_``) is intentionally
    left as literal text — the backend renderer does not emit italics, and
    matching them risks false positives on the underscore-wrapped placeholder
    strings ("_未运行仿真_").
    """
    if not md:
        return ""

    lines = md.splitlines()
    out: list[str] = []
    in_list = False
    in_blockquote = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def close_quote() -> None:
        nonlocal in_blockquote
        if in_blockquote:
            out.append("</blockquote>")
            in_blockquote = False

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            close_list()
            close_quote()
            continue
        if line.startswith("### "):
            close_list()
            close_quote()
            out.append(f"<h3>{_inline(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            close_list()
            close_quote()
            out.append(f"<h2>{_inline(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            close_list()
            close_quote()
            out.append(f"<h1>{_inline(line[2:])}</h1>")
            continue
        if line == "---" or line == "***":
            close_list()
            close_quote()
            out.append("<hr />")
            continue
        if line.startswith("> "):
            close_list()
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            out.append(f"<p>{_inline(line[2:])}</p>")
            continue
        m = _LIST_PREFIX_RE.match(line)
        if m:
            close_quote()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line[m.end():])}</li>")
            continue
        close_list()
        close_quote()
        out.append(f"<p>{_inline(line)}</p>")

    close_list()
    close_quote()
    return "\n".join(out)


# ---------- print-mode structuring (Phase E) ---------------------------------
#
# The downloadable HTML is the printable artifact, so we add a thin post-pass
# that wraps each Phase D chapter into a ``<section>`` and tags well-known
# metric rows with stable ``metric-*`` classes. This is intentionally done
# AFTER ``markdown_to_html_fragment`` runs (and only inside the document
# wrapper) so the in-app preview, the per-section markdown contract tests,
# and the inline-HTML escaping behavior remain untouched.

# Map h2 chapter title (after stripping the leading enumeration prefix) to a
# CSS-friendly slug. Keys mirror the literal strings written by
# ``report_builder._render_markdown`` so adding a section there only requires
# adding an entry here.
_SECTION_SLUG: dict[str, str] = {
    "数据来源覆盖": "coverage",
    "风险评估": "risk",
    "舆情仿真摘要": "simulation",
    "预测拟合摘要": "forecast",
    "因果分析摘要": "causal",
    "决策建议": "recommendation",
    "证据链与置信度汇总": "evidence",
}

# Map list-item line prefix → metric key for the ``.metric-row`` class.
# Prefixes are matched as plain ASCII/CJK substrings against the rendered
# ``<li>`` inner text and must end with the fullwidth colon used by the
# backend renderer.
_METRIC_KEY: dict[str, str] = {
    "证据数量：": "evidence-count",
    "证据 ID：": "evidence-ids",
    "来源 Run：": "source-run",
    "图谱特征：": "kg-features",
    "图谱链接：": "kg-link",
    "置信度（最弱链）：": "reliability",
    "数据覆盖：": "coverage",
    "置信度：": "confidence",
    "优先级：": "priority",
    "标签：": "tags",
    "指标依据：": "metric-trace",
    "证据链：": "evidence-chain",
}

_H2_SPLIT_RE = re.compile(r"(<h2>.*?</h2>)", re.DOTALL)
_H2_INNER_RE = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)
_ENUM_PREFIX_RE = re.compile(r"^[一二三四五六七八九十百零]+、\s*")
_LI_METRIC_RE = re.compile(r"<li>([^<]+?：)")

# Match a metric-reliability ``<li>`` whose body carries the Chinese tier label
# emitted by ``report_builder._reliability_tier``. The body is intentionally
# constrained to ``[^<]`` so a future inline tag inside the row falls through
# untouched rather than getting misclassified.
_RELIABILITY_TIER_RE = re.compile(
    r'<li class="metric-row metric-reliability">([^<]*?等级\s*)(强|一般|弱|未知)([^<]*)</li>'
)
# Derived from the shared (label → slug) table in
# ``app.services.reliability_tier`` so the slug set never falls out of sync
# with the threshold logic. Adding a new tier requires editing exactly one
# place: ``reliability_tier.TIERS``.
_RELIABILITY_TIER_SLUG: dict[str, str] = dict(_LABEL_TO_SLUG)


def _section_slug_for(h2_text: str) -> str | None:
    """Return the section slug for an ``<h2>`` inner text.

    Strips the leading Chinese-numeral enumeration prefix (e.g. ``一、``)
    so chapter ordering changes in the markdown don't break the slug.
    """
    plain = _ENUM_PREFIX_RE.sub("", h2_text.strip())
    return _SECTION_SLUG.get(plain)


def _wrap_sections(fragment: str) -> str:
    """Wrap each ``<h2>...</h2>`` plus its following siblings into a
    ``<section class="report-section section-{slug}">`` element.

    Content before the first ``<h2>`` (project title, generation timestamp,
    leading ``<hr />``) stays at the top level. Content after the last
    ``<h2>`` is folded into that final section.
    """
    if "<h2>" not in fragment:
        return fragment

    parts = _H2_SPLIT_RE.split(fragment)
    out: list[str] = []
    if parts and parts[0]:
        out.append(parts[0].rstrip())

    i = 1
    while i < len(parts):
        h2 = parts[i]
        body = parts[i + 1] if (i + 1) < len(parts) else ""
        m = _H2_INNER_RE.match(h2)
        if not m:
            out.append(h2)
            if body:
                out.append(body)
            i += 2
            continue
        title = re.sub(r"<[^>]+>", "", m.group(1))
        slug = _section_slug_for(title)
        cls = "report-section"
        if slug:
            cls += f" section-{slug}"
        out.append(f'<section class="{cls}">')
        out.append(h2)
        body_clean = body.strip()
        if body_clean:
            out.append(body_clean)
        out.append("</section>")
        i += 2

    return "\n".join(out)


def _annotate_metric_rows(fragment: str) -> str:
    """Add ``class="metric-row metric-{key}"`` to ``<li>`` elements whose
    inner text starts with one of the well-known stable prefixes.

    The regex is bounded by ``[^<]`` so an ``<li>`` whose value starts with a
    bold/code wrapper (``<strong>``, ``<code>``) won't be misclassified.
    """

    def _sub(match: re.Match[str]) -> str:
        prefix = match.group(1)
        for needle, key in _METRIC_KEY.items():
            if prefix.startswith(needle):
                return f'<li class="metric-row metric-{key}">{prefix}'
        return match.group(0)

    return _LI_METRIC_RE.sub(_sub, fragment)


def _annotate_reliability_tier(fragment: str) -> str:
    """Append a ``metric-reliability-{strong|fair|weak|unknown}`` modifier
    class to the weakest-link reliability ``<li>``.

    The Chinese tier label is emitted by ``report_builder._reliability_tier``;
    here we mirror the same threshold-derived slug onto the rendered HTML so
    the print stylesheet can colour-code the row in line with the decision
    board chip's ``reliabilityColor`` (>=0.7 success / >=0.4 warning / else
    error). Runs after ``_annotate_metric_rows`` because we match on the
    already-classified ``metric-reliability`` row.
    """

    def _sub(match: re.Match[str]) -> str:
        head, tier, tail = match.group(1), match.group(2), match.group(3)
        slug = _RELIABILITY_TIER_SLUG.get(tier, "unknown")
        return (
            f'<li class="metric-row metric-reliability metric-reliability-{slug}">'
            f"{head}{tier}{tail}</li>"
        )

    return _RELIABILITY_TIER_RE.sub(_sub, fragment)


def _structure_for_print(fragment: str) -> str:
    """Run the print-mode post-passes in a stable order."""
    return _wrap_sections(_annotate_reliability_tier(_annotate_metric_rows(fragment)))


# ---------- self-contained document wrapper ----------------------------------


_PRINT_CSS = """
:root {
  --fg: #1f2933;
  --fg-muted: #5b6470;
  --accent: #1d4ed8;
  --bg-quote: #eef2ff;
  --border-muted: #e5e7eb;
  --bg-code: #f3f4f6;
  --bg-section-soft: #fafbfc;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Microsoft YaHei", sans-serif;
  font-size: 13px;
  line-height: 1.65;
  color: var(--fg);
  background: #fff;
}
.markdown-body {
  max-width: 760px;
  margin: 32px auto;
  padding: 0 24px;
}
h1 { font-size: 22px; margin: 12px 0 8px; }
h2 {
  font-size: 17px;
  margin: 18px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-muted);
}
h3 { font-size: 15px; margin: 14px 0 6px; }
p { margin: 6px 0; }
ul { padding-left: 22px; margin: 6px 0; }
li { margin: 2px 0; }
blockquote {
  margin: 8px 0;
  padding: 6px 14px;
  color: var(--fg-muted);
  border-left: 3px solid var(--accent);
  background: var(--bg-quote);
}
code {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--bg-code);
  font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
  font-size: 12.5px;
}
hr {
  border: 0;
  border-top: 1px solid var(--border-muted);
  margin: 14px 0;
}
strong { color: #111; }
.report-section {
  margin-top: 16px;
  padding: 4px 0;
  page-break-inside: avoid;
}
.report-section > h2 {
  margin-top: 8px;
}
.report-section.section-evidence,
.report-section.section-recommendation {
  background: var(--bg-section-soft);
  padding: 4px 12px;
  border-radius: 4px;
}
.metric-row {
  list-style: "› ";
  padding: 1px 0;
}
.metric-row.metric-reliability {
  font-weight: 500;
  color: var(--accent);
}
.metric-row.metric-reliability.metric-reliability-strong {
  color: #047857; /* emerald-700 — matches decision chip "success" */
}
.metric-row.metric-reliability.metric-reliability-fair {
  color: #b45309; /* amber-700 — matches decision chip "warning" */
}
.metric-row.metric-reliability.metric-reliability-weak {
  color: #b91c1c; /* red-700  — matches decision chip "error" */
}
.metric-row.metric-reliability.metric-reliability-unknown {
  color: var(--fg-muted);
}
.metric-row.metric-priority {
  color: #b91c1c;
  font-weight: 500;
}
.metric-row.metric-source-run {
  color: #92400e;
}
.metric-row.metric-evidence-count,
.metric-row.metric-evidence-ids,
.metric-row.metric-evidence-chain {
  color: #047857;
}
.metric-row.metric-kg-features,
.metric-row.metric-kg-link {
  color: #4338ca;
}
@page {
  size: A4;
  margin: 16mm 14mm;
}
@media print {
  body { font-size: 12px; }
  .markdown-body { margin: 0; padding: 0; max-width: none; }
  h1, h2, h3 { page-break-after: avoid; }
  ul, blockquote, .report-section { page-break-inside: avoid; }
  .report-section.section-evidence,
  .report-section.section-recommendation { background: transparent; }
}
"""


def render_html_document(*, title: str, markdown: str) -> str:
    """Render a fully self-contained HTML document.

    The returned string includes ``<!DOCTYPE html>``, an inline ``<style>`` block,
    and the rendered markdown body. No external resources are referenced — the
    file can be opened from any local path or attached as-is.

    The body fragment goes through ``_structure_for_print`` so each chapter is
    wrapped in a classed ``<section>`` and well-known metric rows are tagged
    with ``.metric-row.metric-{key}``. This only affects the downloadable
    HTML, not the in-app preview or the markdown contract.
    """
    body = _structure_for_print(markdown_to_html_fragment(markdown))
    safe_title = _escape_html(title)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        f"<title>{safe_title}</title>\n"
        f"<style>{_PRINT_CSS}</style>\n"
        "</head>\n"
        '<body>\n<main class="markdown-body">\n'
        f"{body}\n"
        "</main>\n</body>\n</html>\n"
    )


__all__ = ["markdown_to_html_fragment", "render_html_document"]
