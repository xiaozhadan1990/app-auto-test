"""Generate a self-contained HTML test report from test_results.json."""
from __future__ import annotations

import base64
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent


def generate_report(results_file: str | Path, output_file: str | Path) -> bool:
    results_path = Path(results_file)
    if not results_path.exists():
        return False

    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception:
        return False

    tests = data.get("tests", [])
    total = data.get("total", 0)
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)
    skipped = data.get("skipped", 0)
    pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "0%"
    total_duration = sum(t.get("duration", 0) for t in tests)

    rows_html = ""
    for i, test in enumerate(tests):
        status = test.get("status", "unknown")
        status_class = {"passed": "pass", "failed": "fail", "skipped": "skip"}.get(status, "skip")
        status_label = {"passed": "✓ 通过", "failed": "✗ 失败", "skipped": "⊘ 跳过"}.get(status, status)

        # Screenshot — embed as base64 for self-contained report
        sc_path_str = test.get("screenshot")
        if sc_path_str:
            sc_abs = _PROJECT_ROOT / sc_path_str
            if sc_abs.exists():
                img_b64 = base64.b64encode(sc_abs.read_bytes()).decode()
                screenshot_html = f'<img src="data:image/png;base64,{img_b64}" class="screenshot" alt="截图"/>'
            else:
                screenshot_html = '<p class="no-art">截图文件不存在</p>'
        else:
            screenshot_html = '<p class="no-art">无截图（测试通过）</p>'

        # Video — absolute URI link
        video_path_str = test.get("video")
        if video_path_str:
            video_abs = _PROJECT_ROOT / video_path_str
            if video_abs.exists():
                video_uri = video_abs.resolve().as_uri()
                video_html = (
                    f'<a class="video-btn" href="{video_uri}" target="_blank">▶ 播放视频</a>'
                    f'<div class="video-path">{video_path_str}</div>'
                )
            else:
                video_html = '<p class="no-art">视频文件不存在</p>'
        else:
            video_html = '<p class="no-art">无视频</p>'

        # Error
        error_msg = test.get("error_message") or ""
        error_html = ""
        if error_msg:
            safe = error_msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            error_html = f'<div class="error-block"><pre>{safe[:1000]}</pre></div>'

        rows_html += f"""
        <tr class="test-row {status_class}-row" onclick="toggle('det{i}')">
          <td class="idx">{i + 1}</td>
          <td class="tname" title="{test.get('node_id', '')}">{test.get('name', '')}</td>
          <td><span class="badge {status_class}">{status_label}</span></td>
          <td class="center">{test.get('duration', 0)}s</td>
          <td class="center">{test.get('app', '-')}</td>
        </tr>
        <tr id="det{i}" class="det-row">
          <td colspan="5">
            <div class="det-body">
              <div class="det-sc"><h4>截图</h4>{screenshot_html}</div>
              <div class="det-vid"><h4>测试视频</h4>{video_html}</div>
              {error_html}
            </div>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>测试报告</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f7fa;color:#333;padding:20px}}
h1{{color:#2c3e50;margin-bottom:8px;font-size:1.6em}}
.meta{{color:#888;font-size:.85em;margin-bottom:20px}}
.summary{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
.card{{background:#fff;border-radius:8px;padding:16px 24px;box-shadow:0 2px 8px rgba(0,0,0,.08);flex:1;min-width:110px;text-align:center}}
.num{{font-size:2.2em;font-weight:700}}.label{{font-size:.82em;color:#666;margin-top:2px}}
.num.pass{{color:#27ae60}}.num.fail{{color:#e74c3c}}.num.skip{{color:#f39c12}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
th{{background:#2c3e50;color:#fff;padding:10px 14px;text-align:left;font-weight:500;font-size:.88em}}
.test-row td{{padding:9px 14px;border-bottom:1px solid #f0f0f0;cursor:pointer}}
.test-row:hover td{{background:#f8f9fa}}
.fail-row td{{background:#fff8f8}}.fail-row:hover td{{background:#fef2f2}}
.badge{{padding:2px 10px;border-radius:12px;font-size:.8em;font-weight:600}}
.badge.pass{{background:#eafaf1;color:#1e8449}}
.badge.fail{{background:#fdedec;color:#c0392b}}
.badge.skip{{background:#fef9e7;color:#d68910}}
.det-row{{display:none}}
.det-row.open{{display:table-row}}
.det-row td{{background:#fafbfc;padding:0}}
.det-body{{display:flex;gap:20px;padding:16px 20px;flex-wrap:wrap;align-items:flex-start}}
.det-sc,.det-vid{{flex:1;min-width:200px}}
h4{{font-size:.82em;text-transform:uppercase;letter-spacing:.5px;color:#666;margin-bottom:8px}}
.screenshot{{max-width:100%;max-height:380px;border:1px solid #ddd;border-radius:4px;display:block}}
.video-btn{{display:inline-block;background:#3498db;color:#fff;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:.88em}}
.video-btn:hover{{background:#2980b9}}
.video-path{{font-size:.78em;color:#999;margin-top:6px;word-break:break-all}}
.no-art{{color:#aaa;font-size:.85em;font-style:italic;margin:4px 0}}
.error-block{{flex:100%;background:#fff5f5;border-left:4px solid #e74c3c;border-radius:4px;padding:12px;margin-top:8px}}
.error-block pre{{font-size:.8em;color:#c0392b;white-space:pre-wrap;word-break:break-word}}
.idx,.center{{text-align:center}}
.tname{{max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
</style>
</head>
<body>
<h1>测试报告</h1>
<div class="meta">
  开始: {data.get('session_start', '-')} &nbsp;|&nbsp;
  结束: {data.get('session_end', '-')} &nbsp;|&nbsp;
  总耗时: {total_duration:.1f}s &nbsp;|&nbsp;
  通过率: {pass_rate}
</div>
<div class="summary">
  <div class="card"><div class="num">{total}</div><div class="label">总计</div></div>
  <div class="card"><div class="num pass">{passed}</div><div class="label">通过</div></div>
  <div class="card"><div class="num fail">{failed}</div><div class="label">失败</div></div>
  <div class="card"><div class="num skip">{skipped}</div><div class="label">跳过</div></div>
</div>
<table>
  <thead>
    <tr>
      <th style="width:40px">#</th>
      <th>测试用例</th>
      <th style="width:90px">结果</th>
      <th style="width:70px">耗时</th>
      <th style="width:110px">应用</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
<script>
function toggle(id){{
  var el=document.getElementById(id);
  el.classList.toggle('open');
}}
</script>
</body>
</html>"""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return True
