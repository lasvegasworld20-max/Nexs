import {Buffer} from 'buffer';
import {Keypair,Transaction,SystemProgram,PublicKey} from '@solana/web3.js';
import {MINT_SIZE,TOKEN_PROGRAM_ID,createInitializeMintInstruction,getAssociatedTokenAddress,createAssociatedTokenAccountInstruction,createMintToInstruction,createSetAuthorityInstruction,AuthorityType} from '@solana/spl-token';
import {connection} from '../context/WalletContext';
if(!window.Buffer)window.Buffer=Buffer;
export async function waitForConfirmation(signature){
 for(let i=0;i<35;i++){
  const {value}=await connection.getSignatureStatuses([signature],{searchTransactionHistory:true});
  if(value[0]?.err)throw new Error('The transaction failed on-chain. No launch was registered.');
  if(['confirmed','finalized'].includes(value[0]?.confirmationStatus))return;
  await new Promise(r=>setTimeout(r,2000));
 }
 throw new Error('Confirmation is still pending. Keep your transaction signature and retry registration.');
}
export async function createToken(provider,wallet,supply,onSent){
 const payer=new PublicKey(wallet),mint=Keypair.generate();
 const rent=await connection.getMinimumBalanceForRentExemption(MINT_SIZE);
 const ata=await getAssociatedTokenAddress(mint.publicKey,payer);
 const {blockhash}=await connection.getLatestBlockhash('confirmed');
 const tx=new Transaction({feePayer:payer,recentBlockhash:blockhash});
 tx.add(SystemProgram.createAccount({fromPubkey:payer,newAccountPubkey:mint.publicKey,space:MINT_SIZE,lamports:rent,programId:TOKEN_PROGRAM_ID}),
  createInitializeMintInstruction(mint.publicKey,6,payer,null),
  createAssociatedTokenAccountInstruction(payer,ata,payer,mint.publicKey),
  createMintToInstruction(mint.publicKey,ata,payer,BigInt(supply)*1000000n),
  createSetAuthorityInstruction(mint.publicKey,payer,AuthorityType.MintTokens,null));
 tx.partialSign(mint);
 const signed=await provider.signTransaction(tx);
 const signature=await connection.sendRawTransaction(signed.serialize(),{skipPreflight:false,maxRetries:3});
 const result={mint:mint.publicKey.toBase58(),signature};onSent(result);
 await waitForConfirmation(signature);return result;
}
export async function sendReward(provider,wallet,to,amount,onSent){
 const {blockhash}=await connection.getLatestBlockhash('confirmed');
 const tx=new Transaction({feePayer:new PublicKey(wallet),recentBlockhash:blockhash}).add(SystemProgram.transfer({fromPubkey:new PublicKey(wallet),toPubkey:new PublicKey(to),lamports:Math.round(amount*1e9)}));
 const signed=await provider.signTransaction(tx);const signature=await connection.sendRawTransaction(signed.serialize(),{skipPreflight:false});
 onSent?.(signature);await waitForConfirmation(signature);return signature;
}