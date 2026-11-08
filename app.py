import os
import re
import random
import string
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ---------------------------------------------------------------------------
# UTILITY — name generator, constant obfuscation, string encoding
# ---------------------------------------------------------------------------

def _rname(prefix="", length=12):
    """Intention-revealing obfuscated name: prefix + random alnum tail."""
    tail = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return (prefix or "_") + tail


def _encode_string(s):
    """
    Encode a Lua string literal as a char-code table reassembled at runtime.
    Avoids any string literal appearing verbatim in the output.
    """
    codes = ", ".join(str(ord(c)) for c in s)
    n = _rname("_s")
    t = _rname("_t")
    return (
        f"(function() local {t}={{{{ {codes} }}}} local {n}='' "
        f"for _,v in ipairs({t}) do {n}={n}..string.char(v) end return {n} end)()"
    )


def _fold_number(n):
    """
    Constant folding: express an integer as a runtime arithmetic expression.
    e.g. 42 → ((6*7)+0) so the literal never appears.
    """
    if n == 0:
        return "0"
    a = random.randint(2, 15)
    b = n // a
    rem = n - a * b
    sign = "+" if rem >= 0 else "-"
    return f"(({a}*{b}){sign}{abs(rem)})"


# ---------------------------------------------------------------------------
# STAGE 1 — Tokenise source into executable segments (Luraph-style chunking)
# ---------------------------------------------------------------------------

def _segment(source: str) -> list[str]:
    """
    Split cleaned source into individual executable statements/blocks.
    Multi-line constructs (function … end, do … end, if … end, repeat … until)
    are kept intact so each loadstring call receives a complete chunk.
    Mirrors how Luraph partitions the AST before re-emitting per-chunk.
    """
    source = re.sub(r'--\[\[.*?\]\]', '', source, flags=re.DOTALL)
    source = re.sub(r'--.*$', '', source, flags=re.MULTILINE).strip()

    segments = []
    buf = []
    depth = 0  # tracks open block nesting

    block_open  = re.compile(r'\b(function|do|then|else|elseif|repeat)\b')
    block_close = re.compile(r'\b(end|until)\b')

    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        opens  = len(block_open.findall(stripped))
        closes = len(block_close.findall(stripped))

        # heuristic: subtract paired open+close on same line
        net = opens - closes
        depth += net

        buf.append(line)

        if depth <= 0:
            segments.append('\n'.join(buf).strip())
            buf   = []
            depth = 0

    if buf:
        segments.append('\n'.join(buf).strip())

    return segments or ["-- nop"]


# ---------------------------------------------------------------------------
# STAGE 2 — Opcode table (Luraph-style: randomised per-build instruction set)
# ---------------------------------------------------------------------------

class OpcodeTable:
    """
    Per-build opcode assignment.  Every build randomises the integer values
    so static signatures on the dispatcher never match across builds.
    Mirrors Luraph's per-compile opcode shuffling.
    """
    _NAMES = [
        "PUSH_CHUNK",   # load a segment string into the register file
        "CALL_CHUNK",   # execute the string in register[N] via loadstring
        "WIPE_CHUNK",   # zero out segment and register after execution
        "JMP",          # unconditional jump (ip ← operand)
        "JMP_IF_ERR",   # jump if last pcall returned false
        "STORE_K",      # store a constant into a named register
        "LOAD_K",       # read a named register
        "HALT",         # stop the VM
    ]

    def __init__(self):
        pool = random.sample(range(0x10, 0xF0), len(self._NAMES))
        self._map = dict(zip(self._NAMES, pool))

    def __getitem__(self, name):
        return self._map[name]

    def all(self):
        return dict(self._map)


# ---------------------------------------------------------------------------
# STAGE 3 — Instruction stream encoder (rolling XOR, same logic as before
#            but now encoding richer opcodes)
# ---------------------------------------------------------------------------

