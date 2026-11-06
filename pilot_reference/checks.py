from pathlib import Path
import numpy as np, pandas as pd
root=Path(__file__).resolve().parent
rng=np.random.default_rng(20261106)
data=pd.read_csv(root/'panel.csv',parse_dates=['date'])
for eps in (0,.05,.1):
 print('Threshold',eps)
 for name,subset in [('full',data),('matched_2022_2026',data[data.date>='2022-03-07']),('matched_no_ocr',data[(data.date>='2022-03-07')&(data.method=='text')]),('holdout_2025_26',data[data.date>='2025-01-01'])]:
  print(name)
  for c,b in subset.groupby('country'):
   b=b.copy()
   b['gap']=(b.offered-b.accepted).clip(lower=0).where(b.accepted<(1-eps)*b.offered,0)
   b['missing_bids']=(b.offered-b.bids).clip(lower=0).where(b.gap>0,0)
   bydate=b.groupby('date')[['offered','accepted','bids','gap','missing_bids']].sum()
   funded=bydate.accepted>=(1-eps)*bydate.offered
   nmask=((bydate.gap>0)&funded).sum()
   nactual=(b.gap>0).sum()
   when_enough=((b.gap>0)&(b.bids>=b.offered)).sum()
   byq=bydate.groupby(bydate.index.to_period('Q'))[['gap','missing_bids']].sum().to_numpy()
   sums=byq[rng.integers(len(byq),size=(3000,len(byq)))].sum(axis=1)
   bounds=np.nanquantile(np.divide(sums[:,1],sums[:,0],where=sums[:,0]>0,out=np.full(len(sums),np.nan)),[.025,.975])
   print(c,'events',len(bydate),'gap_tenors',nactual,'gaps_despite_sufficient_bids',when_enough,'weak_share',round(b.missing_bids.sum()/b.gap.sum(),3),'quarter_bootstrap',bounds.round(3),'met_total',funded.sum(),'masked',nmask,'whole_event_demand_gap',((bydate.bids<bydate.offered)&~funded).sum())
 for market,tests in pd.read_csv(root/f'predictions_{eps}.csv',parse_dates=['date']).groupby('country'):
  z=tests.copy()
  z=z.merge(data[['country','date','tenor','offered','accepted']],on=['country','date','tenor'])
  z['gap_amount']=(z.offered-z.accepted).clip(lower=0).where(z.target>0,0)
  for m in ('tenor_recent','lag_transition','logistic','hgb','transfer','pooled','no_yield_calendar'):
   p=z[[m+str(i) for i in range(3)]].to_numpy()
   z[m]=-np.log(np.maximum(p[np.arange(len(z)),z.target.to_numpy()],1e-10))
   top=z.iloc[np.argsort(p[:,0])[:int(len(z)*.25)]]
   print(market,m,'top_quarter_amount_capture',round(top.gap_amount.sum()/z.gap_amount.sum(),3), 'avg_loss',round(z[m].mean(),3))
  for model,bench in [('logistic','lag_transition'),('logistic','tenor_recent'),('hgb','tenor_recent')]:
   diff=z.assign(diff=z[model]-z[bench]).groupby('date').agg(delta=('diff','mean'))
   vals=diff.delta.to_numpy()
   if len(vals)<8:continue
   block_length=4
   ind=rng.integers(len(vals),size=(3000,(len(vals)+block_length-1)//block_length,1))
   sampled=((ind+np.arange(block_length))%len(vals)).reshape(3000,-1)[:,:len(vals)]
   print('DiffLogLoss',market,model,bench,round(vals.mean(),3),np.quantile(vals[sampled].mean(axis=1),[.025,.975]).round(3))
