"""Conservative, inspectable text labels for this exploratory audit. No external model calls."""
import re

# These rules describe the complaint, not a demanded refund/replacement or a closure claim.
PATTERNS={
'coupon_discount': r'coupon|promo code|discount (?:was |is |not |has |code)|discount.*(?:appl|checkout|invoice)|promised a discount|festive offer|offer vanished',
'payment_no_order': r'(?:amount|money|payment).*(?:deducted|debited).*(?:no order|without.*ord|order.*(?:fail|not|creat))|(?:bank|card).*says.*(?:no orders|no order)|charged.*(?:no order|order.*(?:fail|not))|payment went through.*(?:no order|order)|paid.*(?:no order|order.*(?:not|missing))|failed order after payment|payment debited, no ord|amount deducted without ord',
'duplicate_payment': r'(?:charged|charge|payment|deducted|debited).*(?:twice|two times)|double (?:payment|charge)|duplicate (?:payment|charge)|two.*(?:charges|debits)|paid twice',
'invoice': r'invoice.*(?:download|gst|share|need|missing)|(?:share|need|send|download|want|request).*invoice|tax bill|gstin|gst (?:invoice|number)|invoice query|invoice not downloading',
'refund_pending': r'refund.*(?:pending|delay|not (?:credit|receiv|come|reflect)|promised|where|status|nothing)|(?:waiting|wait|where|haven.t|not got|not received).*refund|money.*(?:hasn.t|has not|not).*(?:back|come|credit)|refund.*ago|picked up.*money|rfnd (?:not credited|delay|pending)',
'return_pickup': r'(?:pickup|pick.up|collection).*(?:not|miss|pending|delay|happen|done|schedul)|(?:no one|nobody|waiting|wait).*pick|packed the box|reverse (?:pickup|pkp) pending|pkp (?:not done|missed)|courier.*(?:collect|pick up)',
'delivery_missing': r'(?:order|package|parcel|shipment).*(?:not (?:deliver|receiv)|hasn.t (?:arriv|come)|haven.t receiv|delayed|delay|missing)|(?:haven.t|not|never).*received my order|delivery.*delay|tracking.*(?:updat|stuck|mov)|(?:marked|shows|says).*deliver.*(?:nobody|not|never|nothing|but)|courier marked it delivered|(?:order status|status).*stuck on shipped|(?:shipment|ord) not (?:rcvd|delivered)|dlvry delayed|delivery delayed',
'transit_damage': r'(?:box|parcel).*(?:crush|damage|kick)|(?:arrived|received|delivered|transit).*(?:damag|crack|broken)|damaged in transit|transit damage|unit (?:received|rcvd) damaged|(?:unit|product).*(?:crack).*',
'wrong_item': r'wrong (?:product|item|variant|colou?r|model)|incorrect product|ordered black.*(?:white|got)|(?:sent|received|got).*instead|not what i (?:asked|ordered)|different (?:product|colou?r|model)',
'cancel_order': r'cancel.*(?:order|button)|order cancellation|cancellation request|cancel ord',
'address_change': r'(?:address|pincode|pin code).*(?:change|wrong|update|incorrect)|(?:change|update|wrong|incorrect).*(?:address|pincode|pin code)',
'left_bud_charging': r'left.*(?:not charg|no charg|won.t charg|doesn.t charg|taking charge|0 percent|0%)|(?:l|left) bud.*(?:paperweight|charge)|(?:app shows|shows).*left.*(?:0|zero)|left earbud not taking charge',
'case_charging': r'case.*(?:not charg|no charg|won.?t charg|wont charge|doesn.t charg|no light|dead|no led)|no light.*(?:case|plug)|charging case dead',
'battery_drain': r'battery.*(?:drain|backup|last|poor|flat|die)|(?:dies|dead|lasts|drains).*(?:hour|minute)|rapid battery drain|poor battery backup|charge.*(?:lasts|last).*hour',
'pairing': r'pair(?:ing)?.*(?:fail|not|unable)|(?:cannot|can.t|unable to|won.t).*pair|(?:not|never).*discover|pairing light|not (?:show|appear).*bluetooth|bluetooth.*(?:not show|not find)|device not discoverable|unable to pair',
'bluetooth_dropout': r'disconnect|dropout|connection dropping|bluetooth.*(?:drop|cut)|sound stutters.*pocket|keeps dropping|connection.*(?:drop|cut)',
'one_side_audio': r'no (?:sound|audio).*side|no (?:sound|audio).*earbud|(?:left|right|one).*side.*(?:silent|sound|audio)|(?:left|right).*earbud.*silent|only one side|single side audio|one (?:bud|earbud).*(?:silent|sound)|(?:left|right) side silent',
'audio_distortion': r'crackl|distort|buzzing|static (?:noise|sound)|sound.*(?:fuzzy|muffled)|audio distortion',
'microphone': r'\bmic\b|microphone|(?:people|other person|caller).*(?:hear me|hear my)|voice.*(?:faint|quiet)',
'firmware_update': r'(?:firmware|fw|update).*(?:stuck|hang|fail|67%|bricked)|update.*(?:hours|hour)|firmware update failed',
'app_crash': r'app.*(?:crash|not open|won.t open|white screen|blank screen|closes|shuts)|(?:white|blank) screen.*app|app.*device settings|app crash on device page',
'login_otp': r'\botp\b|log.?in|log in|login issue',
'repair_status': r'(?:repair|warranty claim|wty claim|rma).*(?:status|update|follow)|status.*(?:repair|warranty)|sent.*unit.*(?:heard nothing|no update)|repair status follow.up',
'watch_strap': r'\bstrap\b|metal pin.*wrist|pin fell out|strap pin issue',
'watch_touch': r'touch.*(?:not|unresponsive|issue)|(?:screen|display).*(?:not respond|unresponsive)|unresponsive display',
'speaker_power': r'speaker.*(?:not power|won.t turn|not turn|dead)|no power|unit dead',
'wifi_setup': r'wi.?fi.*(?:setup|connect|fail)|(?:unable|cannot|can.t).*wi.?fi|network setup issue',
'enquiry_water': r'survive a shower|waterproof|water resistant|swim|water resistance',
'enquiry_compatibility': r'compatible.*(?:tv|phone)|old nokia|will.*app run|compatibility query',
'enquiry_multi_device': r'connect two|two.*together|multipoint|two devices',
}

