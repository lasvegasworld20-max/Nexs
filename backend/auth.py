import base64
import hashlib
import os
import secrets
from datetime import timedelta
import base58
from nacl.signing import VerifyKey
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from database import db, now

router=APIRouter()

def valid_wallet(wallet):
    try:
        if len(base58.b58decode(wallet)) != 32: raise ValueError()
    except Exception: raise HTTPException(400,'Invalid Solana address')

class VerifyRequest(BaseModel):
    wallet:str=Field(max_length=64)
    nonce:str=Field(max_length=100)
    signature:str=Field(max_length=200)

@router.get('/auth/challenge/{wallet}')
async def challenge(wallet:str):
    valid_wallet(wallet)
    nonce=secrets.token_urlsafe(24)
    await db.challenges.delete_many({'wallet':wallet})
    message=f'NEXUS World sign-in\nWallet: {wallet}\nOrigin: {os.environ["APP_ORIGIN"]}\nNonce: {nonce}\nIssued: {now().isoformat()}\nThis signature does not authorize transactions.'
    await db.challenges.insert_one({'wallet':wallet,'nonce':nonce,'message':message,'expires_at':now()+timedelta(minutes=5)})
    return {'nonce':nonce,'message':message}

@router.post('/auth/verify')
async def verify(body:VerifyRequest):
    valid_wallet(body.wallet)
    row=await db.challenges.find_one_and_delete({'wallet':body.wallet,'nonce':body.nonce,'expires_at':{'$gt':now()}},projection={'_id':0})
    if not row: raise HTTPException(401,'Sign-in expired. Please try again.')
    try: VerifyKey(base58.b58decode(body.wallet)).verify(row['message'].encode(),base64.b64decode(body.signature,validate=True))
    except Exception: raise HTTPException(401,'Wallet signature could not be verified')
    token=secrets.token_urlsafe(48)
    await db.sessions.insert_one({'hash':hashlib.sha256(token.encode()).hexdigest(),'wallet':body.wallet,'expires_at':now()+timedelta(hours=12)})
    return {'token':token,'wallet':body.wallet}

async def current_wallet(authorization:str=Header(default='')):
    token=authorization.removeprefix('Bearer ')
    session=await db.sessions.find_one({'hash':hashlib.sha256(token.encode()).hexdigest(),'expires_at':{'$gt':now()}},{'_id':0})
    if not session: raise HTTPException(401,'Connect and sign in with your wallet')
    return session['wallet']