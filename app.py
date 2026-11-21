from flask import Flask, render_template_string, request, jsonify
import urllib.request
import urllib.parse
import json

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
            resultBox.innerHTML = 'Querying Bypass Engine...';

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
                    resultBox.innerHTML = `<strong>Error:</strong> ${data.error || 'Failed to resolve link'}`;
                }
            } catch (err) {
                resultBox.innerHTML = `<strong>Error:</strong> Network request failed.`;
            }
        }
    </script>
</body>
</html>
"""

def query_bypass_vip(target_url):
    try:
        api_endpoint = f"https://bypass.vip/api/free?url={urllib.parse.quote(target_url)}"
        req = urllib.request.Request(
            api_endpoint,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*'
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            raw_body = response.read().decode('utf-8', errors='ignore')
            if not raw_body.strip():
                return "Error: Received empty response from bypass engine."
            
            try:
                res_data = json.loads(raw_body)
            except json.JSONDecodeError:
                return f"Error: Non-JSON response block returned: {raw_body[:100]}"
            
            if isinstance(res_data, dict):
                if res_data.get('status') == 'success':
                    return res_data.get('result') or res_data.get('destination')
                elif 'result' in res_data:
                    return res_data['result']
                elif 'destination' in res_data:
                    return res_data['destination']
                elif 'url' in res_data:
                    return res_data['url']
                elif 'message' in res_data:
                    return f"API Message: {res_data['message']}"
            
            return f"Unexpected response layout: {raw_body}"
    except Exception as e:
        return f"Resolution connection error: {str(e)}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/bypass', methods=['POST'])
def bypass():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    resolved = query_bypass_vip(url)
    return jsonify({'original': url, 'bypassed': resolved})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
