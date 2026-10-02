import React,{useEffect,useState,useCallback} from 'react';
import {Link} from 'react-router-dom';
import {MessageSquare,ArrowUpRight,UserCircle2,LockKeyhole} from 'lucide-react';
import {api,errorMessage} from '../../lib/api';
import {useWallet} from '../../context/WalletContext';
import {Empty,Loading,ActionButton} from '../Shared';
import {PostComposer} from './PostComposer';
import {PostCard} from './PostCard';
export const TokenCommunity=({token,compact=false})=>{
 const {wallet,connect}=useWallet(),[tab,setTab]=useState('all'),[items,setItems]=useState([]),[cursor,setCursor]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const load=useCallback(async(append=false,after=null)=>{if(!token.community_enabled){setLoading(false);return;}setLoading(true);try{const {data}=await api.get(`/communities/${token.id}/feed`,{params:{tab,...(after?{cursor:after}:{})}});setItems(old=>append?[...old,...data.items]:data.items);setCursor(data.next_cursor);setError('');}catch(e){setError(errorMessage(e));}finally{setLoading(false);}},[token.id,token.community_enabled,tab]);
 useEffect(()=>{load();},[load,wallet]);
 if(!token.community_enabled)return <Empty icon={LockKeyhole} title="A community starts with a NEXUS launch." text="This token belongs to the visual catalog. Its community is not enabled." testId="community-nexus-only"><Link to="/launch" data-testid="community-launch-token" className="text-cta">Launch through NEXUS<ArrowUpRight size={14}/></Link></Empty>;
 const update=post=>setItems(items.map(p=>p.id===post.id?{...p,...post,event_id:p.event_id,reposted_by:p.reposted_by}:p));
 return <div className="token-social-community" data-testid="token-social-community"><div className="social-community-top"><span><MessageSquare size={15}/>{token.symbol} community</span>{wallet?<Link to={`/profile/${wallet}`} data-testid="community-my-profile"><UserCircle2 size={15}/>My profile</Link>:<button data-testid="community-connect" onClick={connect}>Connect wallet</button>}{compact&&<Link data-testid="open-full-community" to={`/community/${token.id}`}>Open community<ArrowUpRight size={14}/></Link>}</div><PostComposer token={token} onPosted={()=>load()}/><div className="social-feed-tabs">{[['all','Community'],['following','Following'],['announcements','Announcements']].map(([key,name])=><button key={key} data-testid={`community-feed-${key}`} className={tab===key?'active':''} onClick={()=>setTab(key)}>{name}</button>)}</div>
 {error?<div className="social-error" data-testid="community-feed-error">{error}<button data-testid="retry-community-feed" onClick={()=>load()}>Try again</button></div>:loading&&!items.length?<Loading text="Loading community…"/>:items.length?items.map(post=><PostCard key={post.event_id} post={post} onChange={update} onDeleted={()=>load()}/>):<Empty icon={MessageSquare} title={tab==='following'?'Your circle starts here.':tab==='announcements'?'No announcements yet.':'Be the first voice in this territory.'} text={tab==='following'?'Posts and reposts from people you follow appear here.':'Share an update, a question, or something worth building together.'} testId="social-feed-empty"/>}
 {cursor&&<button className="social-load-more" data-testid="community-load-more" disabled={loading} onClick={()=>load(true,cursor)}>{loading?'Loading…':'Load more'}</button>}
 </div>;
};