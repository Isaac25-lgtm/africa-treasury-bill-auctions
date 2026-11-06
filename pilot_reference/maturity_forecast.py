from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
p=Path(__file__).resolve().parent
d=pd.read_csv(p/'panel.csv',parse_dates=['date'])
d['ratio']=d.bids/d.offered;d['fill']=d.accepted/d.offered
d['shareO']=d.offered/d.groupby(['country','date']).offered.transform('sum')
d['shareA']=d.accepted/d.groupby(['country','date']).accepted.transform('sum')
d['delta']=d.tenor*(d.shareA-d.shareO)
dd=d.pivot(index=['country','date'],columns='tenor',values=['ratio','fill','shareO'])
dd.columns=['%s_%d'%c for c in dd.columns]
dd=dd.join(d.groupby(['country','date']).delta.sum()).sort_index().reset_index()
g=dd.groupby('country')
for c in [x for x in dd if x.startswith(('ratio','fill','shareO'))]+['delta']:
 dd[c+'_lag']=g[c].shift()
 dd[c+'_roll']=g[c].transform(lambda y:y.shift().rolling(6,min_periods=3).median())
feat=[c for c in dd if c.endswith(('_lag','_roll'))]
for m,b in dd.groupby('country'):
 obs=[]
 for start in pd.date_range('2025-01-01','2026-11-01',freq='MS'):
  hold=b[b.date.between(start,start+pd.offsets.MonthBegin(1),inclusive='left')].copy()
  fit=b[b.date<start]
  if hold.empty:continue
  hold['zero']=0
  hold['recent']=hold.delta_roll
  hold['last']=hold.delta_lag
  for name,alg in [('ridge',Ridge(alpha=12)),('boosted',HistGradientBoostingRegressor(max_iter=70,max_leaf_nodes=5,min_samples_leaf=12,l2_regularization=5,random_state=3))]:
   hold[name]=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),alg).fit(fit[feat],fit.delta).predict(hold[feat])
  obs.append(hold)
 w=pd.concat(obs)
 for yr,z in [('all',w),('2025',w[w.date.dt.year==2025]),('2026',w[w.date.dt.year==2026])]:
  print(m,yr,len(z),{name:round(np.abs(z.delta-z[name]).mean(),1) for name in ['zero','recent','last','ridge','boosted']})
