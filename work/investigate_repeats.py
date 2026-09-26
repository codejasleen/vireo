from pathlib import Path
import pandas as pd
import json, re, hashlib
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'work'
OUT=ROOT/'outputs'
PATHS={
 'tickets':r'C:\Users\Jasleen\Downloads\cded5ec7-cd54-40e6-ba66-7b3e581319c7-tickets.csv',
 'orders':r'C:\Users\Jasleen\Downloads\e5c326e5-4764-4ab0-87fd-75abb8f287ae-orders.csv',
 'products':r'C:\Users\Jasleen\Downloads\8e1b3214-16f2-4456-a618-cd1a4e8bddef-products.csv',
}
COST={'chat':210,'email':260,'voice':520,'social':240}

def load():
 raw=pd.read_csv(PATHS['tickets'],keep_default_na=False)
 # Every duplicated ID was checked against its customer/product/message/creation fingerprint.
 for _,g in raw[raw.ticket_id.duplicated(False)].groupby('ticket_id'):
  assert all(g[c].nunique()==1 for c in ['customer_id','product_sku','created_at','customer_message'])
 t=raw.sort_values('source_system').drop_duplicates('ticket_id').copy()
 for c in ['created_at','first_response_at','resolved_at']:
  t[c]=pd.to_datetime(t[c],errors='coerce')
 t.loc[t.source_system.eq('legacy_fd'),'resolved_at']+=pd.Timedelta(hours=5,minutes=30)
 assert not (t.resolved_at<t.first_response_at).any()
 t=t.sort_values(['created_at','ticket_id'])
 edges=[]
 for _,g in t.groupby(['customer_id','product_sku']):
  previous=[]
  for r in g.to_dict('records'):
   for p in previous:
    if pd.notna(p['resolved_at']) and p['resolved_at']<=r['created_at']<=p['resolved_at']+pd.Timedelta(days=30):
     edges.append({'prior_id':p['ticket_id'],'return_id':r['ticket_id'],'gap_days':(r['created_at']-p['resolved_at']).total_seconds()/86400})
   previous.append(r)
 return raw,t,pd.DataFrame(edges)

if __name__=='__main__':
 raw,t,e=load()
 ids=set(e.prior_id)|set(e.return_id)
 related=t[t.ticket_id.isin(ids)]
 print('raw',len(raw),'unique',len(t),'candidate returns',e.return_id.nunique(),'edges',len(e),'related tickets',len(related))
 print('prior status',t.set_index('ticket_id').loc[e.prior_id].status.value_counts().to_dict())
 print('top notes',related.agent_notes.value_counts().head(40).to_dict())
 # Frequent words/phrases reveal the issue vocabulary without trusting intake categories.
 for n in [2,3,4]:
  cnt=Counter()
  for s in related.customer_message:
   w=re.findall(r'[a-z]+',s.lower());cnt.update(set(' '.join(w[i:i+n]) for i in range(len(w)-n+1)))
  print('NGRAM',n,cnt.most_common(100))
 e.to_csv(WORK/'candidate_edges.csv',index=False)
 related.to_json(WORK/'related_tickets.jsonl',orient='records',lines=True,date_format='iso',force_ascii=False)
