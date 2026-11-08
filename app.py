import os
import re
import random
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

def compile_luraph_vm(lua_code):
    # Strip comments
    lua_code = re.sub(r'--\[\[.*?\]\]', '', lua_code, flags=re.DOTALL)
    lua_code = re.sub(r'--.*$', '', lua_code, flags=re.MULTILINE)

    # Randomized dynamic virtual opcodes per compilation
    op_loadk = random.randint(10, 40)
    op_call  = random.randint(41, 80)
    op_halt  = random.randint(200, 250)
    
    # Dynamic XOR encryption key for the instruction stream
    vm_key = random.randint(15, 240)
    
    # Convert code to raw character stream packed into virtual constants
    const_payload = lua_code.strip()
    
    # Virtual Bytecode Stream: [OP_LOADK, RegTarget, ConstIdx, OP_CALL, RegTarget, OP_HALT]
    raw_bytecode = [
        op_loadk, 1, 1,
        op_call, 1,
        op_halt
    ]
    
    # Encrypt the bytecode array using the randomized key
    encrypted_bc = [b ^ vm_key for b in raw_bytecode]
    
    # Build Luraph-style Virtual Machine Dispatcher Stub
    vm_stub = f'''-- Luraph-Style VM Obfuscated Script
local function _run_vm()
    local _bc = {{{", ".join(map(str, encrypted_bc))}}}
    local _consts = {{{repr(const_payload)}}}
    local _k = {vm_key}
    
    -- Virtual Machine CPU State
    local _reg = {{}}
    local _ip = 1
    
    local OP_LOADK = {op_loadk}
    local OP_CALL  = {op_call}
    local OP_HALT  = {op_halt}
    
    local function _bx(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit and bit.bxor then return bit.bxor(a, b) end
        return a ~ b
    end
    
    while _ip <= #_bc do
        local _op = _bx(_bc[_ip], _k)
        _ip = _ip + 1
        
        if _op == OP_LOADK then
            local _dest = _bc[_ip]
            _ip = _ip + 1
            local _cidx = _bc[_ip]
            _ip = _ip + 1
            _reg[_dest] = _consts[_cidx]
            
        elseif _op == OP_CALL then
            local _target = _bc[_ip]
            _ip = _ip + 1
            local _fn, _err = (loadstring or load)(_reg[_target])
            if _fn then
                _fn()
            else
                error("VM Instruction Fault: " .. tostring(_err))
            end
            
        elseif _op == OP_HALT then
            break
        else
            error("Invalid virtual opcode execution")
        end
    end
end

local _ok, _err = pcall(_run_vm)
if not _ok then
    error("VM Critical Error: " .. tostring(_err))
end
'''
    return vm_stub

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Luraph-Style Cloud Obfuscator</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        h1 { color: #58a6ff; text-align: center; font-size: 1.8rem; }
        .pane-group { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 20px; }
        .pane { flex: 1; min-width: 350px; display: flex; flex-direction: column; }
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
        <h1>LURAPH-STYLE VM OBFUSCATOR</h1>
        <div class="pane-group">
            <div class="pane">
                <label for="inputCode">Raw Lua Script:</label>
                <textarea id="inputCode" placeholder="Paste your raw Lua source here..."></textarea>
            </div>
            <div class="pane">
                <label for="outputCode">Virtual Machine Bytecode Output:</label>
                <textarea id="outputCode" placeholder="Virtualized script will appear here..." readonly></textarea>
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

            status.innerText = "Compiling into Virtual Machine instructions...";
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
                    status.innerText = "Success! Bytecode VM generated.";
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
    
    protected = compile_luraph_vm(code)
    return jsonify({"success": True, "obfuscated": protected})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
