import React,{createContext,useContext,useState,useEffect,useRef} from 'react';
import {Connection, PublicKey} from '@solana/web3.js';
import {toast} from 'sonner';
import {api,API_URL,errorMessage} from '../lib/api';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '../components/ui/dialog';
import {Wallet,ArrowUpRight,ShieldCheck,LogOut} from 'lucide-react';
const Context=createContext(null);
export const useWallet=()=>useContext(Context);
export const connection=new Connection(`${API_URL}/rpc`,{commitment:'confirmed',disableRetryOnRateLimit:true});

export const WalletProvider=({children})=>{
 const [wallet,setWallet]=useState(null),[balance,setBalance]=useState(null),[open,setOpen]=useState(false),[busy,setBusy]=useState(false);
 const provider=useRef(null);
 const disconnect=async()=>{try{await provider.current?.disconnect();}catch{} provider.current=null;setWallet(null);setBalance(null);sessionStorage.removeItem('nexus-session');sessionStorage.removeItem('nexus-wallet');};
 const refreshBalance=async(address)=>{try{const value=await connection.getBalance(new PublicKey(address));setBalance(value/1e9);}catch{setBalance(null);}};
 const connect=async(kind)=>{
   const p=kind==='Phantom'?window.phantom?.solana:window.solflare;
   if(!p){window.open(kind==='Phantom'?process.env.REACT_APP_PHANTOM_URL:process.env.REACT_APP_SOLFLARE_URL,'_blank','noopener,noreferrer');return;}
   setBusy(true);
   try{
    const result=await p.connect(); const address=(result?.publicKey || p.publicKey).toString();
    provider.current=p;setWallet(address);setOpen(false);await refreshBalance(address);
    p.on?.('accountChanged',()=>{sessionStorage.removeItem('nexus-session');setWallet(null);setBalance(null);provider.current=null;});
    p.on?.('disconnect',()=>{setWallet(null);setBalance(null);sessionStorage.removeItem('nexus-session');});
    toast.success('Wallet connected');
   }catch(e){toast.error(errorMessage(e));}finally{setBusy(false);}
 };
 const authenticate=async()=>{
  if(!wallet || !provider.current){setOpen(true);throw new Error('Connect your Solana wallet to continue');}
  if(sessionStorage.getItem('nexus-session') && sessionStorage.getItem('nexus-wallet')===wallet)return;
  const {data:c}=await api.get(`/auth/challenge/${wallet}`);
  const signed=await provider.current.signMessage(new TextEncoder().encode(c.message),'utf8');
  const bytes=signed.signature || signed;
  const {data}=await api.post('/auth/verify',{wallet,nonce:c.nonce,signature:btoa(String.fromCharCode(...bytes))});
  sessionStorage.setItem('nexus-session',data.token);sessionStorage.setItem('nexus-wallet',wallet);
 };
 useEffect(()=>{sessionStorage.removeItem('nexus-session');sessionStorage.removeItem('nexus-wallet');},[]);
 return <Context.Provider value={{wallet,balance,provider:provider.current,connect:()=>setOpen(true),disconnect,authenticate,refreshBalance}}>
  {children}<Dialog open={open} onOpenChange={setOpen}><DialogContent className="nexus-dialog wallet-dialog" data-testid="wallet-dialog">
   <div className="dialog-symbol"><Wallet size={24}/></div><DialogTitle data-testid="wallet-dialog-title">Your key to the city.</DialogTitle>
   <DialogDescription data-testid="wallet-dialog-description">Connect a Solana wallet.</DialogDescription>
   {wallet?<button data-testid="disconnect-wallet" className="wallet-option" onClick={disconnect}><LogOut size={20}/>Disconnect wallet</button>:['Phantom','Solflare'].map((name,i)=><button key={name} data-testid={`connect-${name.toLowerCase()}`} className="wallet-option" disabled={busy} onClick={()=>connect(name)}><span className={`wallet-mark wallet-mark-${i}`}><Wallet size={22}/></span><span>{name}<small>{(name==='Phantom'?window.phantom?.solana:window.solflare)?'Detected':'Get wallet'}</small></span><ArrowUpRight size={18}/></button>)}
   <div className="wallet-security" data-testid="wallet-security"><ShieldCheck size={15}/>Non-custodial. Your keys stay yours.</div>
  </DialogContent></Dialog>
 </Context.Provider>
};