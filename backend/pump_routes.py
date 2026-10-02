"""Only session-bound official SDK launches can enter the NEXUS registry."""
import asyncio
import base64
import hashlib
import json
import math
import os
import uuid
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from pymongo.errors import DuplicateKeyError
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from auth import current_wallet,valid_wallet
from database import db,now
from chain import rpc
from catalog import DISTRICTS
from media_store import owned_image,token_metadata
from pump_verifier import verify_creation
router=APIRouter()
builder_lock=asyncio.Semaphore(2)

class Prepare(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mint:str=Field(min_length=32,max_length=44)
    name:str=Field(min_length=1,max_length=32)
    symbol:str=Field(min_length=1,max_length=13,pattern=r'^[A-Za-z0-9]+$')
    description:str=Field(default='',max_length=1000)
    image_id:str=Field(min_length=32,max_length=32)
    district:Literal['meme','defi','ai','culture']
    color:str=Field(pattern=r'^#[0-9a-fA-F]{6}$')
class Submit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    transaction_base64:str=Field(min_length=100,max_length=6000)

def message_bytes(tx):return bytes(to_bytes_versioned(tx.message))

async def session_for(id,wallet):
    row=await db.launch_sessions.find_one({'id':id,'wallet':wallet},{'_id':0})
    if not row:raise HTTPException(404,'Launch session not found for this wallet')
    return row

def public_session(row):
    return {k:row.get(k) for k in ('id','mint','name','symbol','status','signature','last_valid_block_height','network_fee_lamports','error','token_id')}

@router.get('/pump/config')
async def config():
    return {'launch_mode':'nexus_official_sdk','sdk':'@pump-fun/pump-sdk','sdk_version':'2.0.0',
            'creator_fees_managed_by':'pump.fun','arbitrary_imports_enabled':False,'catalog_is_visual_only':True}

@router.post('/pump/verify')
@router.post('/pump/import')
async def imports_disabled(wallet:str=Depends(current_wallet)):
    raise HTTPException(410,'External token imports are disabled. Launch through a NEXUS session.')

@router.post('/pump/launches/prepare')
async def prepare(body:Prepare,wallet:str=Depends(current_wallet)):
    valid_wallet(body.mint)
    if body.mint==wallet:raise HTTPException(400,'Mint must be a new token account')
    if len(body.name.encode())>32:raise HTTPException(400,'Token name must fit in 32 UTF-8 bytes')
    recent=now()-timedelta(minutes=10)
    if await db.launch_sessions.count_documents({'wallet':wallet,'created_at':{'$gt':recent.isoformat()}})>=8:raise HTTPException(429,'Too many launch attempts. Please wait a few minutes.')
    account=await rpc('getAccountInfo',[body.mint,{'encoding':'base64','commitment':'confirmed'}])
    if account.get('value') is not None:raise HTTPException(409,'This mint already exists. External launches cannot be registered.')
    image=await owned_image(body.image_id,wallet,['token-image'])
    id=uuid.uuid4().hex
    row={**body.model_dump(),'id':id,'wallet':wallet,'status':'preparing','created_at':now().isoformat(),'image':image}
    try:await db.launch_sessions.insert_one(dict(row))
    except DuplicateKeyError:raise HTTPException(409,'This mint is already bound to a launch session')
    try:
        metadata=await token_metadata(id,wallet,body.name,body.symbol,body.description,image)
        latest=(await rpc('getLatestBlockhash',[{'commitment':'confirmed'}]))['value']
        async with builder_lock:
            process=await asyncio.create_subprocess_exec('node',os.environ['PUMP_BUILDER_PATH'],stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            try:
                output,errors=await asyncio.wait_for(process.communicate(json.dumps({'mint':body.mint,'wallet':wallet,'name':body.name,'symbol':body.symbol,'uri':metadata['url'],'blockhash':latest['blockhash']}).encode()),timeout=20)
            except asyncio.TimeoutError:
                process.kill();await process.wait();raise HTTPException(503,'Token builder timed out. Please retry with a new launch.')
            if process.returncode:raise HTTPException(503,'Official Pump SDK could not prepare the launch')
            built=json.loads(output)
        fee=await rpc('getFeeForMessage',[built['message_base64'],{'commitment':'confirmed'}])
        update={**built,'status':'prepared','metadata_uri':metadata['url'],'blockhash':latest['blockhash'],
                'last_valid_block_height':latest['lastValidBlockHeight'],'network_fee_lamports':fee.get('value')}
        await db.launch_sessions.update_one({'id':id},{'$set':update})
        return {**public_session({**row,**update}),'transaction_base64':built['transaction_base64'],
                'message_sha256':built['message_sha256'],'metadata_uri':metadata['url'],
                'cost_notice':'Network fee shown excludes Pump account rent. Your wallet displays the full transaction.'}
    except Exception:
        await db.launch_sessions.update_one({'id':id},{'$set':{'status':'failed','error':'Launch preparation did not complete'}})
        raise

@router.post('/pump/launches/{id}/submit')
async def submit(id:str,body:Submit,wallet:str=Depends(current_wallet)):
    session=await session_for(id,wallet)
    if session['status']=='confirmed':return public_session(session)
    if session['status'] not in ('prepared','submitted'):raise HTTPException(409,'This launch is no longer signable. Start a new launch.')
    try:
        raw=base64.b64decode(body.transaction_base64,validate=True);tx=VersionedTransaction.from_bytes(raw)
        if len(raw)>1232:raise ValueError()
        actual=message_bytes(tx)
    except (ValueError,TypeError):raise HTTPException(400,'Invalid signed Solana transaction')
    if actual!=base64.b64decode(session['message_base64']) or hashlib.sha256(actual).hexdigest()!=session['message_sha256']:
        raise HTTPException(409,'Transaction differs from the NEXUS launch session. External launches are not accepted.')
    if not all(tx.verify_with_results()):raise HTTPException(400,'Both the mint and creator wallet must sign the exact NEXUS transaction')
    signature=str(tx.signatures[0])
    if session.get('signature') and session['signature']!=signature:raise HTTPException(409,'Session already has a different transaction')
    if await rpc('getBlockHeight',[{'commitment':'confirmed'}])>session['last_valid_block_height']:
        if session.get('signature'):return await confirm_session(session)
        await db.launch_sessions.update_one({'id':id},{'$set':{'status':'expired'}})
        raise HTTPException(409,'The transaction expired before submission. No new token was registered.')
    await db.launch_sessions.update_one({'id':id,'status':{'$in':['prepared','submitted']}},{'$set':{'status':'submitted','signature':signature,'submitted_at':now().isoformat()}})
    try:
        result=await rpc('sendTransaction',[body.transaction_base64,{'encoding':'base64','skipPreflight':False,'maxRetries':3,'preflightCommitment':'confirmed'}])
        if result!=signature:raise HTTPException(502,'Network returned a different transaction signature')
    except HTTPException:
        # Keep the signature: a network timeout is not proof that no transaction landed.
        return {**public_session({**session,'status':'submitted','signature':signature}),'error':'Submission has not been confirmed. Check status before starting another launch.'}
    return await confirm_session({**session,'status':'submitted','signature':signature})

async def confirm_session(session):
    signature=session.get('signature')
    if not signature:return public_session(session)
    status=(await rpc('getSignatureStatuses',[[signature],{'searchTransactionHistory':True}]))['value'][0]
    if status and status.get('err'):
        await db.launch_sessions.update_one({'id':session['id']},{'$set':{'status':'failed','error':'Pump.fun transaction failed on-chain'}})
        return public_session({**session,'status':'failed','error':'Pump.fun transaction failed on-chain'})
    if not status or status.get('confirmationStatus') not in ('confirmed','finalized'):
        if await rpc('getBlockHeight',[{'commitment':'confirmed'}])>session['last_valid_block_height']:
            await db.launch_sessions.update_one({'id':session['id']},{'$set':{'status':'expired','error':'No confirmed launch was found before blockhash expiry'}})
            return public_session({**session,'status':'expired','error':'No confirmed launch was found before blockhash expiry'})
        return public_session(session)
    chain_tx=await rpc('getTransaction',[signature,{'encoding':'base64','commitment':'confirmed','maxSupportedTransactionVersion':0}])
    if not chain_tx:return public_session(session)
    actual=VersionedTransaction.from_bytes(base64.b64decode(chain_tx['transaction'][0]))
    if message_bytes(actual)!=base64.b64decode(session['message_base64']):raise HTTPException(409,'Confirmed transaction does not match this NEXUS session')
    verified=await verify_creation(session['mint'],signature,session['wallet'])
    if any(verified[k]!=session[k] for k in ('name','symbol','metadata_uri')):raise HTTPException(409,'Confirmed token identity does not match this launch session')
    token=await register_confirmed(session,verified)
    await db.launch_sessions.update_one({'id':session['id']},{'$set':{'status':'confirmed','token_id':token['id'],'confirmed_at':now().isoformat(),'error':None}})
    return public_session({**session,'status':'confirmed','token_id':token['id'],'error':None})

async def register_confirmed(session,verified):
    mint=session['mint'];id=session['id']
    entry={'mint':mint,'token_id':mint,'launch_session_id':id,'creator':session['wallet'],
           'message_sha256':session['message_sha256'],'signature':session['signature'],'status':'confirmed','registered_at':now().isoformat()}
    existing=await db.nexus_registry.find_one({'mint':mint},{'_id':0})
    if existing and existing['launch_session_id']!=id:raise HTTPException(409,'Mint belongs to a different launch session')
    await db.nexus_registry.update_one({'mint':mint},{'$setOnInsert':entry},upsert=True)
    district=next(d for d in DISTRICTS if d['id']==session['district'])
    n=await db.tokens.count_documents({'district':session['district']})
    angle=n*2.39996;radius=20+math.sqrt(n)*6
    token={**verified,'id':mint,'image':session['image'],'description':session['description'],'district':session['district'],'color':session['color'],
           'x':district['x']+math.cos(angle)*radius,'z':district['z']+math.sin(angle)*radius,
           'nexus_launched':True,'community_enabled':True,'is_catalog':False,'registry_status':'nexus',
           'nexus_launch_session':id,'listed_at':now().isoformat(),'market_cap':None,'price':None,'holders':None,
           'volume_24h':None,'change_24h':None,'pump_url':f'{os.environ["PUMP_FUN_URL"]}/coin/{mint}'}
    await db.tokens.update_one({'mint':mint},{'$setOnInsert':token},upsert=True)
    await db.communities.update_one({'token_id':mint},{'$setOnInsert':{'token_id':mint,'creator':session['wallet'],'created_at':now().isoformat()}},upsert=True)
    await db.activity.update_one({'id':f'launch:{id}'},{'$setOnInsert':{'id':f'launch:{id}','token_id':mint,'wallet':session['wallet'],'kind':'launch','text':f'{session["symbol"]} launched through NEXUS on Pump.fun','signature':session['signature'],'created_at':now().isoformat()}},upsert=True)
    return await db.tokens.find_one({'mint':mint},{'_id':0})

@router.get('/pump/launches/{id}')
async def launch_status(id:str,wallet:str=Depends(current_wallet)):
    session=await session_for(id,wallet)
    if session['status'] in ('submitted','confirmed'):return await confirm_session(session)
    return public_session(session)

@router.get('/registry/tokens')
async def registry():
    from ecosystem import registry_ids
    return await db.tokens.find({'id':{'$in':await registry_ids()}},{'_id':0}).to_list(1000)