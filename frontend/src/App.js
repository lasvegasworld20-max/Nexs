import React,{useEffect,useState,useCallback} from 'react';
import {BrowserRouter,Routes,Route,Link} from 'react-router-dom';
import {WalletProvider} from './context/WalletContext';
import {Header} from './components/Header';
import {Toaster} from './components/ui/sonner';
import {api} from './lib/api';
import World from './pages/World';
import TokenDashboard from './pages/TokenDashboard';
import Launch from './pages/Launch';
import Bounties from './pages/Bounties';
import Leaderboard from './pages/Leaderboard';
import './App.css';
function App(){
 const [world,setWorld]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(false);
 const reload=useCallback(async()=>{try{const {data}=await api.get('/world');setWorld(data);setError(false);}catch{setError(true);}finally{setLoading(false);}},[]);
 useEffect(()=>{reload();const timer=setInterval(reload,60000);return()=>clearInterval(timer);},[reload]);
 return <BrowserRouter><WalletProvider><Header tokens={world?.tokens || []}/><Routes>
 <Route path="/" element={<World world={world} loading={loading} error={error} reload={reload}/>}/>
 <Route path="/token/:id" element={<TokenDashboard world={world} reloadWorld={reload}/>}/>
 <Route path="/launch" element={<Launch reloadWorld={reload}/>}/>
 <Route path="/bounties" element={<Bounties tokens={world?.tokens || []}/>}/>
 <Route path="/leaderboard" element={<Leaderboard world={world} loading={loading}/>}/>
 <Route path="*" element={<div className="not-found" data-testid="not-found"><h1>Uncharted territory.</h1><Link to="/" data-testid="return-world-404">Return to the world →</Link></div>}/>
 </Routes><Toaster theme="dark" position="bottom-center" richColors/></WalletProvider></BrowserRouter>;
}
export default App;