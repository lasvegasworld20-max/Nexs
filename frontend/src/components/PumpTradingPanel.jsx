import React,{useState} from 'react';
import {ArrowUpRight,ShieldCheck,ExternalLink} from 'lucide-react';
import {TokenAvatar,ExternalLink as ExplorerLink} from './Shared';
import {shortAddress,price,money} from '../lib/api';

export const PumpTradingPanel=({token})=>{
 const [side,setSide]=useState('buy');
 const url=`${process.env.REACT_APP_PUMP_FUN_URL}/coin/${encodeURIComponent(token.mint)}`;
 return <section className="swap-panel" data-testid="pump-trading-panel">
  <div className="trade-tabs"><button data-testid="buy-token-tab" className={side==='buy'?'active':''} onClick={()=>setSide('buy')}>Buy {token.symbol}</button><button data-testid="sell-token-tab" className={side==='sell'?'active sell':''} onClick={()=>setSide('sell')}>Sell {token.symbol}</button></div>
  <div className="trade-network" data-testid="trade-network"><span className="status-dot"/>Solana mainnet<span>Pump.fun</span></div>
  <div className="pump-trade-body"><div className="pump-trade-identity"><TokenAvatar token={token} size={45}/><div><strong data-testid="pump-trade-symbol">{token.symbol}</strong><span data-testid="pump-trade-address">{shortAddress(token.mint)}</span></div><ShieldCheck size={20}/></div>
   <dl className="pump-trade-metrics"><div><dt>Price</dt><dd data-testid="pump-trade-price">{price(token.price)}</dd></div><div><dt>Market cap</dt><dd data-testid="pump-trade-market-cap">{money(token.market_cap)}</dd></div><div><dt>Market</dt><dd data-testid="pump-market-stage">{token.pump_complete?'Graduated':'Bonding curve'}</dd></div></dl>
   <a href={url} target="_blank" rel="noopener noreferrer" className="action-button pump-trade-button" data-testid="trade-on-pump"><ExternalLink size={15}/>{side==='buy'?'Buy':'Sell'} on Pump.fun<ArrowUpRight size={16}/></a>
   <p data-testid="pump-trade-handoff">Opens the official token page. Select {side==='buy'?'Buy':'Sell'} there and approve with your wallet.</p>
  </div>
  <div className="swap-footer"><ExplorerLink href={url} testId="pump-chart-link">Chart & full trading activity on Pump.fun</ExplorerLink><span data-testid="pump-creator-fees"><ShieldCheck size={13}/>Pump.fun creator fees remain unchanged.</span></div>
 </section>;
};