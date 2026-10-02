import React,{useState} from 'react';
import {Link} from 'react-router-dom';
import {Heart,MessageCircle,Repeat2,Trash2,Megaphone,ArrowUpRight} from 'lucide-react';
import {toast} from 'sonner';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '../ui/dialog';
import {ActionButton} from '../Shared';
import {useWallet} from '../../context/WalletContext';
import {api,errorMessage} from '../../lib/api';
import {ProfileAvatar,AuthorLink} from './SocialIdentity';
export const PostCard=({post,onChange,onDeleted,showToken=false})=>{
 const {wallet,authenticate,connect}=useWallet(),[busy,setBusy]=useState(false),[confirm,setConfirm]=useState(false);
 const key=post.event_id || post.id;
 const interact=async(kind,active)=>{if(!wallet){connect();return;}setBusy(true);try{await authenticate();const {data}=await api.post(`/social/posts/${post.id}/${kind}`,{active});onChange?.({...post,...data});}catch(e){toast.error(errorMessage(e));}finally{setBusy(false);}};
 const remove=async()=>{setBusy(true);try{await authenticate();await api.post(`/social/posts/${post.id}/delete`);setConfirm(false);onDeleted?.();}catch(e){toast.error(errorMessage(e));}finally{setBusy(false);}};
 return <article className="social-post" data-testid={`social-post-${key}`}>
 {post.reposted_by&&<div className="social-repost-by" data-testid={`repost-by-${key}`}><Repeat2 size={12}/><Link data-testid={`reposter-${key}`} to={`/profile/${post.reposted_by.wallet}`}>{post.reposted_by.display_name} reposted</Link></div>}
 <div className="social-post-main"><Link data-testid={`post-avatar-link-${key}`} to={`/profile/${post.wallet}`}><ProfileAvatar profile={post.author}/></Link><div className="social-post-body"><div className="social-post-heading"><AuthorLink profile={post.author} creator={post.is_creator} testId={`post-author-${key}`}/><time data-testid={`post-time-${key}`} dateTime={post.created_at}>{new Date(post.created_at).toLocaleDateString(undefined,{month:'short',day:'numeric'})}</time>{wallet===post.wallet&&<button data-testid={`delete-post-${key}`} title="Delete post" aria-label="Delete post" onClick={()=>setConfirm(true)}><Trash2 size={13}/></button>}</div>
 {post.kind==='announcement'&&<div className="social-announcement-badge" data-testid={`announcement-${key}`}><Megaphone size={12}/>Creator announcement</div>}
 {showToken&&<Link data-testid={`post-community-${key}`} className="social-token-link" to={`/community/${post.token_id}`}>{post.token.symbol} community<ArrowUpRight size={12}/></Link>}
 {post.text&&<p className="social-post-text" data-testid={`post-content-${key}`}>{post.text}</p>}
 {post.media?.length>0&&<div className={`social-post-images count-${post.media.length}`}>{post.media.map(m=><a href={m.url} target="_blank" rel="noreferrer" key={m.id} data-testid={`post-image-link-${key}-${m.id}`}><img src={m.url} alt="Community attachment" data-testid={`post-image-${key}-${m.id}`} loading="lazy"/></a>)}</div>}
 <div className="social-post-actions"><Link data-testid={`reply-post-${key}`} to={`/community/${post.token_id}/post/${post.id}`} aria-label="View replies"><MessageCircle size={15}/><span>{post.replies}</span></Link><button data-testid={`repost-post-${key}`} aria-pressed={post.viewer_reposted} title={post.viewer_reposted?'Undo repost':'Repost'} className={post.viewer_reposted?'is-reposted':''} disabled={busy} onClick={()=>interact('repost',!post.viewer_reposted)}><Repeat2 size={16}/><span>{post.reposts}</span></button><button data-testid={`like-post-${key}`} aria-pressed={post.viewer_liked} title={post.viewer_liked?'Unlike':'Like'} className={post.viewer_liked?'is-liked':''} disabled={busy} onClick={()=>interact('like',!post.viewer_liked)}><Heart size={15} fill={post.viewer_liked?'currentColor':'none'}/><span>{post.likes}</span></button></div></div></div>
 <Dialog open={confirm} onOpenChange={setConfirm}><DialogContent className="nexus-dialog" data-testid="delete-post-dialog"><DialogTitle>Delete this post?</DialogTitle><DialogDescription>This removes it from the community feed.</DialogDescription><ActionButton data-testid="confirm-delete-post" onClick={remove} disabled={busy}>Delete post</ActionButton></DialogContent></Dialog>
 </article>;
};