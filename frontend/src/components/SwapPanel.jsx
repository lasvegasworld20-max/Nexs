import React,{useEffect,useState} from 'react';
import {ArrowUpRight,ShieldCheck,RefreshCw} from 'lucide-react';
import {toast} from 'sonner';
import {ExternalLink,Loading} from './Shared';
const SOL='So11111111111111111111111111111111111111112';
let scriptPromise;
const loadJupiter=()=>{
 // Some embedded browsers report POSIX locale tags, which Intl rejects.
 try{new Intl.NumberFormat(navigator.language);}catch{const locale=(navigator.language || 'en-US').split('@')[0].replace(/_/g,'-');try{Object.defineProperty(navigator,'language',{get:()=>locale,configurable:true});Object.defineProperty(navigator,'languages',{get:()=>[locale,'en'],configurable:true});}catch{}}
 if(window.Jupiter)return Promise.resolve();
 if(!scriptPromise)scriptPromise=new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=process.env.REACT_APP_JUPITER_PLUGIN_URL;s.async=true;s.dataset.preload='true';s.onload=resolve;s.onerror=()=>{scriptPromise=null;reject(new Error('Jupiter is temporarily unavailable'));};document.head.appendChild(s);});
 return scriptPromise;
};
export const SwapPanel=({token})=>{
 const [side,setSide]=useState('buy'),[state,setState]=useState('loading'),[retry,setRetry]=useState(0);
 useEffect(()=>{
  let active=true;setState('loading');let timer;
  loadJupiter().then(()=>{
   if(!active)return;
   window.Jupiter.init({displayMode:'integrated',integratedTargetId:'jupiter-terminal',formProps:{initialInputMint:side==='buy'?SOL:token.mint,initialOutputMint:side==='buy'?token.mint:SOL,fixedMint:token.mint},onSuccess:({txid})=>{toast.success('Transaction submitted to Solana',{description:txid?`${txid.slice(0,16)}…`:undefined});},onSwapError:()=>toast.error('Swap did not complete. No success has been recorded.')});
   setState('ready');
  }).catch(()=>{if(active)setState('error');});
  timer=setTimeout(()=>{if(active&&!document.getElementById('jupiter-terminal')?.hasChildNodes())setState('error');},15000);
  return()=>{active=false;clearTimeout(timer);window.Jupiter?.close?.();};
 },[token.mint,side,retry]);
 return <section className="swap-panel" data-testid="swap-panel"><div className="trade-tabs"><button data-testid="buy-token-tab" className={side==='buy'?'active':''} onClick={()=>setSide('buy')}>Buy {token.symbol}</button><button data-testid="sell-token-tab" className={side==='sell'?'active sell':''} onClick={()=>setSide('sell')}>Sell {token.symbol}</button></div><div className="trade-network" data-testid="trade-network"><span className="status-dot"/>Solana mainnet<span>Powered by Jupiter</span></div>
 {state==='loading'&&<Loading text="Finding your route…"/>}{state==='error'&&<div className="swap-error" data-testid="swap-error"><p>Jupiter could not load here.</p><button data-testid="retry-jupiter" onClick={()=>setRetry(retry+1)}><RefreshCw size={14}/>Retry</button></div>}
 <div id="jupiter-terminal" data-testid="jupiter-terminal" className={state==='error'?'hidden':''}/>
 <div className="swap-footer"><ExternalLink testId="trade-on-jupiter" href={`${process.env.REACT_APP_JUPITER_URL}/swap/${side==='buy'?SOL:token.mint}-${side==='buy'?token.mint:SOL}`}>Open in Jupiter</ExternalLink><span><ShieldCheck size={13}/>Wallet-signed transactions</span></div>
 </section>;
};