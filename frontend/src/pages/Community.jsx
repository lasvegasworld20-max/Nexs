import React,{useEffect,useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {ArrowLeft,MessageSquare} from 'lucide-react';
import {api,errorMessage} from '../lib/api';
import {TokenAvatar,Loading,Empty} from '../components/Shared';
import {TokenCommunity} from '../components/community/TokenCommunity';
import {PostComposer} from '../components/community/PostComposer';
import {PostCard} from '../components/community/PostCard';
export default function Community(){
 const {id,postId}=useParams(),[token,setToken]=useState(null),[post,setPost]=useState(null),[replies,setReplies]=useState([]),[error,setError]=useState('');
 useEffect(()=>{let alive=true;setToken(null);setError('');api.get(`/tokens/${id}`).then(r=>{if(alive)setToken(r.data);}).catch(e=>{if(alive)setError(errorMessage(e));});return()=>{alive=false;};},[id]);
 const loadThread=async()=>{try{const [root,list]=await Promise.all([api.get(`/social/posts/${postId}`),api.get(`/social/posts/${postId}/replies`)]);if(root.data.token_id!==id)throw new Error('This post belongs to another community');setPost(root.data);setReplies(list.data);setError('');}catch(e){setError(errorMessage(e));}};
 useEffect(()=>{setPost(null);setReplies([]);if(postId)loadThread();},[postId,id]);
 if(error)return <main className="content-page"><Empty icon={MessageSquare} title={error} testId="community-page-error"><Link to={`/token/${id}`} data-testid="community-error-back" className="text-cta">Back to Token Hub</Link></Empty></main>;
 if(!token)return <main className="content-page"><Loading/></main>;
 return <main className="content-page social-page" data-testid="community-page"><div className="page-breadcrumb"><Link to={`/token/${id}`} data-testid="community-back-hub"><ArrowLeft size={15}/>Token Hub</Link><span>/</span><Link to={`/community/${id}`} data-testid="community-root-link">{token.symbol} Community</Link>{postId&&<><span>/</span><span>Conversation</span></>}</div><div className="social-page-heading"><TokenAvatar token={token} size={48}/><div><span className="eyebrow">NEXUS COMMUNITY</span><h1 data-testid="community-page-title">{token.name}</h1></div><Link data-testid="community-token-hub" to={`/token/${id}`}>Token Hub ↗</Link></div>
 {!token.community_enabled?<TokenCommunity token={token}/>:postId?<section className="social-thread" data-testid="social-thread">{post?<><PostCard post={post} onChange={setPost} onDeleted={()=>{window.location.assign(`/community/${id}`);}}/><PostComposer token={token} parentId={post.id} onPosted={loadThread}/><h2 className="social-reply-heading" data-testid="thread-reply-count">Replies · {replies.length}</h2>{replies.map(r=><PostCard key={r.id} post={r} onChange={updated=>setReplies(replies.map(x=>x.id===updated.id?updated:x))} onDeleted={loadThread}/>)}</>:<Loading text="Opening conversation…"/>}</section>:<TokenCommunity token={token}/>}
 </main>;
}