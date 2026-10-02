import {Keypair,VersionedTransaction} from '@solana/web3.js';
import {api} from './api';
export const newMintSigner=()=>Keypair.generate();
export async function signNexusLaunch(prepared,mintSigner,provider){
 if(!mintSigner || mintSigner.publicKey.toBase58()!==prepared.mint)throw new Error('Mint signer no longer available. Prepare a new launch.');
 const tx=VersionedTransaction.deserialize(Uint8Array.from(atob(prepared.transaction_base64),c=>c.charCodeAt(0)));
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',tx.message.serialize())),v=>v.toString(16).padStart(2,'0')).join('');
 if(hash!==prepared.message_sha256)throw new Error('Launch message verification failed');
 tx.sign([mintSigner]);
 const signed=await provider.signTransaction(tx);
 return btoa(String.fromCharCode(...signed.serialize()));
}
export async function uploadImage(file,purpose,tokenId){
 if(file.size>5*1024*1024)throw new Error('Choose an image up to 5 MB');
 const body=new FormData();body.append('file',file);body.append('purpose',purpose);if(tokenId)body.append('token_id',tokenId);
 return (await api.post('/media/upload',body,{timeout:90000})).data;
}