#!/usr/bin/env python3
"""MoFashion Survey Server — Render deployment"""

import http.server, json, csv, os, io, base64, urllib.parse, urllib.request, threading
from pathlib import Path
from datetime import datetime

# Google Sheets 后端（服务器端转发，被试不直接连 Google）
GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/AKfycbyJteU9g4I-cHOmcExAnb3HTxHJTBiBTDSpjAqQL5XBDUXPl2ZELMrgfuhE3CNRrq8/exec"

# 内存存储（服务重启前可靠）
MEMORY_STORE = []  # list of submission dicts

PORT = int(os.environ.get("PORT", 10000))
DATA_FILE = Path(__file__).parent / "data.jsonl"

# Find survey HTML files
def find_survey_dir():
    """Find the directory containing survey HTML files"""
    candidates = [
        Path(__file__).parent,           # same dir as script (render)
        Path(__file__).parent / "public_survey",  # subfolder
        Path.cwd(),                       # current working dir
        Path.cwd() / "public_survey",
    ]
    for d in candidates:
        if (d / "survey-1.html").exists():
            return d
    return None

SURVEY_DIR = find_survey_dir()
SURVEY_HTML = {}

def load_surveys():
    global SURVEY_HTML
    if SURVEY_DIR is None:
        return
    for i in [1, 2, 3]:
        path = SURVEY_DIR / f"survey-{i}.html"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                h = f.read()
            # Replace Google URL
            h = h.replace(
                "https://script.google.com/macros/s/AKfycbyJteU9g4I-cHOmcExAnb3HTxHJTBiBTDSpjAqQL5XBDUXPl2ZELMrgfuhE3CNRrq8/exec",
                "/api/submit")
            # Remove dual-channel submit code (iframe+fallback)
            mk1 = "const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(data))));"
            mk2 = "bar.style.display='block';bar.className='status-bar';bar.textContent='"
            p1 = h.find(mk1)
            if p1 >= 0:
                p2 = h.find(mk2, p1)
                if p2 >= 0:
                    ps = h.find(";", p2 + len(mk2) + 10)
                    if ps < 0:
                        ps = h.find("}", p2 + len(mk2))
                    if ps > 0:
                        h = h[:p1] + h[ps+1:]
            SURVEY_HTML[i] = h

