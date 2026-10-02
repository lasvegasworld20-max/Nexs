import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl
from pymongo.errors import DuplicateKeyError
from database import db, now
from auth import current_wallet
from chain import rpc, ALLOWED_RPC, confirmed_transaction, instructions
from ecosystem import require_nexus_token,registry_ids

router=APIRouter()
@router.post('/rpc')
async def rpc_proxy(request:Request):
    body=await request.json()
    if not isinstance(body,dict) or body.get('method') not in ALLOWED_RPC:
        raise HTTPException(400,'RPC method not supported')
    result=await rpc(body['method'],body.get('params',[]))
    return {'jsonrpc':'2.0','id':body.get('id',1),'result':result}

@router.post('/launches')
async def launch(wallet:str=Depends(current_wallet)):
    raise HTTPException(410,'Independent minting and external imports are disabled. Use a NEXUS launch session.')

class Presence(BaseModel):
    description:str=Field(max_length=1000)
    color:str=Field(pattern=r'^#[0-9a-fA-F]{6}$')
    image:HttpUrl|None=None

@router.patch('/tokens/{id}/presence')
async def presence(id:str,body:Presence,wallet:str=Depends(current_wallet)):
    await require_nexus_token(id)
    result=await db.tokens.update_one({'id':id,'creator':wallet},{'$set':body.model_dump(mode='json')})
    if not result.matched_count: raise HTTPException(403,'Only the token creator can change its presence')
    return {'updated':True}

async def record(token_id,wallet,kind,text,signature=None):
    await db.activity.insert_one({'id':str(uuid.uuid4()),'token_id':token_id,'wallet':wallet,'kind':kind,'text':text,'signature':signature,'created_at':now().isoformat()})

class BountyCreate(BaseModel):
    token_id:str=Field(max_length=64)
    name:str=Field(min_length=3,max_length=80)
    reward:float=Field(gt=0,le=100000,allow_inf_nan=False)
    objective:str=Field(min_length=10,max_length=2000)
    rules:str=Field(default='',max_length=2000)
    eligibility:str=Field(default='Open to everyone',max_length=500)
    ends_at:datetime
    distribution:str=Field(default='One winner, selected by the creator',max_length=500)

@router.get('/bounties')
async def bounties(token_id:str|None=None):
    ids=await registry_ids()
    q={'token_id':token_id} if token_id in ids else {'token_id':{'$in':[] if token_id else ids}}
    rows=await db.bounties.find(q,{'_id':0}).sort('created_at',-1).to_list(200)
    for r in rows:
        if r['status']=='open' and r['ends_at']<now().isoformat(): r['status']='closed'
        r['entries']=await db.submissions.count_documents({'bounty_id':r['id']})
    return rows

@router.post('/bounties')
async def create_bounty(body:BountyCreate,wallet:str=Depends(current_wallet)):
    await require_nexus_token(body.token_id)
    token=await db.tokens.find_one({'id':body.token_id,'creator':wallet},{'_id':0})
    if not token: raise HTTPException(403,'Only the token creator can publish bounties')
    end=body.ends_at
    if end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
    if end<=now(): raise HTTPException(400,'End date must be in the future')
    row={**body.model_dump(mode='json'),'ends_at':end.astimezone(timezone.utc).isoformat(), 'id':str(uuid.uuid4()),
         'creator':wallet,'token_symbol':token['symbol'],'token_image':token.get('image'),'district':token['district'],
         'status':'open','created_at':now().isoformat(),'funding':'creator-managed'}
    await db.bounties.insert_one(dict(row))
    await record(body.token_id,wallet,'bounty',f'New bounty: {body.name}')
    return row

class Submission(BaseModel):
    content:str=Field(min_length=10,max_length=3000)

@router.post('/bounties/{id}/submissions')
async def submit(id:str,body:Submission,wallet:str=Depends(current_wallet)):
    b=await db.bounties.find_one({'id':id},{'_id':0})
    if not b: raise HTTPException(404,'Bounty not found')
    await require_nexus_token(b['token_id'])
    if b['status']!='open' or b['ends_at']<=now().isoformat(): raise HTTPException(400,'This bounty is closed')
    if b['creator']==wallet: raise HTTPException(400,'Creators cannot enter their own bounty')
    row={'id':str(uuid.uuid4()),'bounty_id':id,'wallet':wallet, 'content':body.content,'created_at':now().isoformat()}
    try: await db.submissions.insert_one(dict(row))
    except DuplicateKeyError: raise HTTPException(409,'You have already submitted an entry')
    await record(b['token_id'],wallet,'submission',f'Submitted an entry to {b["name"]}')
    return row

@router.get('/bounties/{id}/submissions')
async def entries(id:str):
    b=await db.bounties.find_one({'id':id},{'_id':0})
    if not b:raise HTTPException(404,'Bounty not found')
    await require_nexus_token(b['token_id'])
    return await db.submissions.find({'bounty_id':id},{'_id':0}).to_list(200)

class Award(BaseModel):
    submission_id:str=Field(max_length=64)
    signature:str=Field(min_length=64,max_length=100)

@router.post('/bounties/{id}/award')
async def award(id:str,body:Award,wallet:str=Depends(current_wallet)):
    b=await db.bounties.find_one({'id':id,'creator':wallet},{'_id':0})
    if not b: raise HTTPException(403,'Only the creator can distribute this reward')
    await require_nexus_token(b['token_id'])
    if b['status']=='awarded': raise HTTPException(409,'Reward has already been distributed')
    s=await db.submissions.find_one({'id':body.submission_id,'bounty_id':id},{'_id':0})
    if not s: raise HTTPException(404,'Entry not found')
    if await db.bounties.find_one({'payout_signature':body.signature}): raise HTTPException(409,'Payout already used')
    tx=await confirmed_transaction(body.signature)
    paid=any(i.get('program')=='system' and i.get('parsed',{}).get('type')=='transfer' and i['parsed']['info'].get('source')==wallet and i['parsed']['info'].get('destination')==s['wallet'] and i['parsed']['info'].get('lamports',0)>=round(b['reward']*1e9) for i in instructions(tx))
    if not paid: raise HTTPException(400,'Transaction does not include the required SOL reward to this entrant')
    await db.bounties.update_one({'id':id,'status':{'$ne':'awarded'}},{'$set':{'status':'awarded','winner':s['wallet'],'payout_signature':body.signature}})
    await record(b['token_id'],wallet,'award',f'{b["name"]}: {b["reward"]} SOL reward distributed',body.signature)
    return {'status':'awarded','signature':body.signature}

@router.post('/tokens/{id}/community')
async def community(id:str,body:Submission,wallet:str=Depends(current_wallet)):
    from social_posts import create_post,PostCreate
    return await create_post(id,PostCreate(text=body.content),wallet)