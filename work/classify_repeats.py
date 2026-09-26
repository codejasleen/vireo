from investigate_repeats import *
from issue_rules import label,repeat_marker,complaint_text

raw,t,e=load()
t['customer_labels']=t.customer_message.map(label)
t['note_labels']=t.agent_notes.map(lambda s:label(s,False))
t['repeat_marker']=t.customer_message.map(repeat_marker)
orders=pd.read_csv(PATHS['orders'],keep_default_na=False)
orders['order_date']=pd.to_datetime(orders.order_date)
orders_by_key={k:g for k,g in orders.groupby(['customer_id','sku'])}
orders_by_id=orders.set_index('order_id')

def order_evidence(r):
 # Use quoted message IDs only if valid and compatible; never use nearest order.
 quoted=set(re.findall(r'\bVR\d+\b',r.customer_message.upper()))
 explicit=({r.order_id} if r.order_id else set())|quoted
 if len(explicit)>1:return ('conflict','')
 if explicit:
  oid=next(iter(explicit))
  if oid not in orders_by_id.index:return ('invalid','')
  o=orders_by_id.loc[oid]
  if o.customer_id!=r.customer_id or o.sku!=r.product_sku or o.order_date>r.created_at:return ('invalid','')
  return ('explicit',oid)
 g=orders_by_key.get((r.customer_id,r.product_sku))
 if g is None:return ('missing','')
 g=g[g.order_date<=r.created_at]
 return ('inferred_unique',g.iloc[0].order_id) if len(g)==1 else ('ambiguous','')

t['order_evidence']=t.apply(order_evidence,axis=1)
d=t.set_index('ticket_id').to_dict('index')

def compare(a,b):
 x,y=d[a],d[b];lx,ly=x['customer_labels'],y['customer_labels']
 ox,oy=x['order_evidence'],y['order_evidence']
 if len(lx)!=1 or len(ly)!=1:return ('uncertain_text','')
 if lx!=ly:
  # Follow-on logistics/refund stages and related hardware symptoms may be one episode.
  families=[{'delivery_missing','transit_damage','wrong_item','return_pickup','refund_pending','cancel_order','address_change'}, {'payment_no_order','duplicate_payment','refund_pending','coupon_discount'}, {'left_bud_charging','case_charging','battery_drain','one_side_audio'}, {'pairing','bluetooth_dropout','firmware_update','app_crash'}]
  if any(lx[0] in f and ly[0] in f for f in families):return ('uncertain_issue_progression','')
  return ('different_issue','')
 issue=lx[0]
 if issue=='one_side_audio':
  def side(s):
   hits=re.findall(r'(?:no (?:sound|audio) from the (right|left)|\b(right|left) (?:earbud|side)[^.\n]{0,30}(?:silent|no audio|no sound))',s.lower())
   return {a or b for a,b in hits}
  sx,sy=side(x['customer_message']),side(y['customer_message'])
  if sx and sy and sx.isdisjoint(sy):return ('uncertain_symptom_change',issue)
 if ox[0] in ['conflict','invalid'] or oy[0] in ['conflict','invalid']:return ('uncertain_order',issue)
 if ox[1] and oy[1] and ox[1]!=oy[1]:return ('different_order',issue)
 # A positive contradictory issue in a closing note makes the link reviewable, not confirmed.
 # Notes can also name remedial steps; do not require a generic note to provide a label.
 nx,ny=x['note_labels'],y['note_labels']
 if (nx and issue not in nx) or (ny and issue not in ny):return ('uncertain_note',issue)
 if ox[1] and ox[1]==oy[1]:
  return ('same_explicit_order' if ox[0]==oy[0]=='explicit' else 'same_inferred_order',issue)
 if y['repeat_marker']:return ('same_explicit_recontact',issue)
 return ('uncertain_same_symptom',issue)

e[['classification','issue']]=pd.DataFrame([compare(r.prior_id,r.return_id) for r in e.itertuples()],index=e.index)
rank={'same_explicit_order':0,'same_inferred_order':1,'same_explicit_recontact':2,'uncertain_note':3,'uncertain_order':4,'uncertain_same_symptom':5,'uncertain_symptom_change':6,'uncertain_issue_progression':7,'uncertain_text':8,'different_order':9,'different_issue':10}
e['rank']=e.classification.map(rank)
selected=e.sort_values(['rank','gap_days','prior_id']).drop_duplicates('return_id').copy()
for c in ['product_sku','channel','created_at','status','order_evidence','customer_labels','note_labels']:
 selected[c]=selected.return_id.map(lambda k:d[k][c])
selected['cost_inr']=selected.channel.map(COST)
selected['prior_status']=selected.prior_id.map(lambda k:d[k]['status'])
selected['confirmed']=selected['classification'].str.startswith('same_')
print('TICKET LABEL COVERAGE',t.customer_labels.map(len).value_counts().to_dict())
print('ORDER EVIDENCE',t.order_evidence.map(lambda x:x[0]).value_counts().to_dict())
print('EDGE CLASSES',e.classification.value_counts().to_dict())
print('RETURN CLASSES',selected.classification.value_counts().to_dict())
confirmed=selected[selected.confirmed]
print('CONFIRMED',len(confirmed),'COST',confirmed.cost_inr.sum())
print('ISSUES',confirmed.groupby('issue').agg(n=('return_id','size'),cost=('cost_inr','sum')).sort_values('cost',ascending=False).to_dict('index'))
print('TOP COMBOS',confirmed.groupby(['product_sku','issue','channel']).agg(n=('return_id','size'),cost=('cost_inr','sum')).sort_values('cost',ascending=False).head(20).to_string())
e.to_csv(WORK/'classified_edges.csv',index=False)
selected.to_csv(WORK/'classified_returns.csv',index=False)
t.to_json(WORK/'labeled_tickets.jsonl',orient='records',lines=True,date_format='iso',force_ascii=False)
