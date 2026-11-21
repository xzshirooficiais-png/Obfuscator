from flask import Flask, render_template_string, request, jsonify
import urllib.request
import urllib.parse
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
        <input type="text" id="urlInput" placeholder="Paste Linkvertise or short link here...">
        <button onclick="bypassLink()">Start Bypass</button>
        <div class="result" id="resultBox"></div>
    </div>

    <script>
        async function bypassLink() {
            const url = document.getElementById('urlInput').value;
            const resultBox = document.getElementById('resultBox');
            if(!url) return;
            
            resultBox.style.display = 'block';
            resultBox.innerHTML = 'Bypassing through routing engine...';

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
                    resultBox.innerHTML = `<strong>Error:</strong> ${data.error || 'Failed to resolve'}`;
                }
            } catch (err) {
                resultBox.innerHTML = `<strong>Error:</strong> Network request failed.`;
            }
        }
    </script>
</body>
</html>
"""

def advanced_bypass(target_url):
    # Strategy 1: Query public bypass API (e.g., bypass.bot.nu or similar open endpoints)
    try:
        api_url = f"https://bypass.bot.nu/bypass?url={urllib.parse.quote(target_url)}"
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if res_data.get('success') and res_data.get('destination'):
                return res_data['destination']
    except Exception:
        pass

    # Strategy 2: Fallback manual redirect / meta-tag chain tracker
    try:
        req = urllib.request.Request(
            target_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            final_url = response.url
            if final_url != target_url:
                return final_url
            
            html = response.read().decode('utf-8', errors='ignore')
            # Extract target link if embedded via linkvertise target layouts
            link_match = re.search(r'\"destination\"\s*:\s*\"([^\"]+)\"', html)
            if link_match:
                return link_match.group(1).encode().decode('unicode-escape')
                
            return "Could not auto-extract destination. Target requires browser execution context."
    except Exception as e:
        return f"Resolution error: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/bypass', methods=['POST'])
def bypass():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    resolved = advanced_bypass(url)
    return jsonify({'original': url, 'bypassed': resolved})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
