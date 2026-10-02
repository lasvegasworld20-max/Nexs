"""Read-only Pump state; preserves the existing world placement and renderer."""
import base64
import os
import time
from datetime import timedelta
import httpx
from fastapi import HTTPException
from database import db, now
from chain import rpc
from pump_codec import (PUMP_PROGRAM, TOKEN_LEGACY, TOKEN_2022, SOL_MINT,
                        SYSTEM_PROGRAM, curve_address, decode_curve)

sol_price_cache=(0,None)

async def sol_usd_price():
    global sol_price_cache
    if time.monotonic()-sol_price_cache[0]<60: return sol_price_cache[1]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response=await client.get(f'{os.environ["DEXSCREENER_API_URL"]}/tokens/v1/solana/{SOL_MINT}')
            response.raise_for_status()
            pairs=[p for p in response.json() if p.get('chainId')=='solana' and p.get('baseToken',{}).get('address')==SOL_MINT and p.get('priceUsd')]
            best=max(pairs,key=lambda p:p.get('liquidity',{}).get('usd',0))
            price=float(best['priceUsd'])
            if price<=0: raise ValueError()
            sol_price_cache=(time.monotonic(),price)
            return price
    except (httpx.HTTPError,ValueError,TypeError): return None

async def refresh_pump_state(tokens):
    for offset in range(0,len(tokens),40):
        batch=tokens[offset:offset+40]
        try:
            curves=[curve_address(t['mint']) for t in batch]
            result=await rpc('getMultipleAccounts',[curves+[t['mint'] for t in batch],{'encoding':'base64','commitment':'confirmed'}])
            values=result.get('value') or []
            if len(values)!=len(batch)*2: continue
        except (HTTPException,ValueError,TypeError): continue
        for i,token in enumerate(batch):
            curve,mint_account=values[i],values[i+len(batch)]
            if not curve or curve.get('owner')!=PUMP_PROGRAM or not mint_account or mint_account.get('owner') not in (TOKEN_LEGACY,TOKEN_2022): continue
            try:
                state=decode_curve(base64.b64decode(curve['data'][0],validate=True))
                mint_raw=base64.b64decode(mint_account['data'][0],validate=True)
                if len(mint_raw)<82 or mint_raw[45]!=1: continue
                supply,decimals=int.from_bytes(mint_raw[36:44],'little'),mint_raw[44]
            except (ValueError,TypeError,KeyError,IndexError): continue
            stamp=now()
            update={'launch_provider':'pump.fun','pump_verified':True,'bonding_curve':curves[i],
                    'pump_complete':state['complete'],'pump_quote_mint':state['quote_mint'],
                    'pump_state_updated_at':stamp.isoformat(),'pump_url':f'{os.environ["PUMP_FUN_URL"]}/coin/{token["mint"]}',
                    'creator_fees_managed_by':'pump.fun','token_program':mint_account['owner'],
                    'supply':str(supply),'decimals':decimals,'holders_status':'indexer_unavailable'}
            # After completion only the actual DEX market remains authoritative.
            if state['complete']:
                update['price_sol']=None
                latest=await db.tokens.find_one({'mint':token['mint']},{'_id':0,'market_source':1})
                if latest and latest.get('market_source')=='Pump.fun bonding curve':
                    update.update({'price':None,'market_cap':None,'market_updated_at':'',
                                   'market_source':'Awaiting graduated market data','price_method':'unavailable'})
            native_quote=state['quote_mint'] in (SYSTEM_PROGRAM,SOL_MINT)
            if not state['complete'] and native_quote and state['virtual_token_reserves']>0 and decimals<=18:
                quote_sol=(state['virtual_quote_reserves']/1e9)/(state['virtual_token_reserves']/10**decimals)
                update['price_sol']=quote_sol
                usd=await sol_usd_price()
                if usd is not None:
                    value=quote_sol*usd
                    update.update({'price':value,'market_cap':value*(supply/10**decimals),
                        'market_source':'Pump.fun bonding curve','market_updated_at':stamp.isoformat(),
                        'price_method':'reserve-derived','sol_usd_source':'DEX Screener','sol_usd':usd})
                    minute=int(stamp.timestamp())//60*60
                    await db.market_snapshots.update_one({'mint':token['mint'],'time':minute},{'$setOnInsert':{
                        'mint':token['mint'],'time':minute,'close':value,'source':'Observed Pump.fun quotes',
                        'expires_at':stamp+timedelta(days=7)}},upsert=True)
            await db.tokens.update_one({'mint':token['mint']},{'$set':update})

async def observed_chart(token,period):
    seconds={'1H':3600,'24H':86400,'7D':604800,'30D':2592000}[period]
    query={'mint':token['mint'],'time':{'$gte':int(now().timestamp())-seconds}}
    points=await db.market_snapshots.find(query,{'_id':0,'time':1,'close':1}).sort('time',-1).limit(1000).to_list(1000)
    points.reverse()
    return {'candles':points if len(points)>1 else [],'available':len(points)>1,
            'source':'Observed Pump.fun quotes','history_scope':'Since world registration; up to 7 days of observed quotes, not reconstructed history'}