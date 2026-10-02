import React, {useEffect, useState} from 'react';
import {Link, useNavigate} from 'react-router-dom';
import {ArrowLeft, ArrowUpRight, Check, ShieldCheck, Wallet, LoaderCircle, ExternalLink} from 'lucide-react';
import {toast} from 'sonner';
import {Input} from '../components/ui/input';
import {ActionButton, TokenAvatar} from '../components/Shared';
import {useWallet} from '../context/WalletContext';
import {api, errorMessage, colors, districtNames, shortAddress} from '../lib/api';
const emptyDraft={mint:'', signature:'', district:'meme', color:colors.meme};
const pumpUrl=process.env.REACT_APP_PUMP_FUN_URL;

export default function Launch({reloadWorld}) {
  const {wallet, connect, authenticate}=useWallet(), navigate=useNavigate();
  const [form,setForm]=useState(()=>{try{return {...emptyDraft,...JSON.parse(localStorage.getItem('nexus-pump-draft') || '{}')};}catch{return emptyDraft;}});
  const [verified,setVerified]=useState(null),[busy,setBusy]=useState(false),[step,setStep]=useState(''),[error,setError]=useState('');
  useEffect(()=>{localStorage.setItem('nexus-pump-draft',JSON.stringify(form));},[form]);
  useEffect(()=>{setVerified(null);setError('');},[wallet]);
  const proofField=key=>event=>{setForm({...form,[key]:event.target.value.trim()});setVerified(null);setError('');};
  const submit=async(event)=>{
    event.preventDefault();if(!wallet){connect();return;}setBusy(true);setError('');
    try{
      await authenticate();
      if(!verified){setStep('Verifying Pump.fun creation');const {data}=await api.post('/pump/verify',{mint:form.mint,signature:form.signature});setVerified(data);toast.success('Pump.fun creation verified');}
      else{setStep('Establishing your territory');const {data}=await api.post('/pump/import',form);localStorage.removeItem('nexus-pump-draft');await reloadWorld();toast.success(`${data.symbol} has entered the world`);navigate(`/token/${data.id}`);}
    }catch(e){setError(errorMessage(e));toast.error(errorMessage(e));}finally{setBusy(false);setStep('');}
  };
  return <main className="content-page launch-page" data-testid="launch-page">
    <div className="page-breadcrumb"><Link to="/" data-testid="launch-back-world"><ArrowLeft size={15}/>Back to world</Link><span>/</span><span>New territory</span></div>
    <div className="page-title-row"><div><div className="eyebrow">THE NEXT CHAPTER IS YOURS</div><h1 data-testid="launch-heading">Build your place.</h1><p>Launch on Pump.fun. Establish a territory. Bring your people.</p></div><span className="outline-badge" data-testid="launch-provider"><span className="status-dot"/>PUMP.FUN · SOLANA</span></div>
    <div className="launch-layout"><form className="nexus-form launch-form" onSubmit={submit}>
      <section><div className="form-section-title"><span>01</span><h2>Launch on Pump.fun</h2></div>
        <a href={`${pumpUrl}/create`} target="_blank" rel="noopener noreferrer" data-testid="launch-on-pump" className="action-button pump-launch-link"><ExternalLink size={16}/>Open official Pump.fun launcher<ArrowUpRight size={16}/></a>
        <p className="inline-info" data-testid="pump-launch-handoff">Creation and wallet approval happen on Pump.fun. Return with your token address and its creation transaction.</p>
        <div className="launch-disclosure" data-testid="pump-fee-policy"><ShieldCheck size={18}/><p>Creator fees remain entirely with Pump.fun's existing mechanism. NEXUS does not redirect, change, or collect them.</p></div>
      </section>
      <section><div className="form-section-title"><span>02</span><h2>Verify your token</h2></div>
        <label>Token address<Input data-testid="pump-mint-input" placeholder="Solana mint address" value={form.mint} onChange={proofField('mint')} minLength={32} maxLength={44} required spellCheck={false} disabled={busy}/></label>
        <label>Creation transaction signature<Input data-testid="pump-signature-input" placeholder="Original Pump.fun creation transaction" value={form.signature} onChange={proofField('signature')} minLength={64} maxLength={88} required spellCheck={false} disabled={busy}/></label>
        <div className="inline-info" data-testid="pump-verification-wallet"><Wallet size={14}/>{wallet?`Creator wallet: ${shortAddress(wallet)}`:'Use the same wallet that created the token on Pump.fun.'}</div>
        {verified&&<div className="pump-verified-identity" data-testid="pump-verified-identity"><TokenAvatar token={{...verified,id:verified.mint,color:form.color}} size={40}/><span><strong data-testid="verified-token-name">{verified.name}</strong><small data-testid="verified-token-symbol">{verified.symbol} · Pump.fun creation verified</small></span><ShieldCheck size={20}/></div>}
        {error&&<p role="alert" className="pump-form-error" data-testid="pump-verification-error">{error}</p>}
      </section>
      <section><div className="form-section-title"><span>03</span><h2>Choose your neighborhood</h2></div>
        <div className="district-options">{Object.entries(districtNames).map(([id,name])=><button type="button" key={id} data-testid={`launch-district-${id}`} className={form.district===id?'selected':''} style={{'--district-color':colors[id]}} disabled={busy} onClick={()=>setForm({...form,district:id,color:colors[id]})}><span className="district-dot" style={{background:colors[id]}}/>{name}{form.district===id&&<Check size={14}/>}</button>)}</div>
        <label>Building accent<div className="color-options">{Object.values(colors).map(color=><button type="button" key={color} data-testid={`launch-color-${color.slice(1)}`} disabled={busy} aria-label={`Building color ${color}`} className={form.color===color?'selected':''} style={{background:color}} onClick={()=>setForm({...form,color})}>{form.color===color&&<Check size={14}/>}</button>)}</div></label>
      </section>
      <ActionButton data-testid="launch-submit" type="submit" disabled={busy} className="full-width">{busy?<LoaderCircle className="spin" size={17}/>:<ShieldCheck size={17}/>}{busy?step:!wallet?'Connect creator wallet':verified?'Add verified token to the world':'Verify Pump.fun token'}{!busy&&<ArrowUpRight size={17}/>}</ActionButton>
      <p className="inline-info" data-testid="world-registration-note">World registration signs no transaction and charges no launch fee. It does not create a second token.</p>
    </form>
    <aside className="launch-preview"><div className="preview-scene" style={{'--building-color':form.color}}><div className="preview-grid"/><div className="css-building"><div className="building-top"/><div className="building-front">{Array.from({length:24},(_,i)=><span key={i}/>)}</div><div className="building-side"/></div><span className="preview-token" data-testid="launch-preview-symbol">{verified?.symbol || 'YOUR TOKEN'}</span><div className="preview-plot"/></div><div className="preview-details"><span className="eyebrow">YOUR FUTURE ADDRESS</span><h2 data-testid="launch-preview-name">{verified?.name || 'An idea. A building. A beginning.'}</h2><div><span>District</span><strong data-testid="launch-preview-district">{districtNames[form.district]}</strong></div><div><span>Launch infrastructure</span><strong>Pump.fun</strong></div><div><span>World ownership</span><strong>Your creator wallet</strong></div></div><p className="preview-note">A small beginning. An unlimited skyline.</p></aside>
    </div>
  </main>;
}