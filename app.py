from flask import Flask, render_template_string, request, jsonify
import urllib.request
import urllib.parse
import base64
import json
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

def deep_resolve(target_url):
    try:
        # 1. Base64 / LootLabs Parameter Decoder Check
        parsed_url = urllib.parse.urlparse(target_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        for param in ['cc', 'data', 'token', 'r']:
            if param in query_params:
                val = query_params[param][0]
                padding = 4 - (len(val) % 4)
                if padding < 4:
                    val += '=' * padding
                try:
                    decoded = base64.b64decode(val).decode('utf-8', errors='ignore')
                    # Look for embedded urls inside decoded json or plaintext
                    if '{' in decoded:
                        j = json.loads(decoded)
                        for k in ['url', 'destination', 'link', 'target']:
                            if k in j:
                                return j[k]
                    url_match = re.search(r'https?://[^\s<>"]+', decoded)
                    if url_match and url_match.group(0) != target_url:
                        return url_match.group(0)
                except Exception:
                    pass

        # 2. HTTP Request with Redirect Chaining and Body Scraping
        req = urllib.request.Request(
            target_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        
        # Custom opener to trace redirect URLs step by step
        class RedirectFilter(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                return super().http_error_302(req, fp, code, msg, headers)
            def http_error_301(self, req, fp, code, msg, headers):
                return super().http_error_301(req, fp, code, msg, headers)

        opener = urllib.request.build_opener(RedirectFilter)
        with opener.open(req, timeout=8) as resp:
            final_url = resp.url
            if final_url != target_url and not any(x in final_url for x in ['lootlabs', 'linkvertise', 'ouo.io']):
                return final_url
            
            html = resp.read().decode('utf-8', errors='ignore')

        # 3. Pattern matching inside the HTML response payload
        # Check window.location or target variables
        patterns = [
            r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
            r'destination\s*[:=]\s*["\'](https?://[^"\']+)["\']',
            r'targetUrl\s*[:=]\s*["\'](https?://[^"\']+)["\']',
            r'content=["\'][^"\']*URL=([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                found = match.group(1)
                if found and not found.startswith('javascript:'):
                    return found

        return "Could not unwrap target. Page requires browser automation context."

    except Exception as e:
        return f"Resolution failure: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/bypass', methods=['POST'])
def bypass():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    resolved = deep_resolve(url)
    return jsonify({'original': url, 'bypassed': resolved})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
