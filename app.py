import base64
import os
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string, request
import requests

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Bypasser</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0f1115;
            color: #eef1f6;
            font-family: Arial, sans-serif;
            padding: 16px;
        }
        .card {
            width: 100%;
            max-width: 460px;
            background: #181c24;
            border: 1px solid #2b3240;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
        }
        h2 {
            margin: 0 0 16px;
            font-size: 22px;
        }
        input {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #353e50;
            background: #0f1115;
            color: #ffffff;
            font-size: 14px;
            margin-bottom: 12px;
        }
        button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: #7c5cff;
            color: #ffffff;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover {
            background: #6845f5;
        }
        button:disabled {
            opacity: 0.6;
            cursor: wait;
        }
        #status {
            margin-top: 16px;
            font-size: 14px;
            word-break: break-all;
            line-height: 1.5;
        }
        a {
            color: #4ce0b3;
        }
        .err {
            color: #ff6b6b;
        }
        .copy-btn {
            margin-top: 10px;
            background: #2b3240;
            font-size: 13px;
            padding: 8px;
        }
        .copy-btn:hover {
            background: #3a4356;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>Link Bypasser</h2>
        <input type="text" id="urlInput" placeholder="Paste your link here..." autocomplete="off">
        <button id="startBtn" onclick="startBypass()">Start</button>
        <div id="status"></div>
    </div>

    <script>
        async function startBypass() {
            const input = document.getElementById("urlInput");
            const btn = document.getElementById("startBtn");
            const status = document.getElementById("status");
            const url = input.value.trim();

            status.textContent = "";
            if (!url) {
                status.innerHTML = '<span class="err">Paste a link first.</span>';
                return;
            }

            btn.disabled = true;
            btn.textContent = "Working...";
            status.textContent = "Checking link...";

            try {
                const res = await fetch("/bypass", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                status.textContent = "";

                if (data.success && data.result) {
                    const label = document.createElement("div");
                    label.textContent = "Done (" + data.method + "):";
                    status.appendChild(label);

                    if (data.result.startsWith("http://") || data.result.startsWith("https://")) {
                        const link = document.createElement("a");
                        link.href = data.result;
                        link.target = "_blank";
                        link.rel = "noopener noreferrer";
                        link.textContent = data.result;
                        status.appendChild(link);
                    } else {
                        const textOut = document.createElement("div");
                        textOut.style.color = "#4ce0b3";
                        textOut.textContent = data.result;
                        status.appendChild(textOut);
                    }

                    const copyBtn = document.createElement("button");
                    copyBtn.className = "copy-btn";
                    copyBtn.textContent = "Copy Result";
                    copyBtn.onclick = () => {
                        navigator.clipboard.writeText(data.result);
                        copyBtn.textContent = "Copied!";
                    };
                    status.appendChild(copyBtn);
                } else {
                    const errSpan = document.createElement("span");
                    errSpan.className = "err";
                    errSpan.textContent = data.error || "Could not bypass that link.";
                    status.appendChild(errSpan);
                }
            } catch (e) {
                status.innerHTML = '<span class="err">Server error. Try again.</span>';
            } finally {
                btn.disabled = false;
                btn.textContent = "Start";
            }
        }
    </script>
</body>
</html>
"""


def try_base64_decode(value: str):
    if not value:
        return None
    padded = value.strip() + "=" * (-len(value.strip()) % 4)
    try:
        decoded = base64.b64decode(padded, validate=False).decode("utf-8", errors="ignore").strip()
        if decoded.startswith(("http://", "https://")):
            return decoded
    except Exception:
        pass
    try:
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore").strip()
        if decoded.startswith(("http://", "https://")):
            return decoded
    except Exception:
        pass
    return None


def extract_query_redirect(url: str):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    for key in ("r", "url", "redirect", "target", "dest", "link", "to"):
        if key in params and params[key]:
            val = params[key][0]
            if val.startswith(("http://", "https://")):
                return val
            decoded = try_base64_decode(val)
            if decoded:
                return decoded
    return None


def bypass_linkvertise_local(session: requests.Session, url: str):
    # Check base64 dynamic target first (?r=...)
    direct = extract_query_redirect(url)
    if direct:
        return direct, "linkvertise-dynamic"

    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2 and parts[0].isdigit():
        user_id, link_slug = parts[0], parts[1]
        graphql_url = "https://publisher.linkvertise.com/graphql"
        payload = {
            "operationName": "getDetailPageContent",
            "variables": {
                "url": {"userId": user_id, "linkName": link_slug},
                "accessToken": "",
            },
            "query": (
                "query getDetailPageContent($url: LinkIdentificationInput!) { "
                "getDetailPageContent(url: $url) { "
                "access_token paste_content target_type "
                "} }"
            ),
        }
        r = session.post(
            graphql_url,
            json=payload,
            headers={**HEADERS, "Origin": "https://linkvertise.com", "Referer": "https://linkvertise.com/"},
            timeout=12,
        )
        if r.ok:
            data = r.json()
            content = (data.get("data") or {}).get("getDetailPageContent") or {}
            if content.get("paste_content"):
                return content["paste_content"], "linkvertise-paste"

    r = session.get(url, headers=HEADERS, timeout=12)
    for pattern in (r'"target"\s*:\s*"(https?://[^"]+)"', r'"url"\s*:\s*"(https?://[^"]+)"'):
        m = re.search(pattern, r.text)
        if m and "linkvertise" not in m.group(1):
            return m.group(1).replace("\\/", "/"), "linkvertise-html"
    return None, None


def bypass_plato_local(session: requests.Session, url: str):
    direct = extract_query_redirect(url)
    if direct:
        return direct, "plato-redirect"

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    ticket_id = (params.get("id") or params.get("d") or [None])[0]

    # Try standard Platoboost / Platorelay status API
    if ticket_id:
        for base_api in (
            "https://api-gateway.platoboost.com/v1/authenticators/8",
            "https://api.platorelay.com/v1/sessions/auth",
        ):
            try:
                r = session.get(f"{base_api}/{ticket_id}", headers=HEADERS, timeout=10)
                if r.ok:
                    info = r.json()
                    if isinstance(info, dict):
                        if info.get("key"):
                            return info["key"], "plato-key"
                        if info.get("redirect"):
                            return info["redirect"], "plato-api"
            except Exception:
                continue

    r = session.get(url, headers=HEADERS, allow_redirects=True, timeout=12)
    if r.url != url and "plato" not in urlparse(r.url).netloc:
        return r.url, "plato-follow"
    return None, None


def bypass_via_external_api(session: requests.Session, url: str):
    # Optional custom bypass API from Render Environment Variables
    custom_api = os.environ.get("BYPASS_API_URL", "").strip()
    custom_key = os.environ.get("BYPASS_API_KEY", "").strip()

    endpoints = []
    if custom_api:
        endpoints.append((custom_api, custom_key))
    endpoints.extend([
        ("https://api.bypass.vip/bypass", ""),
    ])

    for endpoint, api_key in endpoints:
        try:
            req_headers = {**HEADERS}
            if api_key:
                req_headers["x-api-key"] = api_key
            r = session.get(endpoint, params={"url": url}, headers=req_headers, timeout=18)
            if r.ok:
                data = r.json()
                for key in ("result", "destination", "bypassed", "url", "key"):
                    val = data.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip(), "external-api"
        except Exception:
            continue
    return None, None


def bypass_generic(session: requests.Session, url: str):
    direct = extract_query_redirect(url)
    if direct:
        return direct, "query-decode"

    r = session.get(url, headers=HEADERS, allow_redirects=True, timeout=12)
    if r.url != url:
        return r.url, "redirect-follow"

    soup = BeautifulSoup(r.text, "html.parser")
    meta = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
    if meta and meta.get("content"):
        m = re.search(r"url=([^\s;]+)", meta["content"], re.I)
        if m:
            return m.group(1).strip("'\""), "meta-refresh"

    for pattern in (
        r'window\.location(?:\.href)?\s*=\s*["\'](https?://[^"\']+)["\']',
        r'location\.replace\(\s*["\'](https?://[^"\']+)["\']\s*\)',
    ):
        m = re.search(pattern, r.text)
        if m:
            return m.group(1), "js-redirect"

    return None, None


def run_bypass(url: str):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    host = urlparse(url).netloc.lower()
    session = requests.Session()

    if any(d in host for d in ("linkvertise.com", "link-target.net", "direct-link.net", "link-hub.net", "up-to-down.net")):
        res, method = bypass_linkvertise_local(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    if any(d in host for d in ("platorelay", "platoboost", "deltaios")):
        res, method = bypass_plato_local(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    if any(d in host for d in ("loot-link", "lootlabs", "lootdest")):
        res = extract_query_redirect(url)
        if res:
            return {"success": True, "result": res, "method": "loot-decode"}

    res, method = bypass_via_external_api(session, url)
    if res:
        return {"success": True, "result": res, "method": method}

    res, method = bypass_generic(session, url)
    if res:
        return {"success": True, "result": res, "method": method}

    return {
        "success": False,
        "error": "Blocked by captcha or Cloudflare. Add a BYPASS_API_URL in Render env settings if needed.",
    }


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/bypass", methods=["POST"])
def bypass_route():
    data = request.get_json(silent=True) or {}
    target_url = (data.get("url") or "").strip()
    if not target_url:
        return jsonify({"success": False, "error": "Please paste a link."}), 400

    try:
        output = run_bypass(target_url)
        return jsonify(output)
    except requests.Timeout:
        return jsonify({"success": False, "error": "The target site took too long to answer."}), 504
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed: {exc}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
