import uuid
from fastapi import APIRouter,Depends,Header,HTTPException,Query
from pydantic import BaseModel,Field,ConfigDict
from pymongo.errors import DuplicateKeyError
from auth import current_wallet,valid_wallet
from database import db,now
from media_store import owned_image
router=APIRouter()

async def viewer_wallet(authorization:str=Header(default='')):
    return await current_wallet(authorization) if authorization else None

async def public_profile(wallet,viewer=None):
    row=await db.profiles.find_one({'wallet':wallet},{'_id':0})
    if not row:row={'wallet':wallet,'handle':None,'display_name':f'{wallet[:4]}…{wallet[-4:]}','bio':'','avatar_url':None,'joined_at':None}
    return {**row,'followers':await db.follows.count_documents({'target':wallet}),
            'following':await db.follows.count_documents({'wallet':wallet}),
            'viewer_follows':bool(viewer and await db.follows.find_one({'wallet':viewer,'target':wallet}))}

class ProfileEdit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    display_name:str=Field(min_length=1,max_length=48)
    handle:str=Field(min_length=3,max_length=24,pattern=r'^[a-zA-Z0-9_]+$')
    bio:str=Field(default='',max_length=280)
    avatar_id:str|None=Field(default=None,max_length=32)
class Active(BaseModel):
    model_config=ConfigDict(extra='forbid')
    active:bool

@router.patch('/profiles/me')
async def edit_profile(body:ProfileEdit,wallet:str=Depends(current_wallet)):
    name=body.display_name.strip()
    if not name:raise HTTPException(422,'Display name cannot be blank')
    avatar=await owned_image(body.avatar_id,wallet,['avatar']) if body.avatar_id else None
    values={'display_name':name,'handle':body.handle.lower(),'bio':body.bio.strip(),'avatar_id':body.avatar_id,'avatar_url':avatar}
    try:await db.profiles.update_one({'wallet':wallet},{'$set':values,'$setOnInsert':{'wallet':wallet,'joined_at':now().isoformat()}},upsert=True)
    except DuplicateKeyError:raise HTTPException(409,'This username is already taken')
    return await public_profile(wallet,wallet)

@router.get('/profiles/{wallet}')
async def get_profile(wallet:str,viewer=Depends(viewer_wallet)):
    valid_wallet(wallet)
    return await public_profile(wallet,viewer)

@router.post('/profiles/{target}/follow')
async def follow(target:str,body:Active,wallet:str=Depends(current_wallet)):
    valid_wallet(target)
    if target==wallet:raise HTTPException(400,'You cannot follow yourself')
    if body.active:
        try:await db.follows.update_one({'wallet':wallet,'target':target},{'$setOnInsert':{'wallet':wallet,'target':target,'created_at':now().isoformat()}},upsert=True)
        except DuplicateKeyError:pass
    else:await db.follows.delete_one({'wallet':wallet,'target':target})
    return await public_profile(target,wallet)

@router.get('/profiles/{wallet}/connections')
async def connections(wallet:str,kind:str=Query('followers',pattern='^(followers|following)$'),viewer=Depends(viewer_wallet)):
    valid_wallet(wallet)
    rows=await db.follows.find({'target':wallet} if kind=='followers' else {'wallet':wallet},{'_id':0}).sort('created_at',-1).to_list(100)
    return [await public_profile(r['wallet' if kind=='followers' else 'target'],viewer) for r in rows]