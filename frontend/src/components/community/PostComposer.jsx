import React,{useRef,useState} from 'react';
import {ImagePlus,X,Send,Megaphone,LoaderCircle} from 'lucide-react';
import {toast} from 'sonner';
import {Textarea} from '../ui/textarea';
import {ActionButton} from '../Shared';
import {useWallet} from '../../context/WalletContext';
import {api,errorMessage} from '../../lib/api';
import {uploadImage} from '../../lib/nexusLaunch';
export const PostComposer=({token,parentId=null,onPosted})=>{
 const {wallet,connect,authenticate}=useWallet(),[text,setText]=useState(''),[media,setMedia]=useState([]),[announcement,setAnnouncement]=useState(false),[busy,setBusy]=useState(false),[uploading,setUploading]=useState(false),[error,setError]=useState('');
 const input=useRef(null),suffix=parentId || 'root';
 const images=async e=>{const files=Array.from(e.target.files || []);if(!files.length)return;setUploading(true);setError('');try{await authenticate();if(files.length+media.length>4)throw new Error('A post can contain up to 4 images');const results=[];for(const file of files)results.push(await uploadImage(file,'community',token.id));setMedia(old=>[...old,...results]);}catch(e){setError(errorMessage(e));}finally{setUploading(false);e.target.value='';}};
 const post=async e=>{e.preventDefault();if(!wallet){connect();return;}setBusy(true);setError('');try{await authenticate();await api.post(`/communities/${token.id}/posts`,{text,media_ids:media.map(m=>m.id),parent_id:parentId,kind:announcement?'announcement':'post'});setText('');setMedia([]);setAnnouncement(false);onPosted?.();toast.success(parentId?'Reply published':'Post published');}catch(e){setError(errorMessage(e));}finally{setBusy(false);}};
 return <form className="social-composer" onSubmit={post} data-testid={`post-composer-${suffix}`}><Textarea data-testid={`post-text-${suffix}`} value={text} onChange={e=>setText(e.target.value)} maxLength={1000} placeholder={parentId?'Write your reply…':`What's happening in ${token.symbol}?`} disabled={busy}/>
 {media.length>0&&<div className="social-compose-images">{media.map(m=><div key={m.id}><img src={m.url} alt="Attachment" data-testid={`attachment-${m.id}`}/><button type="button" data-testid={`remove-attachment-${m.id}`} aria-label="Remove image" onClick={()=>setMedia(media.filter(i=>i.id!==m.id))}><X size={14}/></button></div>)}</div>}
 <div className="social-compose-toolbar"><input ref={input} className="sr-only" data-testid={`post-images-${suffix}`} type="file" multiple accept="image/png,image/jpeg,image/webp" onChange={images}/><button type="button" data-testid={`post-add-image-${suffix}`} title="Add images" aria-label="Add images" disabled={uploading||media.length>=4||busy} onClick={()=>{if(!wallet){connect();return;}input.current?.click();}}>{uploading?<LoaderCircle className="spin" size={17}/>:<ImagePlus size={17}/>}</button>
 {!parentId&&wallet===token.creator&&<label className="social-announcement-control"><input type="checkbox" data-testid="post-announcement-toggle" checked={announcement} onChange={e=>setAnnouncement(e.target.checked)}/><Megaphone size={14}/>Announcement</label>}
 <span className="social-text-count" data-testid={`post-text-count-${suffix}`}>{text.length}/1000</span><ActionButton data-testid={`publish-post-${suffix}`} type="submit" disabled={busy||uploading||(!text.trim()&&!media.length)}><Send size={13}/>{busy?'Publishing…':wallet?(parentId?'Reply':'Post'):'Connect & post'}</ActionButton></div>
 {error&&<p className="social-error" role="alert" data-testid={`post-error-${suffix}`}>{error}</p>}</form>;
};