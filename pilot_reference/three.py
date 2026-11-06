from pathlib import Path
import numpy as np,pandas as pd
r=Path(__file__).resolve().parent
p=pd.read_csv(r/'panel.csv',parse_dates=['date'])
gh_file=r/'ghana.csv' if (r/'ghana.csv').exists() else r/'ghana_partial.csv'
g=pd.read_csv(gh_file,parse_dates=['date'])
data=p.groupby(['country','date'])[['offered','bids','accepted']].sum().reset_index()
data=pd.concat([data,g[['country','date','offered','bids','accepted']]],ignore_index=True)
end=g.date.max()
for name,s in [('shared',data[(data.date>=g.date.min())&(data.date<=end)]),('2025_to_latest_ghana',data[(data.date>='2025-01-01')&(data.date<=end)]),('shared_exclude_offer_mismatches',data[(data.date>=g.date.min())&(data.date<=end)&(~data.date.isin(pd.to_datetime(['2026-07-13','2026-09-30'])))] )]:
 for tol in [0,.05,.10]:
  print(name,tol)
  for country,z in s.groupby('country'):
   ss=z[z.accepted<(1-tol)*z.offered]
   b=(ss.offered-ss.bids).clip(lower=0)
   gap=(ss.offered-ss.accepted).clip(lower=0)
   print(country,len(z),len(ss),sum(ss.bids>=ss.offered),round(b.sum()/gap.sum(),4),z.date.min().date(),z.date.max().date())
