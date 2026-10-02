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

@asynccontextmanager
async def lifespan(app):
    await db.tokens.create_index('mint', unique=True)
    await db.sessions.create_index('expires_at', expireAfterSeconds=0)
    await db.challenges.create_index('expires_at', expireAfterSeconds=0)
    await db.bounties.create_index('id', unique=True)
    await db.submissions.create_index([('bounty_id', 1), ('wallet', 1)], unique=True)
    await db.market_snapshots.create_index([('mint',1),('time',1)],unique=True)
    await db.market_snapshots.create_index('expires_at',expireAfterSeconds=0)
    await seed_world()
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

@app.get('/api/')
async def health():
    return {'name': 'NEXUS', 'network': 'mainnet-beta', 'status': 'online'}