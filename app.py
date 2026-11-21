from flask import Flask, render_template, request, jsonify
import urllib.parse
import re
import urllib.request
import json

app = Flask(__name__)

def resolve_link(target_url):
    try:
        # Basic resolution logic for common trackers/shorteners
        req = urllib.request.Request(
            target_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        
        # If it's a known service pattern, integrate backend logic or fallback to redirect chain following
        with urllib.request.urlopen(req, timeout=10) as response:
            final_url = response.url
            html_content = response.read().decode('utf-8', errors='ignore')
            
            # Look for common meta refresh redirects or window.location patterns in ad gates
            match = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', html_content)
            if match:
                return match.group(1)
                
            return final_url
    except Exception as e:
        return f"Error resolving link: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/bypass', methods=['POST'])
def bypass():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
        
    resolved = resolve_link(url)
    return jsonify({'original': url, 'bypassed': resolved})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
