import os
import re
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Bypasser</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; display: flex; height: 100vh; justify-content: center; align-items: center; margin: 0; padding: 1rem; box-sizing: border-box; }
        .card { background: #1e293b; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 520px; }
        h2 { margin-top: 0; color: #38bdf8; }
        input { width: 100%; padding: 0.75rem; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-bottom: 1rem; box-sizing: border-box; font-size: 0.95rem; }
        button { background: #0284c7; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; font-size: 1rem; }
        button:hover { background: #0369a1; }
        button:disabled { background: #475569; cursor: wait; }
        .result { margin-top: 1.5rem; word-break: break-all; background: #0f172a; padding: 1rem; border-radius: 6px; border: 1px solid #334155; display: none; line-height: 1.5; }
        .copy-btn { margin-top: 0.75rem; background: #10b981; padding: 0.5rem 1rem; font-size: 0.85rem; width: auto; }
        .copy-btn:hover { background: #059669; }
        .error-text { color: #f87171; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Link Bypasser</h2>
        <input type="text" id="urlInput" placeholder="Paste Linkvertise, LootLabs, Work.ink link here...">
        <button id="startBtn" onclick="bypassLink()">Start Bypass</button>
        <div class="result" id="resultBox"></div>
    </div>

    <script>
        async function bypassLink() {
            const input = document.getElementById('urlInput');
            const btn = document.getElementById('startBtn');
            const resultBox = document.getElementById('resultBox');
            const url = input.value.trim();
            if (!url) return;

            btn.disabled = true;
            btn.textContent = 'Bypassing...';
            resultBox.style.display = 'block';
            resultBox.innerHTML = 'Working on it, hold on a few seconds...';

            try {
                const res = await fetch('/api/bypass', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();

                if (data.success && data.bypassed) {
                    const safeUrl = data.bypassed.replace(/"/g, '&quot;');
                    resultBox.innerHTML = `
                        <strong>Result (${data.engine}):</strong><br>
                        <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8;">${data.bypassed}</a><br>
                        <button class="copy-btn" onclick="copyResult('${safeUrl}')">Copy Link</button>
                    `;
                } else {
                    resultBox.innerHTML = `<span class="error-text"><strong>Failed:</strong> ${data.error || 'Could not bypass this link.'}</span>`;
                }
            } catch (err) {
                resultBox.innerHTML = `<span class="error-text"><strong>Error:</strong> Could not reach server.</span>`;
            } finally {
                btn.disabled = false;
                btn.textContent = 'Start Bypass';
            }
        }

        function copyResult(text) {
            navigator.clipboard.writeText(text);
        }
    </script>
</body>
</html>
"""


def safe_get_json(url, headers, timeout=20):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore").strip()
            if raw.startswith("{"):
                return resp.status, json.loads(raw), raw
            return resp.status, None, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore").strip()
        if raw.startswith("{"):
            try:
                return e.code, json.loads(raw), raw
            except Exception:
                pass
        return e.code, None, raw
    except Exception as e:
        return 0, None, str(e)


def decode_lootlabs_xor(encoded_str, key_length=5):
    try:
        padding = 4 - (len(encoded_str) % 4)
        if padding < 4:
            encoded_str += "=" * padding
        raw_bytes = base64.b64decode(encoded_str)
        raw_text = raw_bytes.decode("latin-1")
        key = raw_text[:key_length]
        body = raw_text[key_length:]
        out = "".join(
            chr(ord(body[i]) ^ ord(key[i % len(key)]))
            for i in range(len(body))
        )
        return urllib.parse.unquote(out)
    except Exception:
        return None


def resolve_target(target_url):
    encoded_target = urllib.parse.quote(target_url, safe="")
    errors = []

    # 1. TRW API (keyless public bypass endpoint for Linkvertise, LootLabs, Work.ink, Platoboost)
    trw_url = f"https://trw.lat/api/bypass?url={encoded_target}&mode=normal"
    trw_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://rip.linkvertise.lol/",
        "Origin": "https://rip.linkvertise.lol",
    }
    status, data, raw = safe_get_json(trw_url, trw_headers, timeout=25)
    if data:
        if data.get("success") is True and isinstance(data.get("result"), str):
            res = data["result"].strip()
            if res.startswith(("http://", "https://")):
                return True, res, "trw.lat"
            return True, res, "trw.lat"
        if data.get("result"):
            errors.append(f"TRW: {data['result']}")
    else:
        errors.append(f"TRW HTTP {status}")

    # 2. Bypass.vip official API subdomain
    vip_url = f"https://api.bypass.vip/bypass?url={encoded_target}"
    vip_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://bypass.vip",
        "Referer": "https://bypass.vip/",
    }
    status, data, raw = safe_get_json(vip_url, vip_headers, timeout=20)
    if data:
        if data.get("status") == "success" and isinstance(data.get("result"), str):
            res = data["result"].strip()
            if res.startswith(("http://", "https://")):
                return True, res, "bypass.vip"
        if data.get("message"):
            errors.append(f"VIP: {data['message']}")
    else:
        errors.append(f"VIP HTTP {status}")

    # 3. Direct URL param & page scrape fallback (simple shorteners + LootLabs PUBLISHER_LINK)
    try:
        parsed = urllib.parse.urlparse(target_url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "cc" in qs:
            padding = 4 - (len(qs["cc"][0]) % 4)
            val = qs["cc"][0] + ("=" * padding if padding < 4 else "")
            decoded = base64.b64decode(val).decode("utf-8", errors="ignore")
            match = re.search(r'https?://[^\s"\'<>]+', decoded)
            if match:
                return True, match.group(0), "direct-decode"

        req = urllib.request.Request(
            target_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.url != target_url and not any(
                d in resp.url for d in ("lootlabs", "linkvertise", "work.ink", "platorelay")
            ):
                return True, resp.url, "redirect"

            html = resp.read().decode("utf-8", errors="ignore")
            pub_match = re.search(r'PUBLISHER_LINK\s*=\s*["\']([^"\']+)["\']', html)
            if pub_match:
                decoded_pub = decode_lootlabs_xor(pub_match.group(1))
                if decoded_pub and decoded_pub.startswith(("http://", "https://")):
                    return True, decoded_pub, "lootlabs-xor"
    except Exception as e:
        errors.append(f"Direct: {str(e)}")

    return False, " | ".join(errors) if errors else "No engine could bypass this link.", "none"


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/bypass", methods=["POST"])
def bypass():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "Please paste a link first."}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    ok, output, engine = resolve_target(url)
    return jsonify({
        "success": ok,
        "original": url,
        "bypassed": output if ok else None,
        "error": None if ok else output,
        "engine": engine,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
