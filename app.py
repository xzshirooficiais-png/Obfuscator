import os
import re
import random
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

def obfuscate_code_string(code):
    # Strip comments
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--.*$', '', code, flags=re.MULTILINE)

    # Generate dynamic random key
    key = random.randint(15, 240)
    
    # Convert code to XOR encrypted byte list
    bytes_list = []
    for c in code:
        b = ord(c) ^ key
        bytes_list.append(str(b))
    
    bytes_str = ", ".join(bytes_list)

    # Bulletproof runtime decoding stub using raw byte arrays
    final_payload = f'''-- Obfuscated via Ollie's Secure Cloud Obfuscator
local function _run()
    local _b = {{{bytes_str}}}
    local _k = {key}
    local _r = {{}}
    
    local function _bx(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit and bit.bxor then return bit.bxor(a, b) end
        return a ~ b
    end
    
    for _i = 1, #_b do
        _r[_i] = string.char(_bx(_b[_i], _k))
    end
    
    local _code = table.concat(_r)
    local _f, _err = (loadstring or load)(_code)
    if _f then
        return _f()
    else
        error("Obfuscation load error: " .. tostring(_err))
    end
end
_run()
'''
    return final_payload

# Embedded HTML / CSS / JS Interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ollie's Cloud Obfuscator</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        h1 { color: #58a6ff; text-align: center; font-size: 1.8rem; }
        .pane-group { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 20px; }
        .pane { flex: 1; min-width: 350px; display: flex; flex-direction: column; }
        label { margin-bottom: 8px; font-weight: bold; color: #8b949e; }
        textarea { width: 100%; height: 350px; background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 14px; resize: vertical; box-sizing: border-box; }
        textarea:focus { border-color: #58a6ff; outline: none; }
        button { background-color: #238636; color: white; border: none; padding: 12px 20px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 15px; width: 100%; transition: background 0.2s; }
        button:hover { background-color: #2ea043; }
        .status { text-align: center; margin-top: 10px; color: #f0883e; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>OLLIE'S CLOUD LUA OBFUSCATOR</h1>
        <div class="pane-group">
            <div class="pane">
                <label for="inputCode">Raw Script Input:</label>
                <textarea id="inputCode" placeholder="Paste your raw Lua source here..."></textarea>
            </div>
            <div class="pane">
                <label for="outputCode">Obfuscated Output:</label>
                <textarea id="outputCode" placeholder="Obfuscated script will appear here..." readonly></textarea>
            </div>
        </div>
        <button onclick="obfuscateScript()">OBFUSCATE SCRIPT</button>
        <div id="status" class="status"></div>
    </div>

    <script>
        async function obfuscateScript() {
            const code = document.getElementById('inputCode').value;
            const status = document.getElementById('status');
            const outputBox = document.getElementById('outputCode');

            if (!code.trim()) {
                status.innerText = "Error: Input box is empty!";
                return;
            }

            status.innerText = "Obfuscating script...";
            outputBox.value = "";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code })
                });

                const data = await response.json();
                if (data.success) {
                    outputBox.value = data.obfuscated;
                    status.innerText = "Success! Script obfuscated.";
                } else {
                    status.innerText = "Error: " + (data.error || "Unknown error");
                }
            } catch (err) {
                status.innerText = "Network Error: Failed to reach server.";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/obfuscate', methods=['POST'])
def api_obfuscate():
    data = request.get_json(silent=True) or request.form
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "No Lua code provided"}), 400
    
    protected = obfuscate_code_string(code)
    return jsonify({"success": True, "obfuscated": protected})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
