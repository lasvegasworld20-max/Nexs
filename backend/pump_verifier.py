import base64
import base58
from fastapi import HTTPException
from solders.pubkey import Pubkey
from chain import rpc, confirmed_transaction, instructions
from pump_codec import (PUMP_PROGRAM, TOKEN_2022, TOKEN_LEGACY, ATA_PROGRAM, SYSTEM_PROGRAM,
                        METADATA_PROGRAM, MAYHEM_PROGRAM, pda, curve_address, decode_create,
                        decode_curve, decode_create_event, pump_event_payloads, IDL_COMMIT)

def validate_signature(signature):
    try:
        if len(base58.b58decode(signature)) != 64: raise ValueError()
    except (ValueError, TypeError): raise HTTPException(400, 'Invalid Solana transaction signature')

def verify_instruction_accounts(ix, decoded, mint):
    accounts = ix.get('accounts') or []
    v2 = decoded['version'] == 'create_v2'
    if len(accounts) < (16 if v2 else 14): raise ValueError('Missing Pump creation accounts')
    program = TOKEN_2022 if v2 else TOKEN_LEGACY
    curve = curve_address(mint)
    expected = {0:mint, 1:pda([b'mint-authority']), 2:curve,
                3:pda([bytes(Pubkey.from_string(curve)), bytes(Pubkey.from_string(program)), bytes(Pubkey.from_string(mint))], ATA_PROGRAM),
                4:pda([b'global'])}
    if v2:
        expected.update({6:SYSTEM_PROGRAM, 7:program, 8:ATA_PROGRAM, 9:MAYHEM_PROGRAM,
                         10:pda([b'global-params'], MAYHEM_PROGRAM), 11:pda([b'sol-vault'], MAYHEM_PROGRAM),
                         12:pda([b'mayhem-state',bytes(Pubkey.from_string(mint))], MAYHEM_PROGRAM),
                         14:pda([b'__event_authority']), 15:PUMP_PROGRAM})
    else:
        expected.update({5:METADATA_PROGRAM, 6:pda([b'metadata',bytes(Pubkey.from_string(METADATA_PROGRAM)),bytes(Pubkey.from_string(mint))], METADATA_PROGRAM),
                         8:SYSTEM_PROGRAM, 9:program, 10:ATA_PROGRAM, 11:'SysvarRent111111111111111111111111111111111',
                         12:pda([b'__event_authority']), 13:PUMP_PROGRAM})
    if any(accounts[index] != value for index,value in expected.items()):
        raise ValueError('Creation accounts do not match official Pump PDAs')
    return accounts[5 if v2 else 7], program, curve

async def verify_creation(mint, signature, wallet):
    validate_signature(signature)
    tx = await confirmed_transaction(signature)
    signers = {a['pubkey'] for a in tx['transaction']['message']['accountKeys'] if isinstance(a,dict) and a.get('signer')}
    candidates = []
    for ix in instructions(tx):
        if ix.get('programId') != PUMP_PROGRAM or not ix.get('data'): continue
        try:
            decoded = decode_create(ix['data'])
            if not decoded or (ix.get('accounts') or [None])[0] != mint: continue
            user, program, curve = verify_instruction_accounts(ix, decoded, mint)
            candidates.append((decoded, user, program, curve))
        except (ValueError, TypeError, IndexError): continue
    if len(candidates) != 1:
        raise HTTPException(400, 'This confirmed transaction does not contain a supported Pump.fun creation for this mint')
    decoded, user, program, curve = candidates[0]
    if wallet != user or wallet not in signers:
        raise HTTPException(403, 'Connect the same wallet that created this token on Pump.fun')
    events = []
    for payload in pump_event_payloads(tx):
        try:
            event = decode_create_event(payload)
            if event: events.append(event)
        except (ValueError, UnicodeError): continue
    matching = [e for e in events if e['mint']==mint and e['bonding_curve']==curve and e['user']==wallet
                and all(e[key]==decoded[key] for key in ('name','symbol','uri'))]
    if len(matching) != 1:
        raise HTTPException(400, 'A successful Pump.fun creation event could not be verified. Supply the original creation transaction.')
    result = await rpc('getMultipleAccounts', [[mint, curve], {'encoding':'base64','commitment':'confirmed'}])
    values = (result or {}).get('value') or []
    if len(values)!=2 or not values[0] or not values[1]: raise HTTPException(400, 'Mint or Pump.fun bonding curve is missing')
    if values[0]['owner']!=program or values[1]['owner']!=PUMP_PROGRAM:
        raise HTTPException(400, 'Account ownership does not match the official Pump.fun program')
    try:
        raw_mint = base64.b64decode(values[0]['data'][0], validate=True)
        curve_state = decode_curve(base64.b64decode(values[1]['data'][0], validate=True))
        if len(raw_mint)<82 or raw_mint[45] != 1: raise ValueError()
        supply, decimals = int.from_bytes(raw_mint[36:44], 'little'), raw_mint[44]
        if decimals!=6 or not decoded['name'] or not decoded['symbol']: raise ValueError()
    except (ValueError, IndexError, TypeError): raise HTTPException(400, 'Unsupported or invalid Pump.fun token account')
    return {'mint':mint, 'name':decoded['name'], 'symbol':decoded['symbol'], 'metadata_uri':decoded['uri'],
            'creator':wallet, 'creation_signature':signature, 'bonding_curve':curve, 'token_program':program,
            'pump_creator':curve_state['pump_creator'], 'supply':str(supply), 'decimals':decimals,
            'pump_complete':curve_state['complete'], 'creation_slot':tx['slot'],
            'creation_block_time':tx.get('blockTime'), 'pump_instruction':decoded['version'], 'idl_commit':IDL_COMMIT,
            'launch_provider':'pump.fun', 'pump_verified':True, 'pump_creation_verified':True,
            'creator_fees_managed_by':'pump.fun'}