import axios from 'axios';
export const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({baseURL: API_URL, timeout: 45000});
api.interceptors.request.use(config => {
  const token = sessionStorage.getItem('nexus-session');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(response=>response,error=>{
  if(error?.response?.status===401){sessionStorage.removeItem('nexus-session');sessionStorage.removeItem('nexus-wallet');}
  return Promise.reject(error);
});
export const errorMessage = e => {
  const detail=e?.response?.data?.detail;
  return typeof detail==='string'?detail:e?.message || 'Something went wrong. Please try again.';
};
export const money=(n, compact=true)=> n==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:compact?'compact':'standard',maximumFractionDigits:2}).format(n);
export const price=n=>n==null?'—':n<1?`$${Number(n).toPrecision(4)}`:money(n,false);
export const shortAddress=a=>a?`${a.slice(0,4)}…${a.slice(-4)}`:'';
export const districtNames={meme:'Meme Quarter',defi:'DeFi Heights',ai:'Neural District',culture:'The Waterfront'};
export const colors={meme:'#b6f36e',defi:'#f1bd6c',ai:'#bca4f7',culture:'#68d5df'};