import asyncio
import math
import os
import time
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError
from auth import current_wallet, valid_wallet
from database import db, now
from catalog import DISTRICTS
from pump_verifier import verify_creation, validate_signature
from pump_metadata import fetch_metadata

router=APIRouter()
verification_cache={}
verification_lock=asyncio.Semaphore(3)
rate_limits={}

class PumpProof(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mint:str=Field(min_length=32,max_length=44)
    signature:str=Field(min_length=64,max_length=88)

class PumpImport(PumpProof):
    district:Literal['meme','defi','ai','culture']
    color:str=Field(pattern=r'^#[0-9a-fA-F]{6}$')

class VerifiedToken(BaseModel):
    model_config=ConfigDict(extra='allow')
    mint:str
    name:str
    symbol:str
    creator:str
    pump_verified:bool

async def verified_proof(body,wallet):
    valid_wallet(body.mint); validate_signature(body.signature)
    key=(wallet,body.mint,body.signature)
    cached=verification_cache.get(key)
    if cached and time.monotonic()-cached[0]<300: return dict(cached[1])
    tick=time.monotonic()
    attempts=[t for t in rate_limits.get(wallet,[]) if tick-t<60]
    if len(attempts)>=8: raise HTTPException(429,'Too many verification attempts. Please wait a minute.')
    rate_limits[wallet]=attempts+[tick]
    async with verification_lock:
        value=await verify_creation(body.mint,body.signature,wallet)
        value.update(await fetch_metadata(value['metadata_uri']))
        value['pump_url']=f'{os.environ["PUMP_FUN_URL"]}/coin/{body.mint}'
        value['verified_at']=now().isoformat()
    if len(verification_cache)>500: verification_cache.clear()
    verification_cache[key]=(time.monotonic(),dict(value))
    return value

@router.get('/pump/config')
async def config():
    return {'launch_mode':'official_redirect','create_url':f'{os.environ["PUMP_FUN_URL"]}/create',
            'creator_fees_managed_by':'pump.fun','registration_requires':'confirmed_creation_transaction_and_creator_wallet'}

@router.post('/pump/verify',response_model=VerifiedToken)
async def verify(body:PumpProof,wallet:str=Depends(current_wallet)):
    return VerifiedToken(**await verified_proof(body,wallet))

@router.post('/pump/import',response_model=VerifiedToken)
async def import_token(body:PumpImport,wallet:str=Depends(current_wallet)):
    verified=await verified_proof(body,wallet)
    existing=await db.tokens.find_one({'mint':body.mint},{'_id':0})
    if existing and existing.get('creator'):
        if existing['creator']==wallet and existing.get('creation_signature')==body.signature and existing.get('pump_creation_verified'):
            return VerifiedToken(**existing)
        raise HTTPException(409,'This token already belongs to a creator in the world')
    if existing:
        # Claiming an existing catalog building never relocates or duplicates it.
        result=await db.tokens.update_one({'mint':body.mint,'creator':None},{'$set':verified})
        if not result.matched_count: raise HTTPException(409,'This token was just registered. Refresh the world.')
        row={**existing,**verified}
    else:
        district=next(d for d in DISTRICTS if d['id']==body.district)
        n=await db.tokens.count_documents({'district':body.district})
        angle=n*2.39996; radius=20+math.sqrt(n)*6
        row={**verified,'id':body.mint,'district':body.district,'color':body.color,
             'x':district['x']+math.cos(angle)*radius,'z':district['z']+math.sin(angle)*radius,
             'market_cap':None,'price':None,'volume_24h':None,'change_24h':None,'holders':None,
             'listed_at':now().isoformat(),'source':'Pump.fun on-chain'}
        try: await db.tokens.insert_one(dict(row))
        except DuplicateKeyError:
            existing=await db.tokens.find_one({'mint':body.mint},{'_id':0})
            if existing and existing.get('creator')==wallet and existing.get('creation_signature')==body.signature:
                return VerifiedToken(**existing)
            raise HTTPException(409,'Token already registered')
    await db.activity.insert_one({'id':str(uuid.uuid4()),'token_id':row['id'],'wallet':wallet,
        'kind':'launch','text':f'{row["symbol"]} entered the world through Pump.fun',
        'signature':body.signature,'created_at':now().isoformat()})
    from pump_market import refresh_pump_state
    await refresh_pump_state([row])
    row=await db.tokens.find_one({'mint':body.mint},{'_id':0})
    return VerifiedToken(**row)