"""/api/report blueprint — markdown report generation.

The blueprint is a thin HTTP layer over ``app.services.report_builder``.
Reports are generated on demand from the latest decision snapshot and stored
in an in-memory LRU registry. The frontend uses:

- ``POST /api/report/generate``       to create a new report
- ``GET  /api/report?projectId=...``  to list reports for a project
- ``GET  /api/report/<id>``           to fetch the rendered markdown
- ``GET  /api/report/<id>/download``        to download the markdown as a file
- ``GET  /api/report/<id>/download.html``   to download a self-contained HTML
                                            (suitable for "Print → Save as PDF")
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.services import report_builder
from app.services.project_store import get_store
from app.services.report_html import render_html_document

bp = Blueprint("report", __name__, url_prefix="/api/report")


def _ok(data: object, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


@bp.get("/ping")
def ping() -> tuple[Response, int]:
    return _ok({"module": "report", "implemented": True})


@bp.get("")
@bp.get("/")
def list_reports() -> tuple[Response, int]:
    project_id = request.args.get("projectId") or request.args.get("project_id")
    if not project_id:
        return _err("projectId 查询参数必填", 400)
    if get_store().get(project_id) is None:
        return _err(f"项目 {project_id} 不存在", 404)
    summaries = [r.summary() for r in report_builder.list_reports(project_id)]
    return _ok(summaries)


@bp.post("/generate")
def generate_report() -> tuple[Response, int]:
    payload: dict[str, Any] = request.get_json(silent=True) or {}
    project_id = payload.get("projectId") or payload.get("project_id")
    if not project_id:
        return _err("payload 缺少 projectId", 400)
    try:
        record = report_builder.generate_report(project_id)
    except KeyError:
        return _err(f"项目 {project_id} 不存在", 404)
    return _ok(record.summary(), status=201)


@bp.get("/<report_id>")
def get_report(report_id: str) -> tuple[Response, int]:
    record = report_builder.get_report(report_id)
    if record is None:
        return _err(f"报告 {report_id} 不存在或已过期", 404)
    return _ok(record.full())


@bp.get("/<report_id>/download")
def download_report(report_id: str) -> tuple[Response, int] | Response:
    record = report_builder.get_report(report_id)
    if record is None:
        return _err(f"报告 {report_id} 不存在或已过期", 404)
    filename = f"echolens-report-{record.project_id}-{record.id[:8]}.md"
    response = Response(record.markdown, mimetype="text/markdown; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@bp.get("/<report_id>/download.html")
def download_report_html(report_id: str) -> tuple[Response, int] | Response:
    """Download a self-contained HTML rendering of the report.

    The HTML inlines all styles (no external links) and includes a ``@page``
    rule so users can open it in any browser and use "Print → Save as PDF"
    for a print-quality export — no server-side PDF toolchain required.
    """
    record = report_builder.get_report(report_id)
    if record is None:
        return _err(f"报告 {report_id} 不存在或已过期", 404)
    html = render_html_document(title=record.title, markdown=record.markdown)
    filename = f"echolens-report-{record.project_id}-{record.id[:8]}.html"
    response = Response(html, mimetype="text/html; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
