from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss
r=Path(__file__).resolve().parent
p=pd.read_csv(r/'panel.csv',parse_dates=['date']).groupby(['country','date'])[['offered','bids','accepted']].sum().reset_index()
gh=pd.read_csv(r/'ghana.csv',parse_dates=['date'])
d=pd.concat([p,gh[p.columns]],ignore_index=True).sort_values(['country','date'])
d=d[(d.date>=gh.date.min())&(d.date<=gh.date.max())].copy()
d['x_bids']=d.bids/d.offered;d['x_fill']=d.accepted/d.offered;d['x_not_filled']=1-d.accepted/d.bids
g=d.groupby('country')
d['gap']=g.date.diff().dt.days
for c in ['x_bids','x_fill','x_not_filled']:
 d[c+'_lag']=g[c].shift()
 d[c+'_roll']=g[c].transform(lambda s:s.shift().rolling(8,min_periods=3).median())
features=[c for c in d if c.endswith(('_lag','_roll'))]
d['test']=np.where(d.x_fill>=1,0,np.where(d.x_bids<1,1,2))
def predict(fit,test,model):
 clf=make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),model).fit(fit[features],fit.test)
 pp=np.full((len(test),3),1e-5); pp[:,clf.classes_]=clf.predict_proba(test[features])
 return pp/pp.sum(axis=1,keepdims=True)
def hist(y):return (np.bincount(y,minlength=3)+1)/(len(y)+3)
for k,block in d.groupby('country'):
 ys=[]; pools=[[] for _ in range(6)]
 for month in pd.date_range('2025-01-01','2026-10-01',freq='MS'):
  w=block[(block.date>=month)&(block.date<month+pd.offsets.MonthBegin(1))]
  if w.empty:continue
  fit=block[block.date<month]
  foreign=d[(d.date<month)&(d.country!=k)]
  for row in w.itertuples():
   av=block[block.date<row.date]
   pools[0].append(hist(av.test))
   pools[1].append(hist(av.test.tail(12)))
   val=np.where(av.x_fill_lag>=1,0,np.where(av.x_bids_lag<1,1,2))
   lag_class=0 if row.x_fill_lag>=1 else (1 if row.x_bids_lag<1 else 2)
   pools[2].append(hist(av.loc[val==lag_class,'test']))
  pools[3].extend(predict(fit,w,LogisticRegression(C=.35,max_iter=300)))
  pools[4].extend(predict(fit,w,HistGradientBoostingClassifier(max_iter=65,max_leaf_nodes=5,min_samples_leaf=12,l2_regularization=4,random_state=0)))
  pools[5].extend(predict(foreign,w,LogisticRegression(C=.35,max_iter=300)))
  ys.extend(w.test)
 print(k,len(ys),np.bincount(ys,minlength=3),'log-loss',dict((n,round(log_loss(ys,np.array(x),labels=[0,1,2]),3)) for n,x in zip(['historical','recent','transition','logistic','trees','foreign_only'],pools)))
