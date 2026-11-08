import random
import re

def build_advanced_vm(source_code):
    # 1. Clean comments and dead padding
    source_code = re.sub(r'--\[\[.*?\]\]', '', source_code, flags=re.DOTALL)
    source_code = re.sub(r'--.*$', '', source_code, flags=re.MULTILINE).strip()

    # 2. Dynamic Opcode Shuffling per build
    op_loadk = random.randint(10, 45)
    op_concat = random.randint(46, 85)
    op_exec = random.randint(86, 130)
    op_halt = random.randint(200, 254)

    # 3. Constant Splitting (Chunks string to defeat monolithic memory scans)
    chunk_size = random.randint(4, 8)
    chunks = [source_code[i:i+chunk_size] for i in range(0, len(source_code), chunk_size)]
    
    # 4. Generate Raw Instruction Sequence
    # Sequence: LOADK chunks into registers, CONCAT them, EXEC, HALT
    instructions = []
    for idx, _ in enumerate(chunks):
        instructions.extend([op_loadk, idx + 1, idx + 1]) # OP, Reg, ConstIdx
    
    instructions.extend([op_concat, len(chunks)]) # OP, TotalChunks
    instructions.extend([op_exec, 1])            # OP, TargetReg
    instructions.extend([op_halt, 0])            # OP, Padding

    # 5. Rolling-Cipher Bytecode Encryption (Each byte's key depends on previous byte)
    initial_seed = random.randint(20, 220)
    multiplier = random.randint(3, 11) * 2 + 1 # odd multiplier for full ring
    
    encrypted_bytes = []
    current_key = initial_seed
    for b in instructions:
        enc_b = b ^ (current_key & 0xFF)
        encrypted_bytes.append(enc_b)
        # Mutate rolling state
        current_key = (current_key * multiplier + b + 17) & 0xFF

    # 6. Build the Hardened Lua VM Engine
    engine_payload = f'''-- [ OLLIE NEXT-GEN VIRTUAL MACHINE ]
-- Hardened against memory dumps and detours

local function _init_guard()
    -- Anti-Hook / Anti-Dump Integrity Shield
    local _tostring = tostring
    local _pcall = pcall
    
    -- Detect if core execution hooks are tampered
    local function _check_closure(fn)
        local str = _tostring(fn)
        return str:find("builtin") or str:find("native") or str:find("function: 0x") or str:find("function: [A-Za-z0-9]")
    end
    
    if not _check_closure(pcall) or not _check_closure(tostring) then
        while true do end -- Infinite lock on hook detection
    end
end
_init_guard()

local function _dispatch()
    local _bc = {{{", ".join(map(str, encrypted_bytes))}}}
    local _const_pool = {repr(chunks)}
    local _state_key = {initial_seed}
    local _mult = {multiplier}
    
    -- Virtual CPU registers
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
    
    -- Execution State Dispatcher (Flattened loop)
    while _ip <= #_bc do
        -- Decrypt byte using current rolling cipher state
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
            -- Opaque panic trap
            while true do end
        end
    end
end

_dispatch()
'''
    return engine_payload

if __name__ == "__main__":
    sample = "print('Virtualization running past Luraph standards!')"
    print(build_advanced_vm(sample))
