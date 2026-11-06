from pathlib import Path
import numpy as np,pandas as pd
root=Path(__file__).resolve().parent
df=pd.read_csv(root/'panel.csv',parse_dates=['date'])
z=df[df.date>='2022-03-07'].copy()
z['O_days']=z.offered*z.tenor
z['A_days']=z.accepted*z.tenor
d=z.groupby(['country','date'])[['offered','bids','accepted','O_days','A_days']].sum()
d['shift']=d.A_days/d.accepted-d.O_days/d.offered
d['meet']=d.accepted>=d.offered
for c,g in d.groupby(level=0):
 for n,s in [('all',g),('2025+',g[g.index.get_level_values('date')>='2025-01-01']),('met',g[g.meet])]:
  print(c,n,len(s),'maturity shift mean med q1 q3',s['shift'].mean().round(2),s['shift'].quantile([.5,.25,.75]).round(2).to_list(),'shorter_by30',sum(s['shift']<=-30),'longer_by30',sum(s['shift']>=30))
 g=g.copy()
 g['no_bid_gap']=(g.offered-g.bids).clip(lower=0)
 g['total_gap']=(g.offered-g.accepted).clip(lower=0)
 print(c,'aggregate share',g['no_bid_gap'].sum()/g['total_gap'].sum(),'by year')
 print(g.groupby(g.index.get_level_values('date').year)[['no_bid_gap','total_gap']].sum().assign(share=lambda x:x.no_bid_gap/x.total_gap))
if (root/'ghana.csv').exists():
 a=pd.read_csv(root/'ghana.csv',parse_dates=['date'])
 print('GH notices',len(a),a.date.min(),a.date.max())
 for eps in [0,.05,.10]:
  s=a[a.accepted<(1-eps)*a.offered].copy()
  s['missing_bids']=(s.offered-s.bids).clip(lower=0)
  s['shortfall']=(s.offered-s.accepted).clip(lower=0)
  print('GH',eps,len(s),'shortfalls',(s.bids>=s.offered).sum(),'despite volume',s.missing_bids.sum()/s.shortfall.sum(),'volume from thin bidding')
