"""Bounded, allowlisted reads of on-chain referenced metadata. No upload API."""
import json
import os
from urllib.parse import urlsplit
import httpx

def public_image_url(value):
    if not isinstance(value,str) or len(value)>4096: return None
    if value.startswith('ipfs://'): value=f'{os.environ["IPFS_GATEWAY_URL"]}/{value[7:].removeprefix("ipfs/")}'
    try:
        u=urlsplit(value)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443): return None
        if u.hostname in ('localhost','127.0.0.1','::1') or '.' not in u.hostname: return None
        return value
    except ValueError: return None

async def fetch_metadata(uri):
    url=public_image_url(uri)
    if not url or urlsplit(url).hostname not in set(os.environ['PUMP_METADATA_HOSTS'].split(',')):
        return {'image':None, 'description':'', 'metadata_status':'unavailable'}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            async with client.stream('GET',url) as response:
                response.raise_for_status()
                if response.is_redirect: raise ValueError('Metadata redirect not followed')
                content=bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content)>262144: raise ValueError('Metadata too large')
                data=json.loads(content)
                if not isinstance(data,dict): raise ValueError('Invalid metadata JSON')
        return {'image':public_image_url(data.get('image')),
                'description':str(data.get('description',''))[:1000], 'metadata_status':'available'}
    except (httpx.HTTPError, ValueError, TypeError):
        return {'image':None, 'description':'', 'metadata_status':'unavailable'}