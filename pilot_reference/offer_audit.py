from pathlib import Path
import re,subprocess,json
from dateutil.parser import parse
import pandas as pd,numpy as np
from parse import get_nums, find_date, numeric_date, normalize
root=Path(__file__).resolve().parent
actual=pd.read_csv(root/'panel.csv').pivot_table(index=['country','date'],columns='tenor',values='offered')
def read(p):
 return normalize(subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,text=True).stdout)
def date_ug(s):
 try: return parse(re.sub(r'\b(?:Wednesday|Thursday|Tuesday|Monday|Friday|Saturday|Sunday)\b','',s,flags=re.I),fuzzy=True,dayfirst=True).date().isoformat()
 except (ValueError,OverflowError): return None
def test_offers(market,folder):
 matches=[]
 for p in sorted((root/folder).glob('*.pdf')):
  t=read(p)
  if market=='UG':
   l=re.search(r'^\s*AUCTION DATE\s*:\s*([^\r\n]+)',t,re.M|re.I)
   if not l:continue
   dt=date_ug(l.group(1))
   offer=[]
   for tenor in (91,182,364):
    m=re.search(rf'\b{tenor}\s*-?\s*DAYS?\s+(\d{{1,3}}(?:,\d{{3}}){{2,}})\s*(?:/=)?',t,re.I)
    if m:offer.append(float(m.group(1).replace(',',''))/1e9)
  else:
   nx=re.search(r'NEXT TREASURY BILLS? AUCTIONS?[^\r\n]*',t,re.I)
   if not nx:continue
   nt=t[nx.start():]
   dt=find_date(nx.group(0),numeric_date)
   offer=get_nums(nt,r'^Offer amount(?:\s*\([^)]*\))?\s+(.*)',4)
   if offer:offer=offer[:3]
  if dt and offer and len(offer)==3 and (market,dt) in actual.index:
   a=actual.loc[(market,dt)].to_numpy()
   matches.append((dt,all(np.abs(a-offer)<.02),a,offer))
 print(market,len(matches),'exact displayed values',sum(m[1] for m in matches))
 print('Mismatches',[(x[0],x[2],x[3]) for x in matches if not x[1]][:12])
test_offers('UG','UG_INV')
test_offers('KE','KE')
