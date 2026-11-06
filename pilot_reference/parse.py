import re, json, subprocess, zipfile, tempfile, os
from pathlib import Path
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as X
from dateutil.parser import parse
import pandas as pd

root=Path(__file__).resolve().parent
num=r'(?<![\w/.-])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w/.-])'
date_pattern=r'\b\d{1,2}\s*[-/ .]\s*(?:[A-Z]{3,9}|\d{1,2})\s*[-/ .]\s*(?:20\d\d|1[7-9]|2[0-6])\b'
numeric_date=r'\b\d{1,2}[-/.]\d{1,2}[-/.]20\d\d\b'
def numbers(s):
    return [float(x.replace(',','')) for x in re.findall(num,s)]
def get_lines(t, pattern):
    return [m.group(1) for l in t.splitlines() if (m:=re.match(pattern,l.strip(),re.I))]
def get_nums(t,pattern,size=3):
    for s in get_lines(t,pattern):
        vals=numbers(s)
        if len(vals)>=size:
            return vals[:size]
    return None
def as_date(m):
    if not m:
        return None
    try: return parse(m.group(0), dayfirst=True).date().isoformat()
    except (ValueError,OverflowError): return None
def find_date(t,pat):
    return as_date(re.search(pat,t,re.I))
def normalize(t):
    t=t.replace('\u00a0',' ').replace('\u2013','-').replace('\u2014','-').replace('_',' ')
    t=re.sub(r'(?<=\d),[ \t]+(?=\d{3}\b)',',',t)
    return re.sub(r'(?m)^(ACCEPTED BIDS[ \t]+)[ \t\x27-]+(?=\d)',r'\1',t)
def parse_ke(p,t,url):
    O=get_nums(t,r'^Amount Offered(?:\s*\([^)]*\))?\s+(.*)',4)
    B=get_nums(t,r'^(?:Bids Received|Amount (?:Applied|Tendered))(?:\s*\([^)]*\))?\s+(.*)',4)
    A=get_nums(t,r'^(?:Total )?Amount Accepted(?:\s*\([^)]*\))?\s+(.*)',4)
    R=get_nums(t,r'^Rollover\s*/\s*Redemptions\s+(.*)',4)
    issued=find_date(t.split('The auction outcome')[0][:700],numeric_date) or find_date(url,numeric_date)
    closes=find_date(' '.join(get_lines(t,r'^Auction Dates? & Bids Closure\s+(.*)')),numeric_date)
    nextR=get_nums(t,r'^Redemptions\s+(.*)',1)
    y=[]
    for tenor in (91,182,364):
        v=get_nums(t,rf'^{tenor}\s*-?\s*days?\s+(.*)',3)
        y.append(v[0] if v else None)
    if issued and O and B and A and all(abs(sum(v[:3])-v[3])<=.07 for v in [O,B,A]):
        return issued, O[:3],B[:3],A[:3],y, R, nextR, closes
    return None
def parse_ug(p,t,url):
    O=get_nums(t,r'^(?:AMOUNT\s+)?OFFERED(?:\s*\([^)]*\))?\s*[:=]?\s+(.*)')
    B=get_nums(t,r'^(?:AMOUNT\s+)?(?:TENDERED|BIDS RECEIVED)(?:\s*\([^)]*\))?\s*[:=]?\s+(.*)')
    A=get_nums(t,r'^(?:TOTAL\s+)?(?:AMOUNT\s+)?ACCEPTED(?:\s+BIDS)?(?:\s*\([^)]*\))?\s*[:=]?\s+(.*)')
    ys=get_nums(t,r'^EFFECTIVE\s+YIELD(?:\s*\([^)]*\)|\s+AT\s+(?:WAP|COP))?\s*[:=]?\s+(.*)') or [None]*3
    line=' '.join(l for l in t.splitlines() if re.search(r'(?:\bAUCTION\s+DATE\b|HELD\s+ON\b)',l,re.I))
    issued=find_date(line,date_pattern) 
    if issued and O and B and A and min(O)>=1e9 and max(O)<1e13 and max(B)<1e13 and max(A)<1e13:
        return issued, O,B,A,ys,None,None,None
    return None
def extract(p):
    if p.suffix=='.pdf':
        return subprocess.run(['pdftotext','-layout',str(p),'-'],capture_output=True,text=True,errors='replace',timeout=12).stdout
    if p.suffix=='.docx':
        with zipfile.ZipFile(p) as z:
            r=X.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        return '\n'.join(' '.join(e.text for e in a.findall('.//w:t',ns) if e.text) for a in r.findall('.//w:tr',ns))
    if p.suffix=='.xlsx':
        import openpyxl
        wb=openpyxl.load_workbook(p,data_only=True)
        return '\n'.join(' '.join(str(x) for x in row if x is not None) for sh in wb for row in sh.values)
    return ''
def get(job):
    country,p,url=job
    try:
        t=normalize(extract(p))
        method='text'
        parser=parse_ke if country=='KE' else parse_ug
        got=parser(p,t,url)
        if got is None and country=='UG' and p.suffix=='.pdf':
            cache=p.with_suffix('.ocr.txt')
            if not cache.exists():
                with tempfile.TemporaryDirectory() as tmp:
                    dest=Path(tmp)/'img'
                    subprocess.run(['pdftoppm','-f','1','-l','1','-r','180','-png',str(p),str(dest)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
                    s=subprocess.run(['tesseract',str(next(Path(tmp).glob('img-*.png'))),'stdout','--psm','6'],capture_output=True,text=True,errors='replace',timeout=18)
                    cache.write_text(s.stdout)
            got=parser(p,normalize(cache.read_text()),url)
            method='ocr'
        if not got:
            return p,None
        issued,O,B,A,y,R,nextR,closes=got
        if any(a>b+0.02 for a,b in zip(A,B)) or any(o<=0 for o in O):
            return p,None
        if country=='UG':
            O=[v/1e9 for v in O]; B=[v/1e9 for v in B]; A=[v/1e9 for v in A]
        rows=[]
        for i,tenor in enumerate((91,182,364)):
            rows.append(dict(country=country,date=issued,tenor=tenor,offered=O[i],bids=B[i],accepted=A[i],yield_pct=y[i],method=method,source=url,reported_redemptions=R[3] if R else None,next_redemptions=nextR[0] if nextR else None,next_close=closes))
        return p,rows
    except Exception as e:
        print('error',str(p),str(e)[:100])
        return p,None
if __name__=='__main__':
    jobs=[]
    for section in ('KE','UG','UG_API'):
        d=root/section
        if not (d/'manifest.json').exists():continue
        manifest=json.loads((d/'manifest.json').read_text())
        jobs += [(section[:2],p,manifest[int(p.stem)]) for p in sorted(d.iterdir()) if p.suffix in {'.pdf','.docx','.xlsx'} and p.stem.isdecimal()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(get,jobs))
    df=pd.DataFrame([r for p,rs in results if rs for r in rs])
    err=[str(p) for p,rs in results if not rs]
    (root/'parse_errors.txt').write_text('\n'.join(err))
    dups=df[df.duplicated(['country','date','tenor'],keep=False)]
    if len(dups):
        print('duplicate row count',len(dups),dups.groupby(['country','date','tenor'])[['offered','bids','accepted']].nunique().gt(1).sum().to_dict())
    df=df.drop_duplicates(['country','date','tenor'])
    df.sort_values(['country','date','tenor']).to_csv(root/'panel.csv',index=False)
    print(df.assign(year=df.date.str[:4]).groupby(['country','year','method']).date.nunique())
    print('parse failures',len(err),'of',len(results))
