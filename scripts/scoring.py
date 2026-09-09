"""Pure, reproducible scoring functions; no demographic attributes are used."""
import math

WEIGHTS = dict(income=.25, poverty=.25, vacancy=.20, value=.15, affordability=.15)
REVERSED = {'poverty', 'vacancy', 'affordability'}

def clean(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):
        return None

def ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator<=0 or numerator>denominator:
        return None
    return 100*numerator/denominator

def percentile(values,p):
    ordered=sorted(values)
    k=(len(ordered)-1)*p
    a,b=math.floor(k),math.ceil(k)
    return ordered[a]+(ordered[b]-ordered[a])*(k-a)

def normalize(x, anchors, reverse=False):
    if x is None: return None
    lo,mid,hi=anchors
    x=max(lo,min(hi,x))
    if x==mid: score=50
    elif x<mid: score=50*(x-lo)/(mid-lo) if mid>lo else 50
    else: score=50+50*(x-mid)/(hi-mid) if hi>mid else 50
    return 100-score if reverse else score

def calculate(rows):
    anchors={k:[percentile([r['raw_'+k] for r in rows if r['raw_'+k] is not None],p) for p in [.05,.5,.95]] for k in WEIGHTS}
    for r in rows:
        full={k:normalize(r['raw_'+k],anchors[k],k in REVERSED) for k in WEIGHTS}
        available=sum(WEIGHTS[k] for k,v in full.items() if v is not None)
        r['coverage']=round(available*100)
        r['overall']=math.floor(sum(WEIGHTS[k]*v for k,v in full.items() if v is not None)/available+.5) if available>=.74999 and full['income'] is not None and full['poverty'] is not None else None
        for k,v in full.items():r[k]=math.floor(v+.5) if v is not None else None
    return anchors
