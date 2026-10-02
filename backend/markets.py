import asyncio
import os
import time
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from database import db, now
from catalog import TOKENS, DISTRICTS
from ecosystem import visible_query,registry_ids

router = APIRouter()
refresh_lock = asyncio.Lock()
last_attempt = 0
chart_cache = {}

class Token(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    name: str
    symbol: str
    mint: str
    district: str

async def seed_world():
    offsets = [(-15,-12),(7,4),(20,-14),(-12,15),(18,19),(-24,2)]
    counts = {}
    for id, name, symbol, mint, district in TOKENS:
        i = counts.get(district, 0); counts[district] = i+1
        d = next(d for d in DISTRICTS if d['id']==district)
        dx,dz = offsets[i % len(offsets)]
        await db.tokens.update_one({'mint':mint}, {'$setOnInsert':{
            'id':id, 'name':name, 'symbol':symbol, 'mint':mint, 'district':district,
            'color':d['color'], 'x':d['x']+dx, 'z':d['z']+dz, 'creator':None,
            'image':None, 'market_cap':None, 'price':None, 'change_24h':None, 'volume_24h':None,
            'liquidity':None, 'holders':None, 'source':'DEX Screener', 'listed_at':now().isoformat(),
            'description':f'{name} in the {d["name"]}.', 'identity_source':'CoinGecko platform registry',
        }}, upsert=True)
    await refresh_markets()

async def refresh_markets():
    global last_attempt
    if time.time()-last_attempt < 60 or refresh_lock.locked(): return
    async with refresh_lock:
        last_attempt=time.time()
        tokens=await db.tokens.find(await visible_query(), {'_id':0}).to_list(1000)
        async with httpx.AsyncClient(timeout=18) as c:
            for start in range(0,len(tokens),30):
                try:
                    addresses=','.join(t['mint'] for t in tokens[start:start+30])
                    r=await c.get(f'{os.environ["DEXSCREENER_API_URL"]}/tokens/v1/solana/{addresses}')
                    r.raise_for_status(); pairs=r.json()
                    for token in tokens[start:start+30]:
                        matches=[p for p in pairs if p.get('baseToken',{}).get('address')==token['mint'] and p.get('chainId')=='solana']
                        if not matches: continue
                        p=max(matches,key=lambda x:x.get('liquidity',{}).get('usd',0))
                        data={'price':float(p['priceUsd']) if p.get('priceUsd') else None,
                              'market_cap':p.get('marketCap'), 'change_24h':p.get('priceChange',{}).get('h24'),
                              'volume_24h':p.get('volume',{}).get('h24'), 'liquidity':p.get('liquidity',{}).get('usd'),
                              'pair':p.get('pairAddress'), 'market_updated_at':now().isoformat(),
                              'buys_24h':p.get('txns',{}).get('h24',{}).get('buys'),
                              'sells_24h':p.get('txns',{}).get('h24',{}).get('sells'),
                              'market_source':'DEX Screener','price_method':'market-price'}
                        if p.get('info',{}).get('imageUrl'): data['image']=p['info']['imageUrl']
                        await db.tokens.update_one({'mint':token['mint']},{'$set':data})
                except (httpx.HTTPError, ValueError, TypeError):
                    pass  # Keep the last real snapshot and expose its timestamp, never invent prices.
        from pump_market import refresh_pump_state
        await refresh_pump_state(tokens)

@router.get('/world')
async def world():
    await refresh_markets()
    ids=await registry_ids()
    tokens=await db.tokens.find(await visible_query(), {'_id':0}).to_list(1000)
    active=await db.bounties.count_documents({'token_id':{'$in':ids},'status':'open','ends_at':{'$gt':now().isoformat()}})
    return {'tokens':[Token(**t).model_dump() for t in tokens], 'districts':DISTRICTS,
            'stats':{'tokens':len(tokens),'market_cap':sum(t.get('market_cap') or 0 for t in tokens),
                     'volume_24h':sum(t.get('volume_24h') or 0 for t in tokens),'bounties':active,'nexus_tokens':len(ids),'visual_catalog_tokens':sum(t.get('registry_status')=='visual_catalog' for t in tokens)},
            'network':'mainnet-beta','updated_at':max((t.get('market_updated_at','') for t in tokens),default='')}

@router.get('/tokens/{id}', response_model=Token)
async def token(id:str):
    await refresh_markets()
    row=await db.tokens.find_one({'$and':[{'id':id},await visible_query()]},{'_id':0})
    if not row: raise HTTPException(404,'Token not found')
    return Token(**row)

@router.get('/tokens/{id}/chart')
async def chart(id:str, period:str=Query('24H',pattern='^(1H|24H|7D|30D)$')):
    t=await db.tokens.find_one({'$and':[{'id':id},await visible_query()]},{'_id':0})
    if not t: raise HTTPException(404,'Token not found')
    if not t.get('pair'):
        if t.get('pump_verified'):
            from pump_market import observed_chart
            return await observed_chart(t,period)
        return {'candles':[], 'available':False, 'source':'GeckoTerminal'}
    key=f'{id}:{period}'
    if key in chart_cache and time.time()-chart_cache[key][0]<120: return chart_cache[key][1]
    unit,agg,limit={'1H':('minute',1,60),'24H':('hour',1,24),'7D':('hour',4,42),'30D':('day',1,30)}[period]
    try:
        async with httpx.AsyncClient(timeout=12) as c:
            r=await c.get(f'{os.environ["GECKOTERMINAL_API_URL"]}/networks/solana/pools/{t["pair"]}/ohlcv/{unit}',params={'aggregate':agg,'limit':limit,'currency':'usd','token':t['mint']})
            r.raise_for_status()
            candles=[{'time':v[0],'open':v[1],'high':v[2],'low':v[3],'close':v[4],'volume':v[5]} for v in r.json()['data']['attributes']['ohlcv_list']]
            result={'candles':sorted(candles,key=lambda x:x['time']),'available':bool(candles),'source':'GeckoTerminal'}
            chart_cache[key]=(time.time(),result)
            return result
    except (httpx.HTTPError,KeyError,ValueError):
        return {'candles':[],'available':False,'source':'GeckoTerminal','message':'Price history is temporarily unavailable.'}

@router.get('/activity')
async def activity(token_id:str|None=None):
    ids=await registry_ids()
    q={'token_id':token_id} if token_id in ids else {'token_id':{'$in':[] if token_id else ids}}
    return await db.activity.find(q,{'_id':0}).sort('created_at',-1).to_list(50)