import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import db, client
from markets import router as markets_router, seed_world
from auth import router as auth_router
from economy import router as economy_router
from pump_routes import router as pump_router
from pump_activity import router as pump_activity_router
from media_store import router as media_router,init_storage
from social_profiles import router as profiles_router
from social_posts import router as social_router
from ecosystem import classify_existing_tokens
import logging

@asynccontextmanager
async def lifespan(app):
    await db.tokens.create_index('mint', unique=True)
    await db.sessions.create_index('expires_at', expireAfterSeconds=0)
    await db.challenges.create_index('expires_at', expireAfterSeconds=0)
    await db.bounties.create_index('id', unique=True)
    await db.submissions.create_index([('bounty_id', 1), ('wallet', 1)], unique=True)
    await db.market_snapshots.create_index([('mint',1),('time',1)],unique=True)
    await db.market_snapshots.create_index('expires_at',expireAfterSeconds=0)
    for collection,field in [('launch_sessions','id'),('launch_sessions','mint'),('nexus_registry','mint'),('nexus_registry','token_id'),('nexus_registry','launch_session_id'),('communities','token_id'),('profiles','wallet'),('files','id'),('social_posts','id'),('social_feed','id')]:
        await db[collection].create_index(field,unique=True)
    await db.profiles.create_index('handle',unique=True,sparse=True)
    for collection,keys in [('social_likes',[('post_id',1),('wallet',1)]),('social_reposts',[('post_id',1),('wallet',1)]),('follows',[('wallet',1),('target',1)])]:
        await db[collection].create_index(keys,unique=True)
    await db.social_posts.create_index([('token_id',1),('created_at',-1)])
    await db.social_feed.create_index([('token_id',1),('created_at',-1)])
    await seed_world()
    await classify_existing_tokens()
    try:await init_storage()
    except Exception:logging.warning('Storage unavailable at startup; uploads will retry initialization')
    yield
    client.close()

app = FastAPI(title='NEXUS World API', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.environ['APP_ORIGIN']], allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PATCH', 'OPTIONS'], allow_headers=['Authorization', 'Content-Type'])
app.include_router(markets_router, prefix='/api')
app.include_router(auth_router, prefix='/api')
app.include_router(economy_router, prefix='/api')
app.include_router(pump_router, prefix='/api')
app.include_router(pump_activity_router, prefix='/api')
app.include_router(media_router, prefix='/api')
app.include_router(profiles_router, prefix='/api')
app.include_router(social_router, prefix='/api')

@app.get('/api/')
async def health():
    return {'name': 'NEXUS', 'network': 'mainnet-beta', 'status': 'online'}