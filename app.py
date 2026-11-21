import base64
import json
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
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
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
        .key-toggle {
            margin-top: 12px;
            font-size: 12px;
            color: #9aa4b8;
            cursor: pointer;
            text-decoration: underline;
            display: inline-block;
        }
        .key-box {
            display: none;
            margin-top: 10px;
            text-align: left;
        }
        .key-box small {
            display: block;
            color: #8b95aa;
            font-size: 11px;
            margin-bottom: 6px;
            line-height: 1.4;
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

        <div class="key-toggle" onclick="toggleKeyBox()">Backup API Key (optional)</div>
        <div class="key-box" id="keyBox">
            <small>Most links work with no key. Only use this if you want a backup Bacon key.</small>
            <input type="text" id="apiKeyInput" placeholder="Paste backup key (optional)..." oninput="saveKey()" autocomplete="off">
        </div>

        <div id="status"></div>
    </div>

    <script>
        window.addEventListener("DOMContentLoaded", () => {
            const saved = localStorage.getItem("bypass_api_key");
            if (saved) {
                document.getElementById("apiKeyInput").value = saved;
            }
        });

        function toggleKeyBox() {
            const box = document.getElementById("keyBox");
            box.style.display = box.style.display === "block" ? "none" : "block";
        }

        function saveKey() {
            const val = document.getElementById("apiKeyInput").value.trim();
            if (val) {
                localStorage.setItem("bypass_api_key", val);
            } else {
                localStorage.removeItem("bypass_api_key");
            }
        }

        function showSuccess(result, method) {
            const status = document.getElementById("status");
            status.textContent = "";

            const label = document.createElement("div");
            label.textContent = "Done (" + method + "):";
            status.appendChild(label);

            if (result.startsWith("http://") || result.startsWith("https://")) {
                const link = document.createElement("a");
                link.href = result;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = result;
                status.appendChild(link);
            } else {
                const textOut = document.createElement("div");
                textOut.style.color = "#4ce0b3";
                textOut.textContent = result;
                status.appendChild(textOut);
            }

            const copyBtn = document.createElement("button");
            copyBtn.className = "copy-btn";
            copyBtn.textContent = "Copy Result";
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(result);
                copyBtn.textContent = "Copied!";
            };
            status.appendChild(copyBtn);
        }

        function showError(msg) {
            const status = document.getElementById("status");
            status.textContent = "";
            const errSpan = document.createElement("span");
            errSpan.className = "err";
            errSpan.textContent = msg || "Could not bypass that link.";
            status.appendChild(errSpan);
        }

        async function pollTask(taskId, nextPath) {
            const status = document.getElementById("status");
            for (let i = 1; i <= 45; i++) {
                status.textContent = "Solving link... (" + (i * 2) + "s)";
                await new Promise(r => setTimeout(r, 2000));

                const res = await fetch("/check", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ task_id: taskId, next_path: nextPath })
                });
                const data = await res.json();

                if (data.done) {
                    if (data.success && data.result) {
                        showSuccess(data.result, data.method || "trw-api");
                    } else {
                        showError(data.error || "Bypass failed.");
                    }
                    return;
                }
            }
            showError("Timed out waiting for the solver. Try pressing Start again.");
        }

        async function startBypass() {
            const input = document.getElementById("urlInput");
            const keyInput = document.getElementById("apiKeyInput");
            const btn = document.getElementById("startBtn");
            const status = document.getElementById("status");
            const url = input.value.trim();
            const apiKey = keyInput.value.trim();

            status.textContent = "";
            if (!url) {
                showError("Paste a link first.");
                return;
            }

            btn.disabled = true;
            btn.textContent = "Working...";
            status.textContent = "Bypassing link...";

            try {
                const res = await fetch("/bypass", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, api_key: apiKey })
                });
                const data = await res.json();

                if (data.pending) {
                    await pollTask(data.task_id || "", data.next_path || "");
                } else if (data.success && data.result) {
                    showSuccess(data.result, data.method || "direct");
                } else {
                    showError(data.error);
                }
            } catch (e) {
                showError("Server error. Try again.");
            } finally {
                btn.disabled = false;
                btn.textContent = "Start";
            }
        }
    </script>