load_surveys()

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>时尚搭配生成质量评估</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei',sans-serif;text-align:center;padding:40px 20px;background:linear-gradient(135deg,#f5f5f5,#e0e0e0);min-height:100vh}
.card{background:#fff;max-width:520px;margin:0 auto;padding:36px;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.08)}
h1{color:#667eea;margin-bottom:8px;font-size:1.6em}
.subtitle{color:#888;margin-bottom:20px}
.note{background:#fff9c4;padding:16px 20px;border-radius:8px;text-align:left;font-size:0.85em;color:#666;line-height:1.6;margin-bottom:16px}
ul{list-style:none;padding:0;text-align:left}
li{margin:10px 0}
a{display:block;padding:14px 22px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:10px;text-decoration:none;font-size:1.05em}
a:hover{opacity:0.9}
</style></head>
<body>
<div class="card">
<h1>时尚搭配生成质量评估</h1>
<p class="subtitle">AI 生成服装搭配的用户偏好调研</p>
<div class="note">
<b>填写说明：</b><br>
• 每位参与者<b>只需填写一份问卷</b>（约 15-20 分钟）<br>
• 请按照研究者分配给您的编号，点击下方对应链接<br>
• 请使用<b>电脑浏览器</b>填写以获得最佳体验
</div>
<p style="color:#555;margin-bottom:16px;font-size:0.9em">研究人员会告知您应该填写哪一份：</p>
<ul>
<li><a href="/survey/1">问卷 1（25 题，约 15-20 分钟）</a></li>
<li><a href="/survey/2">问卷 2（25 题，约 15-20 分钟）</a></li>
<li><a href="/survey/3">问卷 3（25 题，约 15-20 分钟）</a></li>
</ul>
</div>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path.startswith("/survey/"):
            sid = int(path.split("/")[-1])
            html = SURVEY_HTML.get(sid, "")
            if html:
                self._html(200, html)
            else:
                self._html(404, f"Survey {sid} not found. Available: {list(SURVEY_HTML.keys())}")
            return

        if path == "/" or path == "/index.html":
            self._html(200, INDEX_HTML)
            return

        if path == "/debug":
            info = {
                "cwd": str(Path.cwd()),
                "script_dir": str(Path(__file__).parent),
                "survey_dir": str(SURVEY_DIR) if SURVEY_DIR else "NOT FOUND",
                "survey_html_loaded": list(SURVEY_HTML.keys()),
                "files_in_cwd": sorted(os.listdir(Path.cwd())),
                "files_in_script_dir": sorted(os.listdir(Path(__file__).parent)),
            }
            self._html(200, f"<pre>{json.dumps(info, indent=2, ensure_ascii=False)}</pre>")
            return

        if path == "/admin":
            self._serve_admin()
            return

        if path == "/admin/download":
            self._download_csv()
            return

        if path == "/test-google":
            try:
                body = urllib.parse.urlencode({"data": '{"test":true}'}).encode()
                req = urllib.request.Request(GOOGLE_SHEETS_URL, data=body, method="POST")
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
                resp = urllib.request.urlopen(req, timeout=15)
                result = f"Google OK: HTTP {resp.status} - {resp.read().decode()[:500]}"
            except Exception as e:
                result = f"Google FAIL: {e}"
            self._html(200, f"<pre>{result}</pre>")
            return

        if path == "/health":
            self._json(200, {"status": "ok"})
            return

        self._html(404, "Not found")

    def do_POST(self):
        if self.path == "/api/submit":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            params = urllib.parse.parse_qs(body)
            raw_data = params.get("data", [""])[0]
            if not raw_data:
                self._json(400, {"success": False, "error": "No data"})
                return

            data = json.loads(raw_data)
            record = {
                "timestamp": datetime.now().isoformat(),
                "survey_id": data.get("survey_id", ""),
                "answers": data.get("answers", []),
            }

            # 1. 存内存（服务运行时始终保留）
            MEMORY_STORE.append(record)

            # 2. 存本地文件（尽力而为）
            try:
                with open(DATA_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except:
                pass

            # 3. 转发到 Google Sheets（服务器端，美国→Google 无墙）
            def forward_to_google():
                try:
                    gdata = {
                        "survey_id": record["survey_id"],
                        "timestamp": record["timestamp"],
                        "answers": record["answers"],
                    }
                    body = urllib.parse.urlencode({"data": json.dumps(gdata)}).encode()
                    req = urllib.request.Request(GOOGLE_SHEETS_URL, data=body, method="POST")
                    req.add_header("Content-Type", "application/x-www-form-urlencoded")
                    urllib.request.urlopen(req, timeout=10)
                    print(f"Google Sheets: forwarded survey {record['survey_id']}")
                except Exception as e:
                    print(f"Google Sheets: forward failed ({e})")

            threading.Thread(target=forward_to_google, daemon=True).start()

            self._html(200, "<html><body style='font-family:sans-serif;text-align:center;padding:60px'><h1 style='color:#27ae60'>提交成功！</h1><p>感谢您的参与。</p></body></html>")
            return
        self._json(404, {"error": "Not found"})

    def _serve_admin(self):
        # 优先用内存数据（包含未持久化的最新提交）
        submissions = list(MEMORY_STORE)
        # 如果内存为空，尝试从文件恢复
        if not submissions and DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            submissions.append(json.loads(line))
                            MEMORY_STORE.append(submissions[-1])
            except:
                pass

        def compute_stats(answers_list):
            s = {"MoFashion": {"compat": 0, "personal": 0, "overall": 0},
                 "SD-v1.5": {"compat": 0, "personal": 0, "overall": 0},
                 "SD-v2.1": {"compat": 0, "personal": 0, "overall": 0}}
            for a in answers_list:
                for dim, key in [("compat", "compat_model"), ("personal", "personal_model"), ("overall", "overall_model")]:
                    model = a.get(key, "")
                    if model in s:
                        s[model][dim] += 1
            return s

        # Separate by task
        fitb_answers = []
        gor_answers = []
        for sub in submissions:
            for a in sub.get("answers", []):
                if a.get("task", "").upper() == "GOR":
                    gor_answers.append(a)
                else:
                    fitb_answers.append(a)

        fitb = compute_stats(fitb_answers)
        gor = compute_stats(gor_answers)

        def make_table(stats, title):
            t = f"<tr><th colspan='4' style='background:#667eea;color:#fff'>{title}（共 {sum(stats[m]['overall'] for m in stats)} 次投票）</th></tr>"
            t += "<tr><th>维度</th><th>MoFashion</th><th>SD-v1.5</th><th>SD-v2.1</th></tr>"
            for dim, label in [("compat", "兼容性"), ("personal", "个性化"), ("overall", "整体偏好")]:
                dim_total = sum(stats[m][dim] for m in stats)
                t += f"<tr><td><b>{label}</b></td>"
                for m in ["MoFashion", "SD-v1.5", "SD-v2.1"]:
                    c = stats[m][dim]
                    p = f"{c/dim_total*100:.0f}%" if dim_total > 0 else "-"
                    t += f"<td>{c} ({p})</td>"
                t += "</tr>"
            return t

        table1 = make_table(fitb, "FITB（填空补全）")
        table2 = make_table(gor, "GOR（搭配推荐）")

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>问卷后台</title>
<style>
*{{margin:0;padding:0}}body{{font-family:'Microsoft YaHei',sans-serif;background:#f5f5f5;padding:20px}}
.container{{max-width:1000px;margin:0 auto}}
.card{{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06)}}
h1{{color:#667eea;margin-bottom:8px}}h2{{color:#555;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px;text-align:center;border-bottom:1px solid #eee}}
th{{background:#f0f0f0}}
.summary{{display:flex;gap:16px;flex-wrap:wrap}}
.summary-item{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:14px 20px;border-radius:8px;min-width:100px;text-align:center}}
.summary-item .num{{font-size:1.8em;font-weight:bold}}
.summary-item .label{{font-size:0.8em;opacity:0.9}}
.btn{{display:inline-block;padding:8px 16px;background:#667eea;color:#fff;border-radius:6px;text-decoration:none;margin:4px}}
</style></head>
<body>
<div class="container">
<h1>问卷后台 - 实时统计</h1>
<div class="card"><h2>FITB（填空补全）</h2><table>{table1}</table></div>
<div class="card"><h2>GOR（搭配推荐）</h2><table>{table2}</table></div>
<div class="card"><a class="btn" href="/admin/download">下载 CSV</a></div>
<p style="text-align:center;color:#888;margin-top:12px">共 {len(submissions)} 份提交</p>
<script>setTimeout(function(){{location.reload()}},30000);</script>
</div></body></html>"""
        self._html(200, html)

    def _download_csv(self):
        submissions = list(MEMORY_STORE)
        if not submissions and DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            submissions.append(json.loads(line))
            except:
                pass
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["提交时间","问卷编号","题号","任务","兼容性选择","兼容性模型","个性化选择","个性化模型","整体偏好选择","整体偏好模型"])
        for sub in submissions:
            for a in sub.get("answers", []):
                writer.writerow([sub["timestamp"], sub["survey_id"], a.get("question",""), a.get("task",""),
                    a.get("compat_choice",""), a.get("compat_model",""), a.get("personal_choice",""), a.get("personal_model",""),
                    a.get("overall_choice",""), a.get("overall_model","")])
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=survey_results.csv")
        self.end_headers()
        self.wfile.write(buf.getvalue().encode("utf-8-sig"))

    def _html(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"Server on port {PORT}")
    print(f"Survey dir: {SURVEY_DIR}")
    print(f"Surveys loaded: {list(SURVEY_HTML.keys())}")
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