def normalize(s):
 s=s.lower().replace('’',"'").replace('–','-')
 # Only a small, auditable spelling/abbreviation map; no fuzzy inference.
 fixes={'teh':'the','ord':'order','odrer':'order','oredr':'order','oder':'order','ordre':'order','recieved':'received','recieve':'receive','receved':'received','receiived':'received','rfnd':'refund','refnd':'refund','rfund':'refund','refnud':'refund','refuund':'refund','pkp':'pickup','rcvd':'received','wty':'warranty','fw':'firmware','bt':'bluetooth','dlvry':'delivery','deliivery':'delivery','deliveered':'delivered','bene':'been','stlil':'still','stll':'still','wont':"won't",'hasnt':"hasn't",'cant':"can't",'dont':"don't",'earubd':'earbud','chargin':'charging','pairig':'pairing','conncts':'connects','crasihng':'crashing','amouunt':'amount','ammount':'amount','invioce':'invoice','upddate':'update'}
 for a,b in fixes.items():s=re.sub(r'\b'+re.escape(a)+r'\b',b,s)
 return s

EXTRA={
'coupon_discount':r'ad said.*cart says full price|discount.*none|discount.*appl|coupon code|offer.*vanish',
'payment_no_order':r'(?:page|pge).*(?:failed|fail).*(?:paid|pay)|bank says.*no orders|paid via upi.*(?:no order|no ordre)|money debited.*order not showing',
'duplicate_payment':r'same amount twice|two entries.*statement|two entries.*for one|paid twice',
'invoice':r'company accounts team.*tax bill|bill.*gstin',
'refund_pending':r'where is the money for the return|return was accepted.*amount.*nowhere|still waiting.*ref(?:u?n?d|nud)|money hasn.t come back|money has not come back|refund.*(?:not arrived|not come|not received)',
'return_pickup':r'sitting at home.*waiting for.*courier|app said pickup today|nobody came.*collect|no one.*collect|return pickup has not happened|packed the box.*still here',
'delivery_missing':r'order has not been deliver|order.*not.*deliver|tracking has said out for delivery|paid on.*waiting for.*show up|(?:days|weeks).*nothing in hand|haven.t received my order|courier marked it delivered.*nobody',
'transit_damage':r'dent.*straight out of the box|screen has a crack before|parcel.*kicked|box was crushed|arrived.*broken',
'wrong_item':r'box says.*inside.*not what i paid|ordered black.*got white',
'cancel_order':r'son ordered this without asking|changed my mind.*ship|cancel button|don.t want.*order',
'address_change':r'typo in the flat number|wrong pincode|wrong address',
'left_bud_charging':r'left.*never gets the green light|left.*0 percent|l bud is basically a paperweight',
'case_charging':r'case.*no light|case.*won.t charge|case.*wont charge',
'battery_drain':r'battery life has dropped|full to empty during one commute|bat(?:t)?ery drain',
'pairing':r'connects for a second.*vanishes.*device list|phone just doesn.t see it in the list|not pairing|canont pair|cannot pair|pairing.*fail',
'bluetooth_dropout':r'goes silent for a second every few minutes|blue.?ooth keeps cutting out|sound stutters.*pocket',
'one_side_audio':r'music in one ear only|no sound from the (?:right|left)|(?:right|left) earbud completely silent',
'audio_distortion':r'\bhiss\b|badly tuned radio|buzzing sound|crackling',
'firmware_update':r'update prompt.*went dark|spinning circle for hours',
'app_crash':r'loading screen in the app|app.*white screen|app not opening after update',
'login_otp':r'site keeps saying it sent me a code|cannot logn|cannot login|not receiving otp',
'repair_status':r'service centre took it.*silence|claim number rma|sent the unit.*heard nothing|no update on my repair|status of my warranty claim',
'watch_touch':r'display just ignores my finger|touch.*not respond',
'wifi_setup':r'finds the speaker.*network step',
'enquiry_compatibility':r'work (?:with|w/) iphone|will this talk to.*samsung|old nokia.*watch app',
}

MORE={
'payment_no_order':r'upi shows success.*app shows nothing|page failed.*nothing shows|payment.*through.*no order id|money debi.*order not showing',
'duplicate_payment':r'paid once.*statement disagrees',
'refund_pending':r'return was accepted.*nowhere in my account|where.*money.*return|refund not received',
'delivery_missing':r'tracking.*out for delivery.*week|order status.*shipped|paid on.*(?:waiting|watiing).*show up|order has not.*deliver',
'wrong_item':r'ordered.*got something else|opened the parcel.*different thing|box says.*inside.*paid for|received the wong item|wrog product delivered',
'cancel_order':r'change of mind.*stop the shipment|cncel.*order',
'address_change':r'moved houses yesterday.*old flat|change delivery address',
'left_bud_charging':r'left.*stopped charging|left.*never gets.*light.*case|left bud won.t chareg',
'case_charging':r'plugging in does nothing on the case|case has been at the same battery level',
'battery_drain':r'dies by lunchtime|promised.*hours is nowhere close',
'bluetooth_dropout':r'keeps losing my phone.*other room',
'one_side_audio':r'everything sounds.*one direction|no soud from the (?:right|left) earbud',
'audio_distortion':r'frying sound.*background',
'microphone':r'works for (?:music|msic) but useless for meetings',
'firmware_update':r'progress bar.*since morning|update fail.*won.t turn on',
'app_crash':r'app (?:closes|coses) itself.*device',
'login_otp':r'locked out of my own account',
'repair_status':r'warranty claim pending',
'watch_strap':r'band snapped.*putting it on',
'watch_touch':r'tap ten times.*swipe|display.*finger half the time',
}
for k,v in MORE.items():EXTRA[k]=EXTRA.get(k,r'(?!)')+'|'+v
# A generic demand for a refund and troubleshooting attempts are not separate issues.
PATTERNS['refund_pending']=PATTERNS['refund_pending'].replace('|nothing','')
PATTERNS['login_otp']=r'\botp\b|cannot log.?in|can.t log.?in|unable to log in|login issue|not able to log in'
PATTERNS['duplicate_payment']=r'\b(?:charged|payment|deducted|debited)\b.*(?:twice|two times)|double (?:payment|charge)|duplicate (?:payment|charge)|two.*(?:charges|debits)|paid twice'
PATTERNS['invoice']=r'invoice.*(?:download|gst)|(?:share|need|send|download|want|request).*invoice|tax bill|gstin|gst (?:invoice|number)|invoice query|invoice not downloading'

def complaint_text(s):
 s=normalize(s)
 m=re.search(r'(?:^|\n)issue:\s*(.*?)(?=\n(?:tried|expected):|$)',s,re.S)
 if m:return m.group(1).strip()
 s=re.split(r'i request you',s)[0]
 # Exclude prior troubleshooting and generic demands, which are not the complaint.
 s=re.sub(r'\bi (?:already |have )?(?:tried|checked|emailed|called|waited|fully charged|reset|reinstalled|updated|cleared|turned off|charged|forgot|restarted)[^.\n!?]*',' ',s)
 s=re.sub(r'i want a replacement or refund,? nothing else|refund\. now\.?',' ',s)
 return s

def label(s, customer=True):
 s=complaint_text(s) if customer else normalize(s)
 found=[]
 for k,v in PATTERNS.items():
  v='(?:'+v+')|(?:'+EXTRA.get(k,r'(?!)')+')'
  # Match within a clause, not across the whole message.
  v=v.replace('.*',r'[^.\n!?]{0,100}')
  if re.search(v,s):found.append(k)
 if customer and re.search(r'charge it twice a day',s):
  found=[k for k in found if k!='duplicate_payment']
  found.append('battery_drain')
 if customer and re.search(r'(?:ordered|orered) the wrong colou?r.*(?:don.t ship|ship it)',s):
  found=[k for k in found if k!='wrong_item']
  found.append('cancel_order')
 # Bare update/app references must not convert an app-crash complaint to firmware failure.
 if 'app_crash' in found and 'firmware_update' in found and not re.search(r'\bfirmware\b|\bupdate\b[^.\n]{0,35}(?:stuck|hang|failed|67%)',s):found.remove('firmware_update')
 return sorted(set(found))

def repeat_marker(s):
 return bool(re.search(r'(?:same (?:issue|problem|fault|complaint)|second time|third (?:time|ticket)|earlier ticket|previous ticket|last ticket|told.*(?:fixed|resolved)|writing again|contacted.*(?:before|earlier)|raised this last|issue is back|recontact|repeat contact|second contact|following up on my earlier complaint|fourth time writing|still not fixed after|again the same thing|supposedly sorted.*last time)',normalize(s)))

def spans(s,issue):
 m=re.search(PATTERNS[issue],normalize(s));return m.group(0) if m else ''