</body>
</html>
"""


def looks_like_spam_banner(text: str) -> bool:
    lowered = text.lower()
    bad_markers = (
        "shut down",
        "leechers",
        "join here for working bypasses",
        "bypass.vip/discord",
    )
    return any(m in lowered for m in bad_markers)


def try_base64_decode(value: str):
    if not value:
        return None
    cleaned = value.strip().replace(" ", "+")
    padded = cleaned + "=" * (-len(cleaned) % 4)
    for fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            decoded = fn(padded).decode("utf-8", errors="ignore").strip()
            if decoded.startswith(("http://", "https://")):
                return decoded
        except Exception:
            continue
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


def decrypt_lootlabs_data(url: str):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    raw_data = (params.get("data") or [None])[0]
    if not raw_data:
        return None
    cleaned = raw_data.strip().replace(" ", "+")
    padded = cleaned + "=" * (-len(cleaned) % 4)
    for fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            raw_bytes = fn(padded)
            if len(raw_bytes) <= 5:
                continue
            key = raw_bytes[:5]
            enc = raw_bytes[5:]
            out = bytes(enc[i] ^ key[i % 5] for i in range(len(enc))).decode("utf-8", errors="strict")
            if out.startswith(("http://", "https://")) and all(32 <= ord(c) < 127 for c in out):
                return out
        except Exception:
            continue
    return None


def bypass_rekonise(session: requests.Session, url: str):
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path:
        return None, None
    try:
        r = session.get(f"https://api.rekonise.com/social-unlocks{path}", headers=HEADERS, timeout=10)
        if r.ok:
            data = r.json()
            if isinstance(data, dict) and data.get("url"):
                return data["url"], "rekonise-api"
    except Exception:
        pass
    return None, None


def find_key_recursive(obj, target_key: str):
    if isinstance(obj, dict):
        if target_key in obj and isinstance(obj[target_key], str) and obj[target_key].strip():
            return obj[target_key].strip()
        for val in obj.values():
            found = find_key_recursive(val, target_key)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_key_recursive(item, target_key)
            if found:
                return found
    return None


def bypass_mboost(session: requests.Session, url: str):
    try:
        r = session.get(url, headers=HEADERS, timeout=10)
        if not r.ok:
            return None, None
        soup = BeautifulSoup(r.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            data = json.loads(script.string)
            found = find_key_recursive(data, "targeturl")
            if found:
                return found, "mboost-nextdata"
    except Exception:
        pass
    return None, None


def bypass_paste(session: requests.Session, url: str):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")
    if not path:
        return None, None

    try:
        if "pastebin.com" in host and not path.startswith("raw/"):
            slug = path.split("/")[0]
            r = session.get(f"https://pastebin.com/raw/{slug}", headers=HEADERS, timeout=10)
            if r.ok and r.text.strip():
                return r.text.strip(), "pastebin-raw"

        if "rentry.co" in host or "rentry.org" in host:
            slug = path.split("/")[0]
            r = session.get(f"https://{host}/{slug}/raw", headers=HEADERS, timeout=10)
            if r.ok and r.text.strip():
                return r.text.strip(), "rentry-raw"

        if "pastefy.app" in host:
            slug = path.split("/")[0]
            r = session.get(f"https://pastefy.app/api/v2/paste/{slug}", headers=HEADERS, timeout=10)
            if r.ok:
                data = r.json()
                if isinstance(data, dict) and data.get("content"):
                    return data["content"].strip(), "pastefy-api"
    except Exception:
        pass
    return None, None


def bypass_adfly(session: requests.Session, url: str):
    try:
        r = session.get(url, headers=HEADERS, timeout=10)
        if not r.ok:
            return None, None
        m = re.search(r"var\s+ysmm\s*=\s*['\"]([^'\"]+)['\"]", r.text)
        if not m:
            return None, None
        ysmm = m.group(1)
        a = "".join(ysmm[i] for i in range(0, len(ysmm), 2))
        b = "".join(ysmm[i] for i in range(1, len(ysmm), 2))[::-1]
        combined = list(a + b)
        i = 0
        while i < len(combined):
            if combined[i].isdigit():
                for j in range(i + 1, len(combined)):
                    if combined[j].isdigit():
                        x = int(combined[i]) ^ int(combined[j])
                        if x < 10:
                            combined[i] = str(x)
                        i = j
                        break
            i += 1
        decoded = try_base64_decode("".join(combined))
        if decoded:
            if not decoded.startswith(("http://", "https://")) and "http" in decoded:
                return decoded[decoded.find("http"):], "adfly-decode"
            return decoded, "adfly-decode"
    except Exception:
        pass
    return None, None


def bypass_plato_local(session: requests.Session, url: str):
    direct = extract_query_redirect(url)
    if direct:
        return direct, "plato-redirect"

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    ticket_id = (params.get("id") or [None])[0]

    if ticket_id:
        for app_id in ("8", "2569"):
            try:
                r = session.get(
                    f"https://api-gateway.platoboost.com/v1/authenticators/{app_id}/{ticket_id}",
                    headers=HEADERS,
                    timeout=10,
                )
                if r.ok:
                    info = r.json()
                    if isinstance(info, dict):
                        if info.get("key"):
                            return info["key"], "platoboost-key"
                        if info.get("redirect"):
                            return info["redirect"], "platoboost-api"
            except Exception:
                continue

    return None, None


def bypass_with_trw(session: requests.Session, url: str):
    try:
        r = session.get(
            "https://trw.lat/api/bypass",
            params={"url": url, "mode": "thread", "origin": "web"},
            headers=HEADERS,
            timeout=20,
        )
        data = r.json()
        if data.get("success") is True and data.get("result"):
            val = str(data["result"]).strip()
            if val and not looks_like_spam_banner(val):
                return {"success": True, "result": val, "method": "trw-api"}, None

        tid = data.get("task_id") or data.get("ThreadID") or data.get("id")
        next_path = data.get("next") or ""
        if tid or next_path:
            return {"pending": True, "task_id": str(tid or ""), "next_path": str(next_path)}, None

        if data.get("success") is False and data.get("result"):
            return None, str(data["result"])
    except Exception as exc:
        return None, f"TRW API error: {exc}"
    return None, None


def bypass_with_bacon(session: requests.Session, url: str, api_key: str):
    if not api_key:
        return None, None, None
    try:
        r = session.post(
            "https://api.baconbypass.xyz/bypass",
            json={"url": url, "apikey": api_key},
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=22,
        )
        data = r.json()
        if data.get("status") == "success" and data.get("result"):
            val = str(data["result"]).strip()
            if val and not looks_like_spam_banner(val):
                return val, "bacon-api", None
        err = data.get("message") or data.get("error")
        if err:
            return None, None, f"Backup API error: {err}"
    except Exception as exc:
        return None, None, f"Backup API failed: {exc}"
    return None, None, None


def bypass_with_custom_api(session: requests.Session, url: str):
    custom_api = os.environ.get("BYPASS_API_URL", "").strip()
    custom_key = os.environ.get("BYPASS_API_KEY", "").strip()
    if not custom_api:
        return None, None

    req_headers = {**HEADERS}
    params = {"url": url}
    if custom_key:
        req_headers["x-api-key"] = custom_key
        req_headers["Authorization"] = f"Bearer {custom_key}"
        params["apikey"] = custom_key

    try:
        r = session.get(custom_api, params=params, headers=req_headers, timeout=22)
        if r.ok:
            data = r.json()
            for key in ("result", "resultUrl", "destination", "bypassed", "url", "key"):
                val = data.get(key)
                if isinstance(val, str) and val.strip() and not looks_like_spam_banner(val):
                    return val.strip(), "custom-api"
    except Exception:
        pass
    return None, None


def bypass_generic(session: requests.Session, url: str):
    direct = extract_query_redirect(url)
    if direct:
        return direct, "query-decode"

    try:
        r = session.get(url, headers=HEADERS, allow_redirects=True, timeout=12)
        if r.url != url and "challenges.cloudflare.com" not in r.url:
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
    except Exception:
        pass

    return None, None


def run_bypass(url: str, user_api_key: str = ""):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    host = urlparse(url).netloc.lower()
    session = requests.Session()

    # 1. Fast local decoders
    if any(d in host for d in ("loot-link", "lootlabs", "lootdest", "lootlinks", "links-loot")):
        decoded = decrypt_lootlabs_data(url) or extract_query_redirect(url)
        if decoded:
            return {"success": True, "result": decoded, "method": "loot-decode"}

    if any(d in host for d in ("rekonise.com", "rkns.link")):
        res, method = bypass_rekonise(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    if "mboost.me" in host:
        res, method = bypass_mboost(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    if any(d in host for d in ("pastebin.com", "rentry.co", "rentry.org", "pastefy.app")):
        res, method = bypass_paste(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    if any(d in host for d in ("adf.ly", "j.gs", "q.gs")):
        res, method = bypass_adfly(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    if any(d in host for d in ("platorelay", "platoboost", "deltaios")):
        res, method = bypass_plato_local(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    # 2. Keyless TRW API (handles Linkvertise, LootLabs, Work.ink, Delta, LockR)
    trw_out, trw_err = bypass_with_trw(session, url)
    if trw_out:
        return trw_out

    # 3. Optional backup Bacon API key (if typed or set in Render)
    bacon_key = user_api_key.strip() or os.environ.get("BACON_API_KEY", "").strip()
    bacon_err = None
    if bacon_key:
        res, method, bacon_err = bypass_with_bacon(session, url, bacon_key)
        if res:
            return {"success": True, "result": res, "method": method}

    # 4. Optional custom API from Render environment settings
    res, method = bypass_with_custom_api(session, url)
    if res:
        return {"success": True, "result": res, "method": method}

    # 5. Generic HTTP redirect follow (skip for known gate sites so we don't just echo the gate URL)
    if not any(d in host for d in ("lootlabs", "loot-link", "lootdest", "linkvertise", "platorelay", "platoboost", "work.ink")):
        res, method = bypass_generic(session, url)
        if res:
            return {"success": True, "result": res, "method": method}

    return {"success": False, "error": bacon_err or trw_err or "Could not bypass this link."}


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/bypass", methods=["POST"])
def bypass_route():
    data = request.get_json(silent=True) or {}
    target_url = (data.get("url") or "").strip()
    user_key = (data.get("api_key") or "").strip()
    if not target_url:
        return jsonify({"success": False, "error": "Please paste a link."}), 400

    try:
        output = run_bypass(target_url, user_key)
        return jsonify(output)
    except requests.Timeout:
        return jsonify({"success": False, "error": "The solver took too long to answer."}), 504
    except Exception as exc:
        return jsonify({"success": False, "error": f"Failed: {exc}"}), 500


@app.route("/check", methods=["POST"])
def check_route():
    data = request.get_json(silent=True) or {}
    task_id = (data.get("task_id") or "").strip()
    next_path = (data.get("next_path") or "").strip()

    try:
        if next_path.startswith("/api/"):
            target = f"https://trw.lat{next_path}"
            r = requests.get(target, headers=HEADERS, timeout=15)
        elif task_id:
            r = requests.get(
                "https://trw.lat/api/v2/threadcheck",
                params={"id": task_id, "task_id": task_id},
                headers=HEADERS,
                timeout=15,
            )
        else:
            return jsonify({"done": True, "success": False, "error": "Missing task ID."}), 400

        res = r.json()
        status = str(res.get("status") or "").lower()

        if res.get("success") is True and res.get("result"):
            val = str(res["result"]).strip()
            if not looks_like_spam_banner(val):
                return jsonify({"done": True, "success": True, "result": val, "method": "trw-api"})

        if status in ("done", "failed", "error", "expired") or res.get("success") is False:
            if res.get("success") is False or status in ("failed", "error", "expired"):
                return jsonify({
                    "done": True,
                    "success": False,
                    "error": str(res.get("result") or "Solver could not finish this link."),
                })

        return jsonify({"done": False})
    except Exception as exc:
        return jsonify({"done": True, "success": False, "error": f"Check failed: {exc}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
