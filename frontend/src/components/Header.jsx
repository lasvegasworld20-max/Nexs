import React,{useState,useEffect,useRef} from 'react';
import {Link,NavLink,useNavigate} from 'react-router-dom';
import {Search,Wallet,ArrowUpRight,Command,Globe2,Plus,Layers3} from 'lucide-react';
import {useWallet} from '../context/WalletContext';
import {shortAddress,money} from '../lib/api';
import {TokenAvatar,ActionButton} from './Shared';
export const Header=({tokens=[]})=>{
 const {wallet,balance,connect}=useWallet(),[query,setQuery]=useState(''),[focused,setFocused]=useState(false),navigate=useNavigate();
 const searchRef=useRef(null);
 useEffect(()=>{const handle=e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();searchRef.current?.focus();}};document.addEventListener('keydown',handle);return()=>document.removeEventListener('keydown',handle);},[]);
 const matches=tokens.filter(t=>`${t.name} ${t.symbol} ${t.mint}`.toLowerCase().includes(query.toLowerCase())).slice(0,6);
 return <header className="site-header" data-testid="site-header">
 <Link to="/" className="brand" data-testid="brand-home"><span className="brand-icon"><Layers3 strokeWidth={2.6}/></span>NEXUS<span className="brand-sub">WORLD</span></Link>
 <nav className="header-nav"><NavLink to="/" end data-testid="nav-explore"><Globe2 size={15}/>Explore</NavLink><NavLink to="/bounties" data-testid="nav-bounties">Bounties</NavLink><NavLink to="/leaderboard" data-testid="nav-leaderboard">Leaderboard</NavLink></nav>
 <div className="search-wrap"><Search size={16}/><input ref={searchRef} data-testid="world-search" value={query} onFocus={()=>setFocused(true)} onBlur={()=>setTimeout(()=>setFocused(false),180)} onChange={e=>setQuery(e.target.value)} placeholder="Search tokens or addresses" aria-label="Search tokens"/><kbd><Command size={11}/> K</kbd>
 {focused&&query&&<div className="search-results" data-testid="search-results">{matches.length?matches.map(t=><button data-testid={`search-result-${t.id}`} key={t.id} onClick={()=>{navigate(`/token/${t.id}`);setQuery('');setFocused(false);}}><TokenAvatar token={t}/><span><strong>{t.symbol}</strong><small>{t.name}</small></span><span>{money(t.market_cap)}</span><ArrowUpRight size={15}/></button>):<p data-testid="search-no-results">No tokens found</p>}</div>}
 </div><div className="network-badge" data-testid="network-badge"><span className="solana-mark">≋</span> Solana <span className="status-dot"/></div>
 <Link to="/launch" className="header-launch" data-testid="header-launch-token" title="Launch token" aria-label="Launch token"><Plus size={15}/><span>Launch token</span></Link>
 <ActionButton data-testid="connect-wallet-button" aria-label={wallet?'Manage wallet':'Connect wallet'} className="wallet-button" onClick={connect}><Wallet size={16}/>{wallet?<span>{shortAddress(wallet)}{balance!==null&&<small>{balance.toFixed(3)} SOL</small>}</span>:'Connect wallet'}</ActionButton>
 </header>;
};