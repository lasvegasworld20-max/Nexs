import asyncio
import time
from fastapi import APIRouter, HTTPException
from database import db
from chain import rpc
from pump_codec import pump_event_payloads, decode_trade, SYSTEM_PROGRAM, SOL_MINT

router=APIRouter()
cache={}
lock=asyncio.Semaphore(2)

@router.get('/tokens/{id}/trading-activity')
async def trading_activity(id:str):
    token=await db.tokens.find_one({'id':id},{'_id':0})
    if not token: raise HTTPException(404,'Token not found')
    if not token.get('pump_verified'):
        return {'trades':[],'available':False,'source':'Pump.fun','scope':'No verified Pump.fun provenance'}
    if id in cache and time.monotonic()-cache[id][0]<60: return cache[id][1]
    scope='Recent Pump.fun bonding-curve transactions; a bounded sample, not full market history'
    if token.get('pump_quote_mint') not in (None,SYSTEM_PROGRAM,SOL_MINT):
        return {'trades':[],'available':False,'source':'Solana RPC','scope':'Trade decoding for this quote asset is not yet supported'}
    try:
        signatures=await rpc('getSignaturesForAddress',[token['bonding_curve'],{'limit':8,'commitment':'confirmed'}])
        async def read(item):
            if item.get('err') is not None: return []
            async with lock:
                try:
                    tx=await rpc('getTransaction',[item['signature'],{'encoding':'jsonParsed','commitment':'confirmed','maxSupportedTransactionVersion':0}])
                    if not tx or not tx.get('meta') or tx['meta'].get('err') is not None: return []
                    output=[]
                    for index,payload in enumerate(pump_event_payloads(tx)):
                        trade=decode_trade(payload)
                        if not trade or trade['mint']!=token['mint']: continue
                        output.append({'id':f'{item["signature"]}:{index}','signature':item['signature'],
                            'side':'buy' if trade['is_buy'] else 'sell','wallet':trade['wallet'],
                            'sol_amount':trade['sol_amount_raw']/1e9,
                            'token_amount':trade['token_amount_raw']/10**token.get('decimals',6),
                            'timestamp':trade['timestamp']})
                    return output
                except (HTTPException,ValueError,TypeError,KeyError): return []
        trades=[t for group in await asyncio.gather(*(read(s) for s in signatures)) for t in group]
        result={'trades':sorted(trades,key=lambda t:t['timestamp'],reverse=True),'available':bool(trades),'source':'Solana RPC · Pump.fun TradeEvent','scope':scope}
    except HTTPException:
        result={'trades':[],'available':False,'source':'Solana RPC','scope':scope,'message':'Trading activity is temporarily unavailable'}
    cache[id]=(time.monotonic(),result)
    return result