import React,{useEffect,useState} from 'react';
import {Activity} from 'lucide-react';
import {api,shortAddress} from '../lib/api';
import {Empty,Loading,ExternalLink} from './Shared';
export const TradingActivity=({token})=>{
 const [data,setData]=useState(null);
 useEffect(()=>{let active=true;setData(null);api.get(`/tokens/${token.id}/trading-activity`).then(r=>{if(active)setData(r.data);}).catch(()=>{if(active)setData({trades:[],scope:'Trading activity is temporarily unavailable.'});});return()=>{active=false;};},[token.id]);
 if(!data)return <Loading text="Reading confirmed trades…"/>;
 return <div data-testid="pump-trading-activity"><p className="inline-info" data-testid="pump-activity-scope">{data.scope}</p>{data.trades.length?<div className="pump-trade-list">{data.trades.map(t=><div key={t.id} data-testid={`pump-trade-${t.id}`}><span className={t.side==='buy'?'positive':'negative'}>{t.side.toUpperCase()}</span><span>{shortAddress(t.wallet)}<small>{new Date(t.timestamp*1000).toLocaleString()}</small></span><strong>{t.sol_amount.toLocaleString(undefined,{maximumFractionDigits:5})} SOL</strong><ExternalLink testId={`pump-trade-tx-${t.id}`} href={`${process.env.REACT_APP_EXPLORER_URL}/tx/${t.signature}`}>Tx</ExternalLink></div>)}</div>:<Empty icon={Activity} title="No trades returned in this sample." text="Complete market activity is available on the official token page." testId="pump-trades-empty"/>}<ExternalLink testId="pump-full-trading-activity" href={`${process.env.REACT_APP_PUMP_FUN_URL}/coin/${token.mint}`}>View full activity on Pump.fun</ExternalLink></div>;
};