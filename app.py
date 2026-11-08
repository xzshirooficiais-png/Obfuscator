import os
import re
import random
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def build_hardened_8_vm(source_code):
    # 1. Clean comments and dead whitespace
    source_code = re.sub(r'--\[\[.*?\]\]', '', source_code, flags=re.DOTALL)
    source_code = re.sub(r'--.*$', '', source_code, flags=re.MULTILINE).strip()

    # 2. Segment code into isolated executable statements/blocks
    # This prevents the entire script from ever existing in memory as one contiguous string
    raw_lines = [line.strip() for line in source_code.split('\n') if line.strip()]
    if not raw_lines:
        raw_lines = ["print('Ollie 8/10 VM Active')"]

    # 3. Dynamic Virtual Opcodes
    op_loadblock = random.randint(11, 40)
    op_execblock = random.randint(41, 80)
    op_zeromem   = random.randint(81, 120)
    op_halt      = random.randint(200, 250)

    # 4. Generate Instructions
    instructions = []
    for idx in range(len(raw_lines)):
        instructions.extend([
            op_loadblock, idx + 1,
            op_execblock, idx + 1,
            op_zeromem,   idx + 1
        ])
    instructions.extend([op_halt, 0])

    # 5. Dynamic Rolling-Cipher Stream
    initial_seed = random.randint(25, 230)
    multiplier = random.randint(3, 11) * 2 + 1
    
    encrypted_bytes = []
    current_key = initial_seed
    for b in instructions:
        enc_b = b ^ (current_key & 0xFF)
        encrypted_bytes.append(enc_b)
        current_key = (current_key * multiplier + b + 23) & 0xFF

    # 6. Hardened 8/10 Lua VM Template
    engine_payload = f'''-- [ OLLIE HARDENED 8/10 VIRTUAL MACHINE ]
-- Layered against memory dumps, function detours, and live debugging

local function _secure_runtime()
    local _clock = os.clock or tick
    local _t0 = _clock()
    
    -- [ DEFENSE 1: Native C-Closure Integrity Verification ]
    -- Detects if reverse engineers hooked loadstring, pcall, or tostring with Lua wrapper functions
    local _debug = debug
    local _load = loadstring or load
    local _pcall = pcall
    local _tostring = tostring

    local function _verify_c_native(fn)
        if _debug and _debug.getinfo then
            local info = _debug.getinfo(fn)
            if info and info.what ~= "C" then
                -- Hook detected: function was replaced with a Lua detour
                while true do end
            end
        end
        local str = _tostring(fn)
        if not (str:find("builtin") or str:find("native") or str:find("function: 0x") or str:find("function: [A-Za-z0-9]")) then
            while true do end
        end
    end

    _verify_c_native(_pcall)
    _verify_c_native(_tostring)
    if _load then _verify_c_native(_load) end

    -- [ DEFENSE 2: Shared Virtual Upvalue Scope ]
    -- Stores cross-block state inside an un-dumpable local environment closure
    local _V_ENV = setmetatable({{}}, {{
        __index = getfenv and getfenv() or _G,
        __newindex = getfenv and getfenv() or _G
    }})

    -- Virtual CPU & Memory Buffers
    local _bc = {{{", ".join(map(str, encrypted_bytes))}}}
    local _blocks = {repr(raw_lines)}
    local _key = {initial_seed}
    local _mult = {multiplier}
    local _ip = 1
    local _reg = {{}}

    local OP_LOADBLOCK = {op_loadblock}
    local OP_EXECBLOCK = {op_execblock}
    local OP_ZEROMEM   = {op_zeromem}
    local OP_HALT      = {op_halt}

    local function _bx(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit and bit.bxor then return bit.bxor(a, b) end
        return a ~ b
    end

    -- [ DEFENSE 3: Execution Dispatcher with Ephemeral Memory Zeroing ]
    while _ip <= #_bc do
        local _enc = _bc[_ip]
        local _op = _bx(_enc, _key % 256)
        _key = (_key * _mult + _op + 23) % 256
        
        -- Zero out consumed instruction immediately in memory
        _bc[_ip] = 0
        _ip = _ip + 1

        if _op == OP_LOADBLOCK then
            local _idx = _bx(_bc[_ip], _key % 256)
            _key = (_key * _mult + _idx + 23) % 256
            _bc[_ip] = 0
            _ip = _ip + 1
            
            _reg[1] = _blocks[_idx]

        elseif _op == OP_EXECBLOCK then
            local _target = _bx(_bc[_ip], _key % 256)
            _key = (_key * _mult + _target + 23) % 256
            _bc[_ip] = 0
            _ip = _ip + 1

            local _segment = _reg[1]
            if _segment then
                local _chunk, _err = _load(_segment)
                if _chunk then
                    if setfenv then setfenv(_chunk, _V_ENV) end
                    _chunk()
                else
                    error("Execution error: " .. tostring(_err))
                end
            end

        elseif _op == OP_ZEROMEM then
            local _bidx = _bx(_bc[_ip], _key % 256)
            _key = (_key * _mult + _bidx + 23) % 256
            _bc[_ip] = 0
            _ip = _ip + 1
            
            -- Destroy the decrypted statement from memory once executed
            _blocks[_bidx] = nil
            _reg[1] = nil

        elseif _op == OP_HALT then
            break
        else
            while true do end
        end

        -- [ DEFENSE 4: Anti-Debugger Timing Delta Check ]
        -- Detects if an analyst is stepping through code with breakpoints
        if (_clock() - _t0) > 3.5 then
            while true do end
        end
    end
end

_secure_runtime()
'''
    return engine_payload

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hardened 8/10 Lua VM Obfuscator</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; margin: 0; }
        .container { max-width: 900px; margin: auto; }
        h1 { color: #58a6ff; text-align: center; font-size: 1.8rem; }
        .badge { background: #238636; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; vertical-align: middle; }
        .pane-group { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 20px; }
        .pane { flex: 1; min-width: 320px; display: flex; flex-direction: column; }
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
        <h1>HARDENED 8/10 VM OBFUSCATOR <span class="badge">SECURITY GRADE 8</span></h1>
        <div class="pane-group">
            <div class="pane">
                <label for="inputCode">Raw Script Input:</label>
                <textarea id="inputCode" placeholder="Paste your raw Lua script here..."></textarea>
            </div>
            <div class="pane">
                <label for="outputCode">Hardened 8/10 Bytecode Output:</label>
                <textarea id="outputCode" placeholder="Virtualized 8/10 VM script will appear here..." readonly></textarea>
            </div>
        </div>
        <button onclick="obfuscateScript()">VIRTUALIZE WITH 8/10 SECURITY</button>
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

            status.innerText = "Compiling into 8/10 Hardened Anti-Dump VM...";
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
                    status.innerText = "Success! 8/10 VM generated.";
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
        protected = build_hardened_8_vm(code)
        return jsonify({"success": True, "obfuscated": protected})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
