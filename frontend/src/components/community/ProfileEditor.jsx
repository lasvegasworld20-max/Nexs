import React,{useRef,useState,useEffect} from 'react';
import {ImagePlus} from 'lucide-react';
import {toast} from 'sonner';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '../ui/dialog';
import {Input} from '../ui/input';
import {Textarea} from '../ui/textarea';
import {ActionButton} from '../Shared';
import {useWallet} from '../../context/WalletContext';
import {api,errorMessage} from '../../lib/api';
import {uploadImage} from '../../lib/nexusLaunch';
export const ProfileEditor=({profile,open,onOpenChange,onSaved})=>{
 const {authenticate}=useWallet(),file=useRef(),[form,setForm]=useState({display_name:'',handle:'',bio:'',avatar_id:null}),[avatar,setAvatar]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{if(open){setForm({display_name:profile.display_name || '',handle:profile.handle || '',bio:profile.bio || '',avatar_id:profile.avatar_id || null});setAvatar(profile.avatar_url);setError('');}},[open,profile]);
 const upload=async e=>{const image=e.target.files?.[0];if(!image)return;setBusy(true);try{await authenticate();const media=await uploadImage(image,'avatar');setAvatar(media.url);setForm({...form,avatar_id:media.id});}catch(e){setError(errorMessage(e));}finally{setBusy(false);e.target.value='';}};
 const save=async e=>{e.preventDefault();setBusy(true);setError('');try{await authenticate();const {data}=await api.patch('/profiles/me',form);onSaved(data);onOpenChange(false);toast.success('Profile updated');}catch(e){setError(errorMessage(e));}finally{setBusy(false);}};
 return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="nexus-dialog" data-testid="profile-editor"><DialogTitle>Your place in the community.</DialogTitle><DialogDescription>Your profile is linked to your wallet.</DialogDescription><form className="nexus-form" onSubmit={save}><input ref={file} data-testid="profile-avatar-file" className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={upload}/><button data-testid="profile-upload-avatar" className="social-upload-button" type="button" disabled={busy} onClick={()=>file.current?.click()}>{avatar?<img src={avatar} alt="Profile avatar"/>:<ImagePlus size={22}/>}<span>Change profile image<small>Up to 5 MB</small></span></button><label>Display name<Input data-testid="profile-display-name" value={form.display_name} maxLength={48} required onChange={e=>setForm({...form,display_name:e.target.value})}/></label><label>Username<Input data-testid="profile-handle" value={form.handle} minLength={3} maxLength={24} pattern="[A-Za-z0-9_]+" placeholder="your_name" required onChange={e=>setForm({...form,handle:e.target.value})}/></label><label>Bio<Textarea data-testid="profile-bio" value={form.bio} maxLength={280} onChange={e=>setForm({...form,bio:e.target.value})}/></label>{error&&<p role="alert" className="social-error" data-testid="profile-error">{error}</p>}<ActionButton data-testid="profile-save" disabled={busy}>{busy?'Saving…':'Save profile'}</ActionButton></form></DialogContent></Dialog>;
};