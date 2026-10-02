import asyncio
import io
import json
import logging
import os
import uuid
import warnings
import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from auth import current_wallet
from database import db, now
from ecosystem import require_nexus_token

STORAGE_BASE=(os.environ.get('INTEGRATION_PROXY_URL') or '').strip() or 'https://integrations.emergentagent.com'
STORAGE_URL=STORAGE_BASE.rstrip('/')+'/objstore/api/v1/storage'
storage_key=None
storage_lock=asyncio.Lock()
router=APIRouter()
MAX_IMAGE=5*1024*1024
Image.MAX_IMAGE_PIXELS=20_000_000

async def init_storage(force=False):
    global storage_key
    async with storage_lock:
        if storage_key and not force: return storage_key
        async with httpx.AsyncClient(timeout=30) as c:
            r=await c.post(f'{STORAGE_URL}/init',json={'emergent_key':os.environ['EMERGENT_LLM_KEY']})
            r.raise_for_status();storage_key=r.json()['storage_key']
        return storage_key

async def storage_request(method,path,data=None,content_type=None):
    for attempt in range(2):
        try:
            key=await init_storage(force=attempt==1)
            async with httpx.AsyncClient(timeout=60) as c:
                headers={'X-Storage-Key':key}
                if content_type:headers['Content-Type']=content_type
                r=await c.request(method,f'{STORAGE_URL}/objects/{path}',content=data,headers=headers)
                if r.status_code==404 and attempt==0:continue
                r.raise_for_status();return r
        except (httpx.HTTPError,KeyError):
            logging.warning('Object storage request unavailable')
            raise HTTPException(503,'Image storage is temporarily unavailable. Please retry.')
    raise HTTPException(503,'Stored file is temporarily unavailable')

async def save_file(owner,data,content_type,purpose,token_id=None):
    id=uuid.uuid4().hex
    ext='json' if content_type=='application/json' else 'webp'
    result=(await storage_request('PUT',f'nexus/uploads/{owner}/{id}.{ext}',data,content_type)).json()
    row={'id':id,'owner':owner,'storage_path':result['path'],'size':result['size'],
         'content_type':content_type,'purpose':purpose,'token_id':token_id,'is_deleted':False,'created_at':now().isoformat()}
    await db.files.insert_one(dict(row))
    return {'id':id,'url':f'{os.environ["APP_ORIGIN"]}/api/media/{id}','size':row['size'],'content_type':content_type}

async def owned_image(media_id,wallet,purposes,token_id=None):
    query={'id':media_id,'owner':wallet,'purpose':{'$in':purposes},'is_deleted':False}
    if token_id is not None:query['token_id']=token_id
    image=await db.files.find_one(query,{'_id':0})
    if not image or not image['content_type'].startswith('image/'):raise HTTPException(400,'Image is missing or does not belong to this wallet/community')
    return f'{os.environ["APP_ORIGIN"]}/api/media/{media_id}'

@router.post('/media/upload')
async def upload(file:UploadFile=File(...),purpose:str=Form(...),token_id:str|None=Form(None),wallet:str=Depends(current_wallet)):
    if purpose not in ('community','avatar','token-image'):raise HTTPException(400,'Unsupported image purpose')
    if purpose=='community':await require_nexus_token(token_id)
    if await db.files.count_documents({'owner':wallet,'created_at':{'$gt':now().replace(hour=0,minute=0,second=0,microsecond=0).isoformat()}})>=100:
        raise HTTPException(429,'Daily image upload limit reached')
    content=await file.read(MAX_IMAGE+1)
    if not content or len(content)>MAX_IMAGE:raise HTTPException(413,'Choose an image up to 5 MB')
    if file.content_type not in ('image/png','image/jpeg','image/webp'):raise HTTPException(415,'Only PNG, JPEG, and WebP images are supported')
    def normalize():
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            image=Image.open(io.BytesIO(content));image.verify()
            image=ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
            image.thumbnail((2400,2400));image=image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
            output=io.BytesIO();image.save(output,format='WEBP',quality=90)
            return output.getvalue()
    try:data=await asyncio.to_thread(normalize)
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise HTTPException(400,'This file is not a supported safe image')
    return await save_file(wallet,data,'image/webp',purpose,token_id if purpose=='community' else None)

@router.get('/media/{id}')
async def media(id:str):
    row=await db.files.find_one({'id':id,'is_deleted':False},{'_id':0})
    if not row:raise HTTPException(404,'File not found')
    if row['purpose']=='community':await require_nexus_token(row['token_id'])
    response=await storage_request('GET',row['storage_path'])
    return Response(response.content,media_type=row['content_type'],headers={'Cache-Control':'public, max-age=86400, immutable','X-Content-Type-Options':'nosniff'})

async def token_metadata(session,wallet,name,symbol,description,image_url):
    data={'name':name,'symbol':symbol,'description':description,'image':image_url,
          'external_url':f'{os.environ["APP_ORIGIN"]}/launch','attributes':[{'trait_type':'NEXUS launch session','value':session}]}
    return await save_file(wallet,json.dumps(data,separators=(',',':')).encode(),'application/json','token-metadata')