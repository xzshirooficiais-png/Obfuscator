import base64
import os
import re
import urllib.parse
import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Bypasser</title>
    <style>
        body {
            background: #0f172a;
            color: #f8fafc;
            font-family: system-ui, sans-serif;
            display: flex;
            min-height: 100vh;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 1rem;
            box-sizing: border-box;
        }
        .card {
            background: #1e293b;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 520px;
        }
        h2 { margin-top: 0; color: #38bdf8; }
        input {
            width: 100%;
            padding: 0.75rem;
            border-radius: 6px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #fff;
            margin-bottom: 1rem;
            box-sizing: border-box;
            font-size: 0.95rem;
        }
        button {
            background: #0284c7;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            font-weight: bold;
            font-size: 1rem;
        }
        button:hover { background: #0369a1; }
        button:disabled { background: #475569; cursor: not-allowed; }
        .result {
            margin-top: 1.5rem;
            word-break: break-all;
            background: #0f172a;
            padding: 1rem;
            border-radius: 6px;
            border: 1px solid #334155;
            display: none;
            line-height: 1.5;
        }
        .error { color: #f87171; }
        .meta { color: #94a3b8; font-size: 0.8rem; margin-top: 0.5rem; }
        a { color: #38bdf8; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Link Bypasser</h2>
        <input type="text" id="urlInput" placeholder="Paste Linkvertise, LootLabs, or short link here...">
        <button id="startBtn" onclick="bypassLink()">Start Bypass</button>
        <div class="result" id="resultBox"></div>
    </div>

    <script>
        function isValidHttpUrl(str) {
            return typeof str === 'string' && (str.startsWith('http://') || str.startsWith('https://'));
        }

        function showSuccess(url, source) {
            const resultBox = document.getElementById('resultBox');
            resultBox.innerHTML = '';
            const label = document.createElement('strong');
            label.textContent = 'Result: ';
            const link = document.createElement('a');
            link.href = url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = url;
            const meta = document.createElement('div');
            meta.className = 'meta';
            meta.textContent = 'Solved via: ' + source;
            resultBox.appendChild(label);
            resultBox.appendChild(link);
            resultBox.appendChild(meta);
        }

        function showError(msg) {
            const resultBox = document.getElementById('resultBox');
            resultBox.innerHTML = '';
            const span = document.createElement('span');
            span.className = 'error';
            span.textContent = msg;
            resultBox.appendChild(span);
        }

        async function clientFallback(targetUrl) {
            const encoded = encodeURIComponent(targetUrl);
            const endpoints = [
                {
                    name: 'browser -> trw.lat',
                    url: `https://trw.lat/api/bypass?url=${encoded}&mode=normal`,
                    extract: (d) => d && d.success && isValidHttpUrl(d.result) ? d.result : null
                },
                {
                    name: 'browser -> bypass.vip',
                    url: `https://api.bypass.vip/bypass?url=${encoded}`,
                    extract: (d) => d && d.status === 'success' && isValidHttpUrl(d.result) ? d.result : null
                }
            ];

            for (const ep of endpoints) {
                try {
                    const res = await fetch(ep.url);
                    if (!res.ok) continue;
                    const data = await res.json();
                    const found = ep.extract(data);
                    if (found) return { url: found, source: ep.name };
                } catch (_) {}
            }
            return null;
        }

        async function bypassLink() {
            const input = document.getElementById('urlInput');
            const btn = document.getElementById('startBtn');
            const resultBox = document.getElementById('resultBox');
            const url = input.value.trim();
            if (!url) return;

            btn.disabled = true;
            resultBox.style.display = 'block';
            resultBox.textContent = 'Bypassing... (LootLabs and Linkvertise can take 5-20 seconds)';

            try {
                const res = await fetch('/api/bypass', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();

                if (isValidHttpUrl(data.bypassed)) {
                    showSuccess(data.bypassed, data.source || 'server');
                    return;
                }

                resultBox.textContent = 'Server blocked or timed out, trying direct browser fallback...';
                const direct = await clientFallback(url);
                if (direct) {
                    showSuccess(direct.url, direct.source);
                    return;
                }

                showError('Bypass failed: ' + (data.error || 'Could not resolve this link right now.'));
            } catch (err) {
                showError('Network error: ' + err.message);
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""


def is_http_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def check_base64_param(target_url):
    parsed = urllib.parse.urlparse(target_url)
    params = urllib.parse.parse_qs(parsed.query)
    for key in ("r", "u", "url", "dest"):
        if key in params and params[key]:
            raw = params[key][0]
            if is_http_url(raw):
                return raw
            try:
                padded = raw + "=" * (-len(raw) % 4)
                decoded = base64.b64decode(padded).decode("utf-8", errors="ignore").strip()
                if is_http_url(decoded):
                    return decoded
            except Exception:
                pass
    return None


def query_api_engines(target_url):
    errors = []

    engines = [
        (
            "trw.lat",
            "https://trw.lat/api/bypass",
            {"url": target_url, "mode": "normal"},
            HEADERS,
            lambda d: d.get("result") if d.get("success") else None,
        ),
        (
            "bypass.vip",
            "https://api.bypass.vip/bypass",
            {"url": target_url},
            {**HEADERS, "Origin": "https://bypass.vip", "Referer": "https://bypass.vip/"},
            lambda d: d.get("result") if d.get("status") == "success" else None,
        ),
        (
            "api.4ndra.com",
            "https://api.4ndra.com/v1/bypass-ad-link",
            {"url": target_url},
            HEADERS,
            lambda d: d.get("data", {}).get("result") if d.get("success") else None,
        ),
        (
            "dlr.kys.gay",
            "https://dlr.kys.gay/api/free/bypass",
            {"url": target_url},
            HEADERS,
            lambda d: d.get("result") if d.get("status") == "success" else None,
        ),
    ]

    for name, endpoint, params, req_headers, extractor in engines:
        try:
            resp = requests.get(endpoint, params=params, headers=req_headers, timeout=25)
            if resp.status_code != 200:
                errors.append(f"{name}: HTTP {resp.status_code}")
                continue
            payload = resp.json()
            result = extractor(payload)
            if is_http_url(result) and result != target_url:
                return result, name, errors
            msg = payload.get("result") or payload.get("message") or payload.get("error") or "no result"
            errors.append(f"{name}: {msg}")
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")

    return None, None, errors


def direct_html_fallback(target_url):
    try:
        resp = requests.get(target_url, headers=HEADERS, allow_redirects=True, timeout=12)
        if resp.url != target_url and is_http_url(resp.url):
            return resp.url

        html = resp.text
        for pattern in (
            r'window\.location\.href\s*=\s*["\'](https?://[^"\']+)["\']',
            r'"destination"\s*:\s*"(https?://[^"]+)"',
        ):
            match = re.search(pattern, html)
            if match:
                candidate = match.group(1).replace("\\/", "/")
                if is_http_url(candidate):
                    return candidate

        b64_matches = re.findall(r'aHR0c[A-Za-z0-9+/=]{10,}', html)
        for chunk in b64_matches:
            try:
                padded = chunk + "=" * (-len(chunk) % 4)
                decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
                if is_http_url(decoded):
                    return decoded
            except Exception:
                pass
    except Exception:
        pass
    return None


def resolve_link(target_url):
    direct_param = check_base64_param(target_url)
    if direct_param:
        return direct_param, "url-param", []

    api_result, source, errors = query_api_engines(target_url)
    if api_result:
        return api_result, source, errors

    html_result = direct_html_fallback(target_url)
    if html_result:
        return html_result, "html-redirect", errors

    return None, None, errors


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/bypass", methods=["POST"])
def bypass():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not is_http_url(url):
        return jsonify({"error": "Enter a full URL starting with http:// or https://"}), 400

    resolved, source, errors = resolve_link(url)
    if resolved:
        return jsonify({"original": url, "bypassed": resolved, "source": source})

    detail_text = " | ".join(errors) if errors else "Target needs full captcha/browser solve."
    return jsonify({"original": url, "bypassed": None, "error": detail_text}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
