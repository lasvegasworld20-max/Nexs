import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid} from 'recharts';
import {ChartNoAxesCombined} from 'lucide-react';
import {api, price} from '../lib/api';
import {Loading, Empty} from './Shared';

export const PriceChart = ({token}) => {
  const [period, setPeriod] = useState('24H');
  const [candles, setCandles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState('GeckoTerminal');
  const [size, setSize] = useState({width: 0, height: 0});
  const container = useRef(null);

  useLayoutEffect(() => {
    const element = container.current;
    if (!element) return;
    const measure = () => {
      const width = Math.floor(element.clientWidth);
      const height = Math.floor(element.clientHeight);
      setSize(previous => previous.width === width && previous.height === height ? previous : {width, height});
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setCandles([]);
    api.get(`/tokens/${token.id}/chart`, {params: {period}})
      .then(response => { if (active) { setCandles(response.data.candles); setSource(response.data.source || 'Market data'); } })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [period, token.id]);

  const tickTime = timestamp => ['1H', '24H'].includes(period)
    ? new Date(timestamp * 1000).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit', hour12: false})
    : new Date(timestamp * 1000).toLocaleDateString('en-US', {month: 'short', day: 'numeric'});

  return <section className="price-chart-section" data-testid="price-chart-section">
    <div className="chart-toolbar">
      <span data-testid="chart-pair">{token.symbol} / USD <small>Price</small></span>
      <div className="period-controls">{['1H', '24H', '7D', '30D'].map(value =>
        <button key={value} data-testid={`chart-period-${value.toLowerCase()}`} className={value === period ? 'active' : ''} onClick={() => setPeriod(value)}>{value}</button>
      )}</div>
    </div>
    <div className="chart-area" ref={container} data-testid="chart-area">
      {loading ? <Loading text="Loading price history…"/> : candles.length ? (
        size.width > 0 && size.height > 0 && <AreaChart width={size.width} height={size.height} data={candles} margin={{top: 20, right: 14, bottom: 4, left: 10}}>
          <defs><linearGradient id="price-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b6f36e" stopOpacity={.24}/><stop offset="100%" stopColor="#b6f36e" stopOpacity={0}/></linearGradient></defs>
          <CartesianGrid stroke="#ffffff08" vertical={false}/>
          <XAxis dataKey="time" axisLine={false} tickLine={false} minTickGap={48} tick={{fill: '#718178', fontSize: 10}} tickFormatter={tickTime}/>
          <YAxis domain={['auto', 'auto']} orientation="right" axisLine={false} tickLine={false} width={78} tick={{fill: '#718178', fontSize: 10}} tickFormatter={value => price(value)}/>
          <Tooltip contentStyle={{background: '#131b17', border: '1px solid #354336', fontSize: 12}} formatter={value => [price(value), 'Price']} labelFormatter={value => new Date(value * 1000).toLocaleString()}/>
          <Area type="monotone" dataKey="close" stroke="#b6f36e" strokeWidth={2} fill="url(#price-fill)" isAnimationActive={false}/>
        </AreaChart>
      ) : <Empty icon={ChartNoAxesCombined} title="Price history unavailable" text="Historical candles haven't been returned by the market data provider." testId="chart-unavailable"/>}
    </div>
    <div className="chart-source" data-testid="chart-source">{source} <span>USD · {period}</span></div>
  </section>;
};