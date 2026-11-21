from flask import Flask, render_template_string, request, jsonify
import urllib.request
import urllib.parse
import json
import base64
import re

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Bypasser</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; display: flex; height: 100vh; justify-content: center; align-items: center; margin: 0; }
        .card { background: #1e293b; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 500px; }
        h2 { margin-top: 0; color: #38bdf8; }
        input { width: 100%; padding: 0.75rem; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; margin-bottom: 1rem; box-sizing: border-box; }
        button { background: #0284c7; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; width: 100%; font-weight: bold; }
        button:hover { background: #0369a1; }
        .result { margin-top: 1.5rem; word-break: break-all; background: #0f172a; padding: 1rem; border-radius: 6px; border: 1px solid #334155; display: none; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Link Bypasser</h2>
        <input type="text" id="urlInput" placeholder="Paste LootLabs, Linkvertise link here...">
        <button onclick="bypassLink()">Start Bypass</button>
        <div class="result" id="resultBox"></div>
    </div>

    <script>
        async function bypassLink() {
            const url = document.getElementById('urlInput').value;
            const resultBox = document.getElementById('resultBox');
            if(!url) return;
            
            resultBox.style.display = 'block';
            resultBox.innerHTML = 'Unwrapping target link...';

            try {
                const res = await fetch('/api/bypass', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                if(data.bypassed) {
                    resultBox.innerHTML = `<strong>Result:</strong> <a href="${data.bypassed}" target="_blank" style="color: #38bdf8;">${data.bypassed}</a>`;
                } else {
                    resultBox.innerHTML = `<strong>Error:</strong> ${data.error || 'Could not resolve target'}`;
                }
            } catch (err) {
                resultBox.innerHTML = `<strong>Error:</strong> Request failed.`;
            }
        }
    </script>
</body>
</html>
"""

def resolve_target(target_url):
    try:
        # 1. Handle LootLabs base64 'cc' query parameters directly
        parsed_url = urllib.parse.urlparse(target_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'cc' in query_params:
            cc_val = query_params['cc'][0]
            padding = 4 - (len(cc_val) % 4)
            if padding < 4:
                cc_val += '=' * padding
            decoded_str = base64.b64decode(cc_val).decode('utf-8', errors='ignore')
            try:
                data_json = json.loads(decoded_str)
                if 'url' in data_json:
                    return data_json['url']
                if 'destination' in data_json:
                    return data_json['destination']
            except Exception:
                url_match = re.search(r'https?://[^\s<>"]+', decoded_str)
                if url_match:
                    return url_match.group(0)

        # 2. Query public resolution endpoints for linkvertise / other shorteners
        endpoints = [
            f"https://bypass.bot.nu/bypass?url={urllib.parse.quote(target_url)}",
            f"https://api.bypass.city/bypass?url={urllib.parse.quote(target_url)}"
        ]
        
        for api in endpoints:
            try:
                req = urllib.request.Request(api, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    if res_data.get('success') and res_data.get('destination'):
                        return res_data['destination']
            except Exception:
                continue

        # 3. Final fallback: direct HTTP tracking check
        req_direct = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_direct, timeout=5) as resp:
            return resp.url

    except Exception as e:
        return f"Extraction failed: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/bypass', methods=['POST'])
def bypass():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    resolved = resolve_target(url)
    return jsonify({'original': url, 'bypassed': resolved})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
