import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, balanced_accuracy_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

root=Path(__file__).resolve().parent
raw=pd.read_csv(root/'panel.csv',parse_dates=['date']).sort_values(['country','tenor','date']).reset_index(drop=True)
raw=raw[raw.date<=pd.Timestamp('2026-11-09')].copy()
raw['demand']=raw.bids/raw.offered
raw['fill']=raw.accepted/raw.offered
raw['rejection_fraction']=1-raw.accepted/raw.bids
raw['size_share']=raw.offered/raw.groupby(['country','date']).offered.transform('sum')
g=raw.groupby(['country','tenor'])
raw['gap']=g.date.diff().dt.days
raw['offer_change']=np.log(raw.offered/g.offered.shift(1))
for c in ['demand','fill','rejection_fraction','yield_pct']:
    raw[c+'_lag']=g[c].shift(1)
    raw[c+'_roll']=g[c].transform(lambda s:s.shift(1).rolling(6,min_periods=3).median())
raw['yield_delta_lag']=g.yield_pct.diff().groupby([raw.country,raw.tenor]).shift(1)
raw['tenor']=raw.tenor.astype(str)
raw['month_sin']=np.sin((raw.date.dt.month-1)*np.pi/6)
raw['month_cos']=np.cos((raw.date.dt.month-1)*np.pi/6)
raw['qend']=raw.date.dt.month.isin([3,6,9,12]).astype(int)
base_feat=['size_share','offer_change','demand_lag','fill_lag','rejection_fraction_lag','demand_roll','fill_roll','rejection_fraction_roll']
all_feat=base_feat+['gap','yield_delta_lag','month_sin','month_cos','qend']

def categorize(t,eps):
    return np.where(t['fill']>=1-eps,0,np.where(t['demand']<1-eps,1,2))
def histogram(train):
    return (np.bincount(train,minlength=3)+1)/(len(train)+3)
def model_prob(model,fit,group,feats,cats):
    pre=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),cats),
                           ('num',make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler()),feats)])
    fit_model=make_pipeline(pre,model).fit(fit,fit.target)
    pp=fit_model.predict_proba(group)
    res=np.full((len(group),3),1e-5)
    res[:,fit_model.classes_]=pp
    return res/res.sum(axis=1,keepdims=True)

for ep in (0,.05,.10):
    raw['target']=categorize(raw,ep)
    print('\nTHRESHOLD',ep)
    for market,block in raw.groupby('country'):
        if len(block)==0:continue
        vol_short=(block.offered-block.accepted).clip(lower=0)
        vol_weak=(block.offered-block.bids).clip(lower=0)
        events=block.groupby('date')[['offered','bids','accepted']].sum()
        events['fill']=events.accepted/events.offered; events['demand']=events.bids/events.offered
        events['target']=categorize(events,ep)
        near=(block.target==2)&(block.demand<1)
        overallmask=(block.target>0)
        annual=block.groupby(block.date.dt.year).date.nunique().to_dict()
        print(market,block.date.min().date(),block.date.max().date(),block.date.nunique(),len(block),'tenor states',np.bincount(block.target,minlength=3),'auction states',np.bincount(events.target,minlength=3),'near-cutoff mixed',near.sum(),'weak volume share',round(vol_weak[overallmask].sum()/vol_short[overallmask].sum(),4),'date count',annual)
        print('total cover masking tenor shortfall dates',sum((events.target==0)&(block.groupby('date').target.max()>0)))
    targets=[]
    probs={k:[] for k in ('hist','tenor_recent','lag_transition','logistic','hgb','transfer','pooled','no_yield_calendar','history_only','adaptive_blend')}
    starts=pd.date_range('2025-01-01','2026-11-01',freq='MS')
    for start in starts:
        test=raw[(raw.date>=start)&(raw.date<start+pd.offsets.MonthBegin(1))].copy()
        train=raw[raw.date<start].copy()
        if not len(test):continue
        for market,group in test.groupby('country'):
            fit=train[train.country==market]
            other=train[train.country!=market]
            if len(fit)<40 or fit.target.nunique()<2 or other.target.nunique()<2:
                continue
            ph=[]; pr=[]; pt=[]
            for row in group.itertuples():
                tenor=raw[(raw.country==market)&(raw.tenor==row.tenor)&(raw.date<row.date)]
                ph.append(histogram(tenor.target))
                # All previous rows available at the start of the forecast month.
                pr.append(histogram(tenor.target.tail(12)))
                prevclass=0 if row.fill_lag>=1-ep else (1 if row.demand_lag<1-ep else 2)
                context=tenor.copy()
                context['prevclass']=np.where(context.fill_lag>=1-ep,0,np.where(context.demand_lag<1-ep,1,2))
                pt.append(histogram(context.loc[context.prevclass==prevclass,'target']))
            probs['hist'].extend(ph); probs['tenor_recent'].extend(pr); probs['lag_transition'].extend(pt)
            probs['adaptive_blend'].extend((np.array(pr)+np.array(pt))/2)
            probs['logistic'].extend(model_prob(LogisticRegression(C=.35,max_iter=400),fit,group,all_feat,['tenor']))
            probs['hgb'].extend(model_prob(HistGradientBoostingClassifier(max_iter=65,max_leaf_nodes=5,min_samples_leaf=18,l2_regularization=4,random_state=0),fit,group,all_feat,['tenor']))
            probs['transfer'].extend(model_prob(LogisticRegression(C=.35,max_iter=400),other,group,base_feat,['tenor']))
            probs['pooled'].extend(model_prob(LogisticRegression(C=.35,max_iter=400),train,group,all_feat,['tenor','country']))
            probs['no_yield_calendar'].extend(model_prob(LogisticRegression(C=.35,max_iter=400),fit,group,base_feat,['tenor']))
            probs['history_only'].extend(model_prob(LogisticRegression(C=.35,max_iter=400),fit,group,[c for c in base_feat if c not in ['size_share','offer_change']],['tenor']))
            targets.append(group[['country','date','tenor','target']])
    if not targets:continue
    test=pd.concat(targets,ignore_index=True)
    for name,v in probs.items():
        pp=np.array(v)
        for i in range(3):
            test[name+str(i)]=pp[:,i]
    test.to_csv(root/('predictions_'+str(ep)+'.csv'),index=False)
    for country, block in test.groupby('country'):
        for which,w in [('all',block),('2025',block[block.date.dt.year==2025]),('2026',block[block.date.dt.year==2026]),('text_only_sensitivity',block.merge(raw[raw.method=='text'][['country','date','tenor']],on=['country','date','tenor']))]:
            if w.empty:continue
            y=w.target.to_numpy()
            print('HOLDOUT',country,which,'events',w.date.nunique(),'states',np.bincount(y,minlength=3))
            for name in probs:
                pp=w[[name+str(i) for i in range(3)]].to_numpy()
                brier=np.mean(np.sum((np.eye(3)[y]-pp)**2,axis=1))
                short_brier=np.mean(((y>0)-(1-pp[:,0]))**2)
                print(f' {name:>17} log={log_loss(y,pp,labels=[0,1,2]):.3f} multi_brier={brier:.3f} shortfall_brier={short_brier:.3f}')
