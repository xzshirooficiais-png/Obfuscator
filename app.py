import os
import re
import random
import string
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ---------------------------------------------------------------------------
# UTILITY
# ---------------------------------------------------------------------------

def _rname(prefix="", length=12):
    tail = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return (prefix or "_") + tail


def _encode_string(s):
    codes = ", ".join(str(ord(c)) for c in s)
    n = _rname("_s")
    t = _rname("_t")
    return (
        f"(function() local {t}={{{codes}}} local {n}='' "
        f"for _,v in ipairs({t}) do {n}={n}..string.char(v) end return {n} end)()"
    )


def _fold_number(n):
    if n == 0:
        return "0"
    a = random.randint(2, 15)
    b = n // a
    rem = n - a * b
    sign = "+" if rem >= 0 else "-"
    return f"(({a}*{b}){sign}{abs(rem)})"


# ---------------------------------------------------------------------------
# STAGE 1 — Segmenter
# ---------------------------------------------------------------------------

def _segment(source: str) -> list[str]:
    source = re.sub(r'--\[\[.*?\]\]', '', source, flags=re.DOTALL)
    source = re.sub(r'--.*$',         '', source, flags=re.MULTILINE).strip()

    block_open  = re.compile(r'\b(function|do|then|else|elseif|repeat)\b')
    block_close = re.compile(r'\b(end|until)\b')

    segments, buf, depth = [], [], 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        opens  = len(block_open.findall(stripped))
        closes = len(block_close.findall(stripped))
        depth += opens - closes
        buf.append(line)
        if depth <= 0:
            segments.append('\n'.join(buf).strip())
            buf, depth = [], 0

    if buf:
        segments.append('\n'.join(buf).strip())

    return segments or ["-- nop"]


# ---------------------------------------------------------------------------
# STAGE 2 — Opcode table
# ---------------------------------------------------------------------------

class OpcodeTable:
    _NAMES = ["PUSH_CHUNK", "CALL_CHUNK", "WIPE_CHUNK",
              "JMP", "JMP_IF_ERR", "HALT"]

    def __init__(self):
        pool = random.sample(range(0x10, 0xF0), len(self._NAMES))
        self._map = dict(zip(self._NAMES, pool))

    def __getitem__(self, n): return self._map[n]
    def all(self):            return dict(self._map)


# ---------------------------------------------------------------------------
# STAGE 3 — Encode a flat list of integers with rolling XOR
# ---------------------------------------------------------------------------

def _encode_stream(instructions: list[int], seed: int, mult: int) -> list[int]:
    out, key = [], seed
    for b in instructions:
        out.append(b ^ (key & 0xFF))
        key = (key * mult + b + 23) & 0xFF
    return out


# ---------------------------------------------------------------------------
# STAGE 4 — Build instruction stream
#   Each instruction is exactly 2 bytes: [OPCODE, ARG].
#   HALT and opcodes with no meaningful arg still emit 2 bytes (arg=0)
#   so the ip always advances by exactly 2.  No variable-length weirdness.
# ---------------------------------------------------------------------------

def _build_stream(segments, ops):
    """
    Returns (raw_instructions, error_handler_ip).
    error_handler_ip is the byte index (0-based) where the error block starts.
    The error block is a bare HALT so the script just stops cleanly on fault.
    """
    raw = []
    for i in range(len(segments)):
        raw += [ops["PUSH_CHUNK"], i + 1]   # 2 bytes
        raw += [ops["CALL_CHUNK"], i + 1]   # 2 bytes
        raw += [ops["JMP_IF_ERR"], 0]       # 2 bytes — target filled below
        raw += [ops["WIPE_CHUNK"], i + 1]   # 2 bytes

    # normal HALT
    halt_ip = len(raw)
    raw += [ops["HALT"], 0]

    # error handler block — jumped to by JMP_IF_ERR
    err_ip = len(raw)             # byte offset of this block
    raw += [ops["HALT"], 0]

    # back-patch every JMP_IF_ERR with the real target
    # JMP_IF_ERR is at positions 4, 10, 16, … (every 8 bytes starting at 4)
    for i in range(len(segments)):
        jmp_arg_pos = i * 8 + 5  # byte index of the ARG byte of JMP_IF_ERR
        raw[jmp_arg_pos] = err_ip

    return raw, err_ip


# ---------------------------------------------------------------------------
# STAGE 5 — Emit Lua VM
# ---------------------------------------------------------------------------

