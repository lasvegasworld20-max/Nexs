"""NEXUS membership is a registry decision, never a Pump discovery result."""
from fastapi import HTTPException
from database import db
from catalog import TOKENS

CATALOG_IDS=[t[0] for t in TOKENS]

async def registry_ids():
    rows=await db.nexus_registry.find({'status':'confirmed'},{'_id':0,'token_id':1}).to_list(10000)
    return [r['token_id'] for r in rows]

async def visible_query():
    return {'id':{'$in':CATALOG_IDS+await registry_ids()}}

async def require_nexus_token(token_id):
    entry=await db.nexus_registry.find_one({'token_id':token_id,'status':'confirmed'},{'_id':0})
    if not entry: raise HTTPException(403,'Community and creator features are reserved for tokens launched through NEXUS')
    token=await db.tokens.find_one({'id':token_id,'nexus_launched':True},{'_id':0})
    if not token: raise HTTPException(404,'NEXUS token not found')
    return token

async def classify_existing_tokens():
    # Keep the explicit visual catalog without giving it real NEXUS membership.
    ids=await registry_ids()
    await db.tokens.update_many({'id':{'$nin':ids}}, {'$set':{'nexus_launched':False,'community_enabled':False,'registry_status':'external'}})
    await db.tokens.update_many({'id':{'$in':[i for i in CATALOG_IDS if i not in ids]}},
        {'$set':{'registry_status':'visual_catalog','is_catalog':True}})