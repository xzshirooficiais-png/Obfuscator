import os
import re
import random
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def build_advanced_vm(source_code):
    # 1. Clean comments and dead padding
    source_code = re.sub(r'--\[\[.*?\]\]', '', source_code, flags=re.DOTALL)
    source_code = re.sub(r'--.*$', '', source_code, flags=re.MULTILINE).strip()

    # 2. Dynamic Opcode Shuffling per build
    op_loadk = random.randint(10, 45)
    op_concat = random.randint(46, 85)
    op_exec = random.randint(86, 130)
    op_halt = random.randint(200, 254)

    # 3. Constant Splitting
    chunk_size = random.randint(4, 8)
    chunks = [source_code[i:i+chunk_size] for i in range(0, len(source_code), chunk_size)]
    
    # 4. Generate Raw Instruction Sequence
    instructions = []
    for idx, _ in enumerate(chunks):
        instructions.extend([op_loadk, idx + 1, idx + 1])
    
    instructions.extend([op_concat, len(chunks)])
    instructions.extend([op_exec, 1])
    instructions.extend([op_halt, 0])

    # 5. Rolling-Cipher Bytecode Encryption
    initial_seed = random.randint(20, 220)
    multiplier = random.randint(3, 11) * 2 + 1
    
    encrypted_bytes = []
    current_key = initial_seed
    for b in instructions:
        enc_b = b ^ (current_key & 0xFF)
        encrypted_bytes.append(enc_b)
        current_key = (current_key * multiplier + b + 17) & 0xFF

    # 6. Build the Hardened Lua VM Engine
    engine_payload = f'''-- [ OLLIE ADVANCED LURAPH-KILLER VM ]
local function _init_guard()
    local _tostring = tostring
    local _pcall = pcall
    local function _check_closure(fn)
        local str = _tostring(fn)
        return str:find("builtin") or str:find("native") or str:find("function: 0x") or str:find("function: [A-Za-z0-9]")
    end
    if not _check_closure(pcall) or not _check_closure(tostring) then
        while true do end
    end
end
_init_guard()

local function _dispatch()
    local _bc = {{{", ".join(map(str, encrypted_bytes))}}}
    local _const_pool = {repr(chunks)}
    local _state_key = {initial_seed}
    local _mult = {multiplier}
    
    local _registers = {{}}
    local _accumulator = {{}}
    local _ip = 1
    
    local OP_LOADK  = {op_loadk}
    local OP_CONCAT = {op_concat}
    local OP_EXEC   = {op_exec}
    local OP_HALT   = {op_halt}
    
    local function _bx(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit and bit.bxor then return bit.bxor(a, b) end
        return a ~ b
    end
    
    while _ip <= #_bc do
        local _enc_byte = _bc[_ip]
        local _op = _bx(_enc_byte, _state_key % 256)
        _state_key = (_state_key * _mult + _op + 17) % 256
        _ip = _ip + 1
        
        if _op == OP_LOADK then
            local _reg = _bx(_bc[_ip], _state_key % 256)
            _state_key = (_state_key * _mult + _reg + 17) % 256
            _ip = _ip + 1
            
            local _cidx = _bx(_bc[_ip], _state_key % 256)
            _state_key = (_state_key * _mult + _cidx + 17) % 256
            _ip = _ip + 1
            
            _registers[_reg] = _const_pool[_cidx]
            
        elseif _op == OP_CONCAT then
            local _count = _bx(_bc[_ip], _state_key % 256)
            _state_key = (_state_key * _mult + _count + 17) % 256
            _ip = _ip + 1
            
            for i = 1, _count do
                table.insert(_accumulator, _registers[i])
            end
            
        elseif _op == OP_EXEC then
            local _target = _bx(_bc[_ip], _state_key % 256)
            _state_key = (_state_key * _mult + _target + 17) % 256
            _ip = _ip + 1
            
            local _reconstructed = table.concat(_accumulator)
            local _fn, _err = (loadstring or load)(_reconstructed)
            if _fn then
                _fn()
            else
                error("Engine fault: " .. tostring(_err))
            end
            
        elseif _op == OP_HALT then
            break
        else
            while true do end
        end
    end
end

_dispatch()
'''
    return engine_payload

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Lua VM Obfuscator</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        h1 { color: #58a6ff; text-align: center; font-size: 1.8rem; }
        .pane-group { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 20px; }
        .pane { flex: 1; min-width: 320px; display: flex; flex-direction: column; }
        label { margin-bottom: 8px; font-weight: bold; color: #8b949e; }
        textarea { width: 100%; height: 350px; background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-family: monospace; font-size: 14px; resize: vertical; box-sizing: border-box; }
        textarea:focus { border-color: #58a6ff; outline: none; }
        button { background-color: #238636; color: white; border: none; padding: 12px 20px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 15px; width: 100%; }
        button:hover { background-color: #2ea043; }
        .status { text-align: center; margin-top: 10px; color: #f0883e; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>ADVANCED ROLLING-CIPHER VM OBFUSCATOR</h1>
        <div class="pane-group">
            <div class="pane">
                <label for="inputCode">Raw Script Input:</label>
                <textarea id="inputCode" placeholder="Paste your raw Lua script here..."></textarea>
            </div>
            <div class="pane">
                <label for="outputCode">Hardened Bytecode VM Output:</label>
                <textarea id="outputCode" placeholder="Obfuscated VM code will appear here..." readonly></textarea>
            </div>
        </div>
        <button onclick="obfuscateScript()">VIRTUALIZE SCRIPT</button>
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

            status.innerText = "Encrypting instructions into rolling-cipher VM...";
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
                    status.innerText = "Success! Hardened VM generated.";
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
    return Response(HTML_PAGE, mimetype='text/html')

@app.route('/obfuscate', methods=['POST'])
def api_obfuscate():
    data = request.get_json(silent=True) or request.form
    code = data.get('code', '')
    if not code:
        return jsonify({"error": "No Lua code provided"}), 400
    
    try:
        protected = build_advanced_vm(code)
        return jsonify({"success": True, "obfuscated": protected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
