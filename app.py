import os
import re
import random
import base64
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

def obfuscate_code_string(code):
    # Strip comments
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    code = re.sub(r'--.*$', '', code, flags=re.MULTILINE)

    # Encrypt strings
    key = random.randint(10, 250)
    def encrypt_match(match):
        s = match.group(1)
        encrypted = ''.join(chr(ord(c) ^ key) for c in s)
        b64 = base64.b64encode(encrypted.encode('latin1')).decode('ascii')
        return f'_dec("{b64}", {key})'

    code_encrypted = re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)"', encrypt_match, code)
    code_encrypted = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", encrypt_match, code_encrypted)

    # Variable renaming / identifier mangling
    identifiers = set(re.findall(r'\b(?:local\s+([a-zA-Z_][a-zA-Z0-9_]*))', code_encrypted))
    rename_map = {}
    for idx, ident in enumerate(identifiers):
        if ident not in ['print', 'math', 'string', 'table', 'load', 'bit32']:
            rename_map[ident] = f"_0x{random.randint(1000, 9999):x}_{idx}"

    for old, new in rename_map.items():
        code_encrypted = re.sub(r'\b' + old + r'\b', new, code_encrypted)

    # Wrap in runtime decoder stub
    final_payload = f'''-- Obfuscated via Ollie's Cloud Obfuscator GUI
local function _dec(b64, k)
    local b = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    local s = (b64:gsub('[^%w%+%%/=]', ''))
    local r = {{}}
    for i = 1, #s, 4 do
        local a, b_val, c, d = b:find(s:sub(i,i)), b:find(s:sub(i+1,i+1)), b:find(s:sub(i+2,i+2)), b:find(s:sub(i+3,i+3))
        local n = (a-1)*262144 + (b_val-1)*4096 + ((c or 1)-1)*64 + ((d or 1)-1)
        local t1, t2, t3 = math.floor(n/65536)%256, math.floor(n/256)%256, n%256
        table.insert(r, string.char(t1))
        if c then table.insert(r, string.char(t2)) end
        if d then table.insert(r, string.char(t3)) end
    end
    local raw = table.concat(r)
    local res = {{}}
    for i = 1, #raw do
        res[i] = string.char(bit32 and bit32.bxor(raw:byte(i), k) or (raw:byte(i) ~ k))
    end
    return table.concat(res)
end

local function _exec()
    {code_encrypted}
end
_exec()
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