def _encode_stream(instructions: list[int], seed: int, mult: int) -> list[int]:
    out = []
    key = seed
    for b in instructions:
        enc = b ^ (key & 0xFF)
        out.append(enc)
        key = (key * mult + b + 23) & 0xFF
    return out


# ---------------------------------------------------------------------------
# STAGE 4 — Emit the Luraph-style Lua VM wrapper
# ---------------------------------------------------------------------------

def build_luraph_vm(source_code: str) -> str:
    segments  = _segment(source_code)
    ops       = OpcodeTable()

    seed      = random.randint(30, 220)
    mult      = random.randint(2, 7) * 2 + 1   # odd multiplier
    err_flag  = _rname("_ef")

    # --- build flat instruction stream ---
    # Format: [OP, ARG, OP, ARG, ...]
    # ARG for PUSH_CHUNK / CALL_CHUNK / WIPE_CHUNK = 1-based segment index
    raw = []
    for i in range(len(segments)):
        raw += [ops["PUSH_CHUNK"], i + 1]
        raw += [ops["CALL_CHUNK"], i + 1]
        raw += [ops["JMP_IF_ERR"], len(segments) * 6 + 2]  # jump past halt to error block
        raw += [ops["WIPE_CHUNK"], i + 1]
    raw += [ops["HALT"], 0]
    # error handler block (jumped to on pcall failure)
    raw += [ops["STORE_K"], 0xFF]   # 0xFF sentinel = "in error handler"
    raw += [ops["HALT"], 0]

    encoded = _encode_stream(raw, seed, mult)

    # --- obfuscate segment strings ---
    lua_seg_table_entries = []
    for seg in segments:
        lua_seg_table_entries.append(_encode_string(seg))
    lua_seg_table = "{\n        " + ",\n        ".join(lua_seg_table_entries) + "\n    }"

    # --- fold all opcode constants ---
    op_vars = {}
    for name, val in ops.all().items():
        op_vars[name] = (_rname("_op"), _fold_number(val))

    # --- generate randomised local names for everything ---
    N = {
        "runtime":    _rname("_rt"),
        "bc":         _rname("_bc"),
        "segs":       _rname("_sg"),
        "reg":        _rname("_rg"),
        "ip":         _rname("_ip"),
        "key":        _rname("_ky"),
        "mult":       _rname("_ml"),
        "clock":      _rname("_ck"),
        "t0":         _rname("_t0"),
        "bxor":       _rname("_bx"),
        "op":         _rname("_op_"),
        "enc":        _rname("_en"),
        "arg":        _rname("_ar"),
        "chunk":      _rname("_ch"),
        "err":        _rname("_er"),
        "env":        _rname("_ev"),
        "pcall":      _rname("_pc"),
        "load":       _rname("_ld"),
        "tostr":      _rname("_ts"),
        "dbg":        _rname("_dg"),
        "verifyfn":   _rname("_vf"),
        "errflag":    err_flag,
    }

    # --- op-var declarations ---
    op_decls = "\n    ".join(
        f"local {vname} = {expr}"
        for _, (vname, expr) in op_vars.items()
    )
    # shorthand: map op name → its local variable name
    def OP(name):
        return op_vars[name][0]

    # --- encoded bytecode literal ---
    bc_literal = "{" + ", ".join(str(b) for b in encoded) + "}"

    seed_expr = _fold_number(seed)
    mult_expr = _fold_number(mult)

    payload = f'''-- ================================================================
-- LURAPH-STYLE HARDENED VM  (randomised opcodes, constant folding,
--   rolling-XOR bytecode, per-chunk ephemeral execution)
-- ================================================================

local function {N["runtime"]}()
    -- [ C-NATIVE INTEGRITY: detect Lua-wrapper detours ]
    local {N["dbg"]}    = debug
    local {N["load"]}   = loadstring or load
    local {N["pcall"]}  = pcall
    local {N["tostr"]}  = tostring

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

    -- [ OPCODE TABLE — randomised per build, constant-folded ]
    {op_decls}

    -- [ RUNTIME REGISTERS ]
    local {N["bc"]}   = {bc_literal}
    local {N["segs"]} = {lua_seg_table}
    local {N["reg"]}  = {{}}
    local {N["ip"]}   = 1
    local {N["key"]}  = {seed_expr}
    local {N["mult"]} = {mult_expr}
    local {N["errflag"]} = false

    -- [ SHARED ENV: upvalue-locked, redirects globals into closure scope ]
    local {N["env"]} = setmetatable({{}}, {{
        __index    = getfenv and getfenv() or _G,
        __newindex = getfenv and getfenv() or _G,
    }})

    -- [ XOR HELPER — prefers bit32, falls back to Lua 5.3+ ~ ]
    local function {N["bxor"]}(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit   and bit.bxor   then return bit.bxor(a, b)   end
        return a ~ b
    end

    -- [ DISPATCH LOOP ]
    while {N["ip"]} <= #{N["bc"]} do
        -- decode opcode
        local {N["enc"]} = {N["bc"]}[{N["ip"]}]
        local {N["op"]}  = {N["bxor"]}({N["enc"]}, {N["key"]} % 256)
        {N["key"]}       = ({N["key"]} * {N["mult"]} + {N["op"]} + 23) % 256
        {N["bc"]}[{N["ip"]}] = 0           -- consume + zero immediately
        {N["ip"]}        = {N["ip"]} + 1

        -- decode operand
        local {N["arg"]} = {N["bxor"]}({N["bc"]}[{N["ip"]}], {N["key"]} % 256)
        {N["key"]}       = ({N["key"]} * {N["mult"]} + {N["arg"]} + 23) % 256
        {N["bc"]}[{N["ip"]}] = 0
        {N["ip"]}        = {N["ip"]} + 1

        -- [ PUSH_CHUNK: load segment string into register ]
        if {N["op"]} == {OP("PUSH_CHUNK")} then
            {N["reg"]}[1] = {N["segs"]}[{N["arg"]}]

        -- [ CALL_CHUNK: compile + execute via pcall, isolated env ]
        elseif {N["op"]} == {OP("CALL_CHUNK")} then
            local seg = {N["reg"]}[1]
            if seg then
                local {N["chunk"]}, {N["err"]} = {N["load"]}(seg)
                if {N["chunk"]} then
                    if setfenv then setfenv({N["chunk"]}, {N["env"]}) end
                    local ok, run_err = {N["pcall"]}({N["chunk"]})
                    if not ok then
                        {N["errflag"]} = true
                        -- store error message for the error block
                        {N["reg"]}[2] = tostring(run_err)
                    end
                else
                    error("VM compile error: " .. tostring({N["err"]}))
                end
            end

        -- [ JMP_IF_ERR: branch if last call faulted ]
        elseif {N["op"]} == {OP("JMP_IF_ERR")} then
            if {N["errflag"]} then
                {N["ip"]} = {N["arg"]}
                {N["errflag"]} = false
            end

        -- [ WIPE_CHUNK: zero out segment + register after execution ]
        elseif {N["op"]} == {OP("WIPE_CHUNK")} then
            {N["segs"]}[{N["arg"]}] = nil
            {N["reg"]}[1]  = nil

        -- [ STORE_K: internal sentinel store ]
        elseif {N["op"]} == {OP("STORE_K")} then
            {N["reg"]}[{N["arg"]}] = true

        -- [ HALT ]
        elseif {N["op"]} == {OP("HALT")} then
            break

        -- [ UNKNOWN OPCODE: VM integrity violation ]
        else
            while true do end
        end

        -- [ TIMING CHECK: >3.5s between ticks = debugger stepping ]
        if ({N["clock"]}() - {N["t0"]}) > 3.5 then
            while true do end
        end
    end
end

{N["runtime"]}()
'''
    return payload


# ---------------------------------------------------------------------------
# Flask app — identical surface to the original
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