def build_luraph_vm(source_code: str) -> str:
    segments = _segment(source_code)
    ops      = OpcodeTable()
    seed     = random.randint(30, 220)
    mult     = random.randint(2, 7) * 2 + 1   # odd

    raw, err_ip = _build_stream(segments, ops)
    encoded     = _encode_stream(raw, seed, mult)

    # encode segment strings
    lua_segs = "{\n        " + ",\n        ".join(
        _encode_string(s) for s in segments
    ) + "\n    }"

    # fold opcode constants
    op_vars = {name: (_rname("_op"), _fold_number(val))
               for name, val in ops.all().items()}

    def OP(name): return op_vars[name][0]

    op_decls = "\n    ".join(
        f"local {vname} = {expr}"
        for _, (vname, expr) in op_vars.items()
    )

    # random local names
    N = {k: _rname(f"_{k[:2]}") for k in [
        "runtime","bc","segs","reg","ip","key","mult",
        "clock","t0","bxor","op","enc","arg","chunk",
        "err","env","pcall","load","tostr","dbg","verifyfn","errflag"
    ]}

    bc_literal  = "{" + ", ".join(str(b) for b in encoded) + "}"
    seed_expr   = _fold_number(seed)
    mult_expr   = _fold_number(mult)
    err_ip_expr = _fold_number(err_ip)

    payload = f'''-- ================================================================
-- LURAPH-STYLE HARDENED VM
-- ================================================================

local function {N["runtime"]}()

    -- [ C-NATIVE INTEGRITY ]
    local {N["dbg"]}   = debug
    local {N["load"]}  = loadstring or load
    local {N["pcall"]} = pcall
    local {N["tostr"]} = tostring

    local function {N["verifyfn"]}(fn)
        if {N["dbg"]} and {N["dbg"]}.getinfo then
            local info = {N["dbg"]}.getinfo(fn)
            if info and info.what ~= "C" then while true do end end
        end
        local s = {N["tostr"]}(fn)
        if not (s:find("builtin") or s:find("native") or s:find("function: 0x")) then
            while true do end
        end
    end
    {N["verifyfn"]}({N["pcall"]})
    {N["verifyfn"]}({N["tostr"]})
    if {N["load"]} then {N["verifyfn"]}({N["load"]}) end

    -- [ TIMING ANTI-DEBUG ]
    local {N["clock"]} = os.clock or tick
    local {N["t0"]}    = {N["clock"]}()

    -- [ OPCODE TABLE ]
    {op_decls}

    -- [ VM STATE ]
    local {N["bc"]}      = {bc_literal}
    local {N["segs"]}    = {lua_segs}
    local {N["reg"]}     = {{}}
    local {N["ip"]}      = 1
    local {N["key"]}     = {seed_expr}
    local {N["mult"]}    = {mult_expr}
    local {N["errflag"]} = false

    -- [ SHARED ENV ]
    local {N["env"]} = setmetatable({{}}, {{
        __index    = getfenv and getfenv() or _G,
        __newindex = getfenv and getfenv() or _G,
    }})

    -- [ XOR HELPER ]
    local function {N["bxor"]}(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit   and bit.bxor   then return bit.bxor(a, b)   end
        return a ~ b
    end

    -- [ DISPATCH LOOP ]
    -- Every instruction is exactly 2 bytes: [OPCODE][ARG].
    -- ip always advances by 2 — no variable-length decode.
    while {N["ip"]} <= #{N["bc"]} do

        -- decode opcode (byte 1)
        local {N["enc"]} = {N["bc"]}[{N["ip"]}]
        local {N["op"]}  = {N["bxor"]}({N["enc"]}, {N["key"]} % 256)
        {N["key"]}       = ({N["key"]} * {N["mult"]} + {N["op"]} + 23) % 256
        {N["bc"]}[{N["ip"]}] = 0
        {N["ip"]} = {N["ip"]} + 1

        -- decode arg (byte 2) — always consumed regardless of opcode
        local {N["arg"]} = {N["bxor"]}({N["bc"]}[{N["ip"]}], {N["key"]} % 256)
        {N["key"]}       = ({N["key"]} * {N["mult"]} + {N["arg"]} + 23) % 256
        {N["bc"]}[{N["ip"]}] = 0
        {N["ip"]} = {N["ip"]} + 1

        -- [ PUSH_CHUNK ]
        if {N["op"]} == {OP("PUSH_CHUNK")} then
            {N["reg"]}[1] = {N["segs"]}[{N["arg"]}]

        -- [ CALL_CHUNK ]
        elseif {N["op"]} == {OP("CALL_CHUNK")} then
            local seg = {N["reg"]}[1]
            if seg then
                local {N["chunk"]}, {N["err"]} = {N["load"]}(seg)
                if {N["chunk"]} then
                    if setfenv then setfenv({N["chunk"]}, {N["env"]}) end
                    local ok, run_err = {N["pcall"]}({N["chunk"]})
                    if not ok then
                        {N["errflag"]} = true
                        {N["reg"]}[2]  = tostring(run_err)
                    end
                else
                    -- compile error: surface it and halt
                    error("VM compile error on segment: " .. tostring({N["err"]}))
                end
            end

        -- [ JMP_IF_ERR: ip is 1-based, arg is 0-based byte offset → +1 ]
        elseif {N["op"]} == {OP("JMP_IF_ERR")} then
            if {N["errflag"]} then
                {N["ip"]}      = {N["arg"]} + 1
                {N["errflag"]} = false
            end

        -- [ WIPE_CHUNK ]
        elseif {N["op"]} == {OP("WIPE_CHUNK")} then
            {N["segs"]}[{N["arg"]}] = nil
            {N["reg"]}[1]  = nil

        -- [ HALT ]
        elseif {N["op"]} == {OP("HALT")} then
            break

        -- [ UNKNOWN OPCODE: integrity violation ]
        else
            while true do end
        end

        -- [ TIMING CHECK ]
        if ({N["clock"]}() - {N["t0"]}) > 3.5 then
            while true do end
        end
    end
end

{N["runtime"]}()
'''
    return payload


# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Luraph-Style Hardened VM Obfuscator</title>
    <style>
        * { box-sizing: border-box; }
        body { background: #0d1117; color: #c9d1d9; font-family: 'Cascadia Code', 'Fira Code', monospace; padding: 24px; margin: 0; }
        .container { max-width: 980px; margin: auto; }
        h1 { color: #58a6ff; text-align: center; font-size: 1.6rem; letter-spacing: 0.04em; }
        .badge { background: #238636; color: #fff; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; }
        .meta  { color: #8b949e; font-size: 0.78rem; text-align: center; margin-bottom: 20px; }
        .pane-group { display: flex; gap: 18px; flex-wrap: wrap; }
        .pane { flex: 1; min-width: 300px; display: flex; flex-direction: column; }
        label { margin-bottom: 6px; font-weight: bold; color: #8b949e; font-size: 0.85rem; }
        textarea { flex: 1; min-height: 380px; background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-family: inherit; font-size: 13px; resize: vertical; }
        textarea:focus { border-color: #58a6ff; outline: none; }
        button { background: #238636; color: #fff; border: none; padding: 12px; font-size: 15px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-top: 14px; width: 100%; transition: background .15s; }
        button:hover { background: #2ea043; }
        .status { text-align: center; margin-top: 8px; color: #f0883e; font-size: 0.85rem; min-height: 1.2em; }
        .features { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; justify-content: center; }
        .feat { background: #161b22; border: 1px solid #30363d; border-radius: 20px; padding: 4px 12px; font-size: 0.75rem; color: #79c0ff; }
    </style>
</head>
<body>
<div class="container">
    <h1>LURAPH-STYLE HARDENED VM <span class="badge">OLLIE BUILD</span></h1>
    <p class="meta">Randomised opcode table · Rolling-XOR bytecode · Constant folding · Per-chunk ephemeral exec · Anti-debug timing</p>
    <div class="features">
        <span class="feat">Opcode shuffle per build</span>
        <span class="feat">Constant folding</span>
        <span class="feat">String char-code encoding</span>
        <span class="feat">Randomised local names</span>
        <span class="feat">JMP_IF_ERR dispatcher</span>
        <span class="feat">C-native integrity check</span>
        <span class="feat">Ephemeral segment wipe</span>
        <span class="feat">Timing anti-debug</span>
    </div>
    <div class="pane-group">
        <div class="pane">
            <label>Raw Lua Input</label>
            <textarea id="inputCode" placeholder="Paste your Lua script here..."></textarea>
        </div>
        <div class="pane">
            <label>Hardened VM Output</label>
            <textarea id="outputCode" placeholder="Obfuscated output appears here..." readonly></textarea>
        </div>
    </div>
    <button onclick="run()">VIRTUALIZE</button>
    <div id="status" class="status"></div>
</div>
<script>
    async function run() {
        const code   = document.getElementById('inputCode').value;
        const status = document.getElementById('status');
        const out    = document.getElementById('outputCode');
        if (!code.trim()) { status.innerText = "Nothing to cook."; return; }
        status.innerText = "Virtualizing...";
        out.value = "";
        try {
            const r = await fetch('/obfuscate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });
            const d = await r.json();
            if (d.success) { out.value = d.obfuscated; status.innerText = "Done."; }
            else           { status.innerText = "Error: " + (d.error || "unknown"); }
        } catch(e) { status.innerText = "Network error."; }
    }
</script>
</body>
</html>"""


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
        result = build_luraph_vm(code)
        return jsonify({"success": True, "obfuscated": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
