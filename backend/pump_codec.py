"""Read-only protocol decoder pinned to the official Pump IDL.

Source: pump-fun/pump-public-docs, idl/pump.json
Commit: e0687ae9b7e064a0f54efc7297c65eecfbba3a8f
Only the backwards-compatible prefixes below are decoded. No fee instruction
is built, modified, or submitted by this module.
"""
import base64
import re
import struct
import base58
from solders.pubkey import Pubkey

IDL_COMMIT = 'e0687ae9b7e064a0f54efc7297c65eecfbba3a8f'
PUMP_PROGRAM = '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
TOKEN_2022 = 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'
TOKEN_LEGACY = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
ATA_PROGRAM = 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'
SYSTEM_PROGRAM = '11111111111111111111111111111111'
METADATA_PROGRAM = 'metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'
MAYHEM_PROGRAM = 'MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e'
SOL_MINT = 'So11111111111111111111111111111111111111112'
CREATE = bytes([24,30,200,40,5,28,7,119])
CREATE_V2 = bytes([214,144,76,236,95,139,49,180])
CREATE_EVENT = bytes([27,114,169,77,222,235,99,118])
TRADE_EVENT = bytes([189,219,127,211,78,230,97,238])
BONDING = bytes([23,183,248,55,96,216,172,96])

def pda(seeds, program=PUMP_PROGRAM):
    return str(Pubkey.find_program_address(seeds, Pubkey.from_string(program))[0])

def curve_address(mint):
    return pda([b'bonding-curve', bytes(Pubkey.from_string(mint))])

class Reader:
    def __init__(self, raw, offset=8): self.raw, self.offset = raw, offset
    def take(self, count):
        if count < 0 or self.offset + count > len(self.raw): raise ValueError('Truncated Pump data')
        value = self.raw[self.offset:self.offset+count]; self.offset += count
        return value
    def string(self, maximum=2048):
        length = struct.unpack('<I', self.take(4))[0]
        if length > maximum: raise ValueError('Pump text exceeds protocol bounds')
        return self.take(length).decode('utf-8').rstrip('\0')
    def key(self): return base58.b58encode(self.take(32)).decode()
    def number(self): return struct.unpack('<Q', self.take(8))[0]
    def boolean(self):
        value = self.take(1)[0]
        if value not in (0,1): raise ValueError('Invalid Pump boolean')
        return bool(value)

def decode_create(data):
    raw = base58.b58decode(data)
    if raw[:8] not in (CREATE, CREATE_V2): return None
    r = Reader(raw)
    result = {'version':'create_v2' if raw[:8] == CREATE_V2 else 'create',
              'name':r.string(128), 'symbol':r.string(64), 'uri':r.string()}
    result['instruction_creator'] = r.key() if len(raw)-r.offset >= 32 else None
    if raw[:8] == CREATE_V2:
        if not result['instruction_creator']: raise ValueError('Missing Pump creator')
        result['is_mayhem_mode'] = r.boolean()
    elif len(raw)-r.offset != 0:
        raise ValueError('Unsupported legacy Pump create layout')
    return result

def decode_create_event(raw):
    if raw[:8] != CREATE_EVENT: return None
    r = Reader(raw)
    return {'name':r.string(128), 'symbol':r.string(64), 'uri':r.string(),
            'mint':r.key(), 'bonding_curve':r.key(), 'user':r.key()}

def decode_curve(raw):
    if raw[:8] != BONDING: raise ValueError('Not a Pump bonding curve')
    r = Reader(raw)
    value = dict(zip(['virtual_token_reserves','virtual_quote_reserves','real_token_reserves',
                     'real_quote_reserves','token_total_supply'], [r.number() for _ in range(5)]))
    value['complete'] = r.boolean()
    value['pump_creator'] = r.key() if len(raw) >= 81 else None
    # Optional extension fields were appended over successive program versions.
    value['is_mayhem_mode'] = r.boolean() if len(raw) >= 82 else False
    value['is_cashback_coin'] = r.boolean() if len(raw) >= 83 else False
    value['quote_mint'] = r.key() if len(raw) >= 115 else SYSTEM_PROGRAM
    return value

def pump_event_payloads(tx):
    """Trust only runtime-attributed Pump logs; discard failed call trees."""
    stack, committed = [], []
    for line in (tx.get('meta') or {}).get('logMessages') or []:
        start = re.fullmatch(r'Program ([1-9A-HJ-NP-Za-km-z]+) invoke \[(\d+)\]', line)
        end = re.fullmatch(r'Program ([1-9A-HJ-NP-Za-km-z]+) (success|failed:.*)', line)
        if start:
            if int(start[2]) != len(stack)+1: return []
            stack.append({'program':start[1], 'events':[]})
        elif end:
            if not stack or stack[-1]['program'] != end[1]: return []
            frame = stack.pop()
            if end[2] == 'success':
                if stack: stack[-1]['events'].extend(frame['events'])
                else: committed.extend(frame['events'])
        elif line.startswith('Program data: ') and stack and stack[-1]['program'] == PUMP_PROGRAM:
            try: stack[-1]['events'].append(base64.b64decode(line[14:], validate=True))
            except ValueError: continue
    return committed  # Incomplete call frames are never accepted.

def decode_trade(raw):
    if raw[:8] != TRADE_EVENT: return None
    r = Reader(raw)
    return {'mint':r.key(), 'sol_amount_raw':r.number(), 'token_amount_raw':r.number(),
            'is_buy':r.boolean(), 'wallet':r.key(), 'timestamp':r.number()}