// Official Pump SDK only; this process never signs or sends a transaction.
const fs=require('node:fs');
const crypto=require('node:crypto');
const {PUMP_SDK}=require('@pump-fun/pump-sdk');
const {PublicKey,TransactionMessage,VersionedTransaction,ComputeBudgetProgram}=require('@solana/web3.js');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const {mint,wallet,name,symbol,uri,blockhash}=input;
 if(Buffer.byteLength(name)>32 || Buffer.byteLength(symbol)>13 || Buffer.byteLength(uri)>200)throw Error('Token name, ticker, or metadata URL is too long');
 const owner=new PublicKey(wallet);
 const createIx=await PUMP_SDK.createV2Instruction({mint:new PublicKey(mint),name,symbol,uri,creator:owner,user:owner,mayhemMode:false,cashback:false});
 if(createIx.programId.toBase58()!=='6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P')throw Error('Unexpected Pump program');
 const message=new TransactionMessage({payerKey:owner,recentBlockhash:blockhash,instructions:[ComputeBudgetProgram.setComputeUnitLimit({units:400000}),createIx]}).compileToV0Message();
 const tx=new VersionedTransaction(message),bytes=Buffer.from(message.serialize());
 process.stdout.write(JSON.stringify({transaction_base64:Buffer.from(tx.serialize()).toString('base64'),message_base64:bytes.toString('base64'),message_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),sdk_version:'2.0.0'}));
})().catch(error=>{process.stderr.write(error.message);process.exit(1);});