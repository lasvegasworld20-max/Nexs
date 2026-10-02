import os
import httpx
from fastapi import HTTPException

TOKEN_PROGRAM='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
ALLOWED_RPC={'getBalance','getLatestBlockhash','getMinimumBalanceForRentExemption','getAccountInfo',
 'getSignatureStatuses','getTransaction','sendTransaction','getBlockHeight','getTokenAccountsByOwner',
 'getTokenAccountBalance','getFeeForMessage','getHealth','getVersion','simulateTransaction'}

async def rpc(method, params=None):
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r=await c.post(os.environ['SOLANA_RPC_URL'],json={'jsonrpc':'2.0','id':1,'method':method,'params':params or []})
            r.raise_for_status(); data=r.json()
            if data.get('error'): raise HTTPException(502,'Solana RPC could not complete this request. Please retry.')
            return data.get('result')
    except httpx.HTTPError:
        raise HTTPException(503,'Solana network is temporarily unavailable. Please retry.')

async def confirmed_transaction(signature):
    tx=await rpc('getTransaction',[signature,{'encoding':'jsonParsed','commitment':'confirmed','maxSupportedTransactionVersion':0}])
    if not tx or tx.get('meta',{}).get('err') is not None:
        raise HTTPException(400,'Transaction is not confirmed successfully on Solana mainnet')
    return tx

def instructions(tx):
    outer=tx['transaction']['message']['instructions']
    inner=[i for group in tx.get('meta',{}).get('innerInstructions',[]) for i in group['instructions']]
    return outer+inner