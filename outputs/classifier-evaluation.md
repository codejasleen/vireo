# Evaluation of `offline-rules-v1` against the repeat-contact investigation

## Conclusion

`offline-rules-v1` is not suitable as the final production classifier. It retains the conservative deterministic gate and has high agreement precision, but it recovers only 525 of the 1,039 reviewed high-confidence return contacts. Its 50.53% recall cuts the measured overall and missing-delivery repeat rates roughly in half. The provider is a deterministic regex development stand-in whose fixed 0.90 confidence is not calibrated.

## Comparison method

- Unit for the headline comparison: one candidate return contact. Production contains 561 positive pairs but only 536 distinct return tickets because some returns link to more than one earlier ticket.
- Reviewed positive reference: the 654 `same_explicit_order` plus 385 `same_inferred_order` rows in `work/classified_returns.csv`, totaling 1,039 distinct returns. The 29 `same_explicit_recontact` rows are excluded, as required by the investigation memo.
- A production return is positive if any pair for it has `decision=high_confidence_repeat`. Exact-link agreement separately requires the same first-ticket/return-ticket pair.
- No classifier output was regenerated. This report reads the preserved production and investigation artifacts only.

## Set overlap and classification metrics

| Measure | Count | Formula / interpretation |
|---|---:|---|
| Reviewed positive returns | 1,039 | Reference set |
| Production positive pairs | 561 | Pair-level output |
| Production positive returns | 536 | Distinct return tickets |
| Overlap / true positives | 525 | Production-positive return in the reviewed set |
| False negatives | 514 | `1,039 - 525` |
| Apparent false positives | 11 | `536 - 525` |
| Exact ticket-pair overlap | 510 | Same prior and return link |
| True positives with a different prior link | 15 | Return matches, selected link differs |

At the return-contact level:

- **Recall:** `525 / 1,039 = 50.53%`.
- **Conservative agreement precision:** `525 / 536 = 97.95%`, treating every contact outside the 1,039 set as a false positive.
- **Conservative F1:** `2 × 97.95% × 50.53% / (97.95% + 50.53%) = 66.67%`.
- **Adjudicated-only precision:** `525 / (525 + 4) = 99.24%`. This excludes seven production positives whose reference disposition is uncertain rather than negative.
- **Adjudicated-only F1:** using 99.24% precision and 50.53% recall gives **66.96%**.

The 97.95% figure is positive-set agreement, not proven real-world precision. Of the 11 apparent false positives, only four are reference `different_issue` cases; six are `uncertain_text` and one is `uncertain_symptom_change`. The investigation manually reviewed a precision-oriented sample of positive tiers, not every non-positive contact. Exact-pair precision is `510 / 561 = 90.91%`, exact-pair recall is `510 / 1,039 = 49.09%`, and exact-pair F1 is 63.75%; this stricter view also penalizes valid returns linked to a different earlier ticket in a chain.

## Why the classifier disagrees

### False negatives

- **494 of 514 (96.11%)** become `uncertain`. The offline provider marks a pair uncertain whenever either message is `other`: 133 misses have `other` on both tickets and 361 have it on one ticket. Common misses are indirect wording, typos, and phrases outside narrow regex forms, such as “nothing in hand,” “pairing is not working,” “bank says I have no orders,” and “where is the money for the return.”
- **20 of 514 (3.89%)** are called `different_issue` because the two messages receive different categories. Eleven are the battery/duplicate-payment collision caused by “charged/discharged twice”; five split missing delivery from return pickup; three split invoice from wrong-item wording; and one splits one-sided audio from Bluetooth dropouts.
- None of the 514 misses is caused by the deterministic order gate. The reviewed positives already satisfy the explicit or uniquely inferred same-order rule.

### Apparent false positives

- Four are clear disagreements with reference `different_issue` labels. Three are battery complaints misread as duplicate payment, and one is a wrong-colour complaint misread as an invoice request because it says the customer checked the invoice.
- Seven fall in reference uncertainty buckets. Several look plausibly like real repeats on inspection, so the existing reference does not support treating all seven as errors. One changed-side audio case should remain uncertain because right-earbud failure becomes left-side failure.
- The provider assigns the same 0.90 confidence to every regex match, including obvious category collisions. Confidence therefore does not measure reliability.

## Rate comparison

| Rate | Established baseline | Production result | Difference |
|---|---:|---:|---:|
| Overall mature cohort | `1,008 / 10,485 = 9.61%` | `519 / 10,485 = 4.95%` | -4.66 percentage points |
| Missing delivery, fixed established cohort | `186 / 1,297 = 14.34%` | `93 / 1,297 = 7.17%` | -7.17 percentage points |
| Missing delivery, classifier-defined cohort | Not comparable | `94 / 958 = 9.81%` | Classifier denominator is 339 tickets smaller |

The lower production rates are measurement undercount, not an operational improvement. The overall classifier identifies 519 mature origin tickets with a high-confidence return, versus the established 1,008. On the fixed 1,297-ticket missing-delivery cohort it identifies exactly half of the established numerator: 93 versus 186. If allowed to define its own missing-delivery denominator, it labels only 958 mature tickets, 26.14% fewer than the established 1,297; that 9.81% rate therefore is not comparable to 14.34%.

## Twenty representative disagreements

The first ten are reviewed positives missed by production. The next ten are production positives outside the reviewed positive set.

### 1. False negative: `TK-240394` → `TK-240531`

- **Reference:** `same_explicit_order` / `delivery_missing`.
- **Production ticket classifications:** first `other` (0.35); return `other` (0.35).
- **Production pair:** `uncertain`; category `other`; confidence 0.35; uncertain `True`.
- **First ticket:** > hii it has been 12 days and i have nothing in hand
- **Return ticket:** > This is teh second time I am writing about this., it has beeen 7 days and I have nothing in hand, VR881853
- **Evidence from first:** “hii it has been 12 days and i have nothing in hand”
- **Evidence from return:** “this is teh second time i am writing about this., it has beeen 7 days and i have nothing in hand, [order_id]”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** Both messages use the indirect delivery phrase “nothing in hand,” which the offline patterns do not recognize.

### 2. False negative: `TK-240777` → `TK-240978`

- **Reference:** `same_inferred_order` / `delivery_missing`.
- **Production ticket classifications:** first `missing_delivery_tracking` (0.90); return `other` (0.35).
- **Production pair:** `uncertain`; category `missing_delivery_tracking`; confidence 0.35; uncertain `True`.
- **First ticket:** > Product: the Pulse buds Order: VR900949 Purchased: 18/01 Issue: the courier marked it delivered but nobody in my house got anything Tried: called the courier Expected: replacement
- **Return ticket:** > Product: my Pulse Purchased: 18-01-2025 Issue: it has been 11 days and I have nothing in hand Tried: called the courier Expected: fix
- **Evidence from first:** “urchased: 18/01 issue: the courier marked it delivered but nobody in my house got anything tried: ca”
- **Evidence from return:** “product: my pulse purchased: 18-01-2025 issue: it has been 11 days and i have nothing in hand tried: called the courier”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** The return says “nothing in hand”; one unrecognized side forces the pair to uncertain.

### 3. False negative: `TK-240618` → `TK-240661`

- **Reference:** `same_explicit_order` / `delivery_missing`.
- **Production ticket classifications:** first `other` (0.35); return `missing_delivery_tracking` (0.90).
- **Production pair:** `uncertain`; category `missing_delivery_tracking`; confidence 0.35; uncertain `True`.
- **First ticket:** > Product: Pulse earbuds Order: VR888316 Purchased: 11 Feb Issue: tracking has said out for delivery for a wek now Tried: checked w/ neighbours Expected: fix
- **Return ticket:** > Dear team, Bought the Pullse buds around 11-02-2025 from vireo.in. I haven't received my order. I called the courier. I have been a loyal customer and this is how you treat me. Can someone fix this? Thanks Aishwarya
- **Evidence from first:** “product: pulse earbuds order: [order_id] purchased: 11 feb issue: tracking has said out for delivery for a wek now tried”
- **Evidence from return:** “around 11-02-2025 from vireo.in. i haven't received my order. i called the courier. i have been”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** A typo in “week” prevents the first tracking phrase from matching; the return matches correctly.

### 4. False negative: `TK-240334` → `TK-240712`

- **Reference:** `same_inferred_order` / `pairing`.
- **Production ticket classifications:** first `pairing_device_discovery` (0.90); return `other` (0.35).
- **Production pair:** `uncertain`; category `pairing_device_discovery`; confidence 0.35; uncertain `True`.
- **First ticket:** > it connects for a second and then vanishes from the device list
- **Return ticket:** > Writing again because the issue is back. my phone just doesn't see it in the list anymore
- **Evidence from first:** “it connects for a second and then vanishes from the device list”
- **Evidence from return:** “writing again because the issue is back. my phone just doesn't see it in the list anymore”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** The return describes device discovery indirectly (“doesn’t see it in the list”) and falls to other.

### 5. False negative: `TK-240172` → `TK-240278`

- **Reference:** `same_explicit_order` / `pairing`.
- **Production ticket classifications:** first `other` (0.35); return `pairing_device_discovery` (0.90).
- **Production pair:** `uncertain`; category `pairing_device_discovery`; confidence 0.35; uncertain `True`.
- **First ticket:** > pairing is not working. VR893696. how do i get this fixed?
- **Return ticket:** > I am losing patience. the AirLite buds purchased last month, order VR893696. cannot pair the AirLite buds with my laptop. I already restarted the phone. This is the last time I buy from you.
- **Evidence from first:** “pairing is not working. [order_id]. how do i get this fixed?”
- **Evidence from return:** “ased last month, order [order_id]. cannot pair the airlite buds with my laptop. i”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** “Pairing is not working” is outside the narrower pairing expressions, while the return matches.

### 6. False negative: `TK-240233` → `TK-240619`

- **Reference:** `same_explicit_order` / `payment_no_order`.
- **Production ticket classifications:** first `other` (0.35); return `payment_taken_no_order` (0.90).
- **Production pair:** `uncertain`; category `payment_taken_no_order`; confidence 0.35; uncertain `True`.
- **First ticket:** > product: pulse eabruds order: vr901328 purchased: 10 jan issue: paid via upi, amount deducted, no order confirmation tried: tried logging out and in expected: resolution
- **Return ticket:** > this was supposedly sorted by ur team last time. product: my pulse order: vr901328 purchased: 10-01-2025 issue: money debited but order not showing tried: tried logging out and in expected: replacement
- **Evidence from first:** “product: pulse eabruds order: [order_id] purchased: 10 jan issue: paid via upi, amount deducted, no order confirmation t”
- **Evidence from return:** “r_id] purchased: 10-01-2025 issue: money debited but order not showing tried: tried logging o”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** “Paid via UPI, amount deducted, no order confirmation” is missed on the first ticket.

### 7. False negative: `TK-240213` → `TK-240364`

- **Reference:** `same_inferred_order` / `payment_no_order`.
- **Production ticket classifications:** first `payment_taken_no_order` (0.90); return `other` (0.35).
- **Production pair:** `uncertain`; category `payment_taken_no_order`; confidence 0.35; uncertain `True`.
- **First ticket:** > [IVR transcript] helo payment was deducted but no order was created braided cable ??
- **Return ticket:** > Still not fixed after your last 'resolution'. Product: USB-C cable Purchased: 13-01-2025 Issue: my bank says Rs 4999 went to you but your site says I have no orders Tried: tried logging out and in Expected: callback
- **Evidence from first:** “[ivr transcript] helo payment was deducted but no order was created braided cable ??”
- **Evidence from return:** “still not fixed after your last 'resolution'. product: usb-c cable purchased: 13-01-2025 issue: my bank says rs 4999 wen”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** “Bank says ... no orders” is missed on the return ticket despite describing the same failed order.

### 8. False negative: `TK-240317` → `TK-240660`

- **Reference:** `same_explicit_order` / `battery_drain`.
- **Production ticket classifications:** first `duplicate_payment` (0.90); return `battery_drain` (0.90).
- **Production pair:** `different_issue`; category `battery_drain`; confidence 0.90; uncertain `False`.
- **First ticket:** > i am losing patience. got airlite from vireo.in last week. battery life has dropped to almost nothing. i already fully charged and discharged twice. escalate this to someone senior.
- **Return ticket:** > i am losing patience. i bought airlite earbuds on 27/10. battery draining even when not in use. i already updated the app. escalate this to someone senior.
- **Evidence from first:** “to almost nothing. i already fully charged and discharged twice. escalate this to someone senior.”
- **Evidence from return:** “i bought airlite earbuds on 27/10. battery draining even when not in use. i already”
- **Provider reason:** Offline development rules produced different categories.
- **Disagreement reason:** “Discharged twice” triggers duplicate-payment before the battery pattern, splitting one battery issue into two categories.

### 9. False negative: `TK-241772` → `TK-241927`

- **Reference:** `same_explicit_order` / `battery_drain`.
- **Production ticket classifications:** first `battery_drain` (0.90); return `duplicate_payment` (0.90).
- **Production pair:** `different_issue`; category `duplicate_payment`; confidence 0.90; uncertain `False`.
- **First ticket:** > [IVR transcript] hi i have to charge it twice a day now, it used to last days kindly do the needful
- **Return ticket:** > Namaste, Same problem again. Ordered pulse 1 2 weeks ago. Battery drains very fast, baarely lasts 2 hours. I fully charged and discharged twice. Nothing changed. How do I get this fixed? Thanks, Swati
- **Evidence from first:** “[ivr transcript] hi i have to charge it twice a day now, it used to last days kindly d”
- **Evidence from return:** “st, baarely lasts 2 hours. i fully charged and discharged twice. nothing changed. how do i get thi”
- **Provider reason:** Offline development rules produced different categories.
- **Disagreement reason:** The same pattern-order bug misreads troubleshooting (“charged and discharged twice”) as duplicate payment.

### 10. False negative: `TK-240354` → `TK-240677`

- **Reference:** `same_explicit_order` / `refund_pending`.
- **Production ticket classifications:** first `other` (0.35); return `refund_pending` (0.90).
- **Production pair:** `uncertain`; category `refund_pending`; confidence 0.35; uncertain `True`.
- **First ticket:** > Not what I expected from Vireo. This is regarding 65W charger. where is the money for the return. I already emailed twice. Escalate this to someone senior.
- **Return ticket:** > hi same problem again. refund not received yet the gan charger VR884997 hello??
- **Evidence from first:** “not what i expected from vireo. this is regarding 65w charger. where is the money for the return. i already emailed twic”
- **Evidence from return:** “hi same problem again. refund not received yet the gan charger [order_id] hel”
- **Provider reason:** Offline mode cannot confidently compare one or both messages.
- **Disagreement reason:** The indirect refund phrase “where is the money for the return” falls to other.

### 11. Apparent false positive: `TK-246168` → `TK-246224`

- **Reference:** `different_issue`.
- **Production ticket classifications:** first `duplicate_payment` (0.90); return `duplicate_payment` (0.90).
- **Production pair:** `high_confidence_repeat`; category `duplicate_payment`; confidence 0.90; uncertain `False`.
- **First ticket:** > not what i expected from vireo. bought the pulse 2 earbuds around october 13 from vireo.in. my bank shows the same amount twice on the same day. i already checked with bank. refund. now.
- **Return ticket:** > not what i expected from vireo. this is regarding pulse 2. goes from full to empty during one commute. i already fully charged & discharged twice. fix this or i am posting on twitter.
- **Evidence from first:** “3 from vireo.in. my bank shows the same amount twice on the same day. i already checked”
- **Evidence from return:** “uring one commute. i already fully charged & discharged twice. fix this or i am posting on twitt”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The return is battery drain, but “discharged twice” is misread as duplicate payment, creating a false match.

### 12. Apparent false positive: `TK-251260` → `TK-251466`

- **Reference:** `different_issue`.
- **Production ticket classifications:** first `duplicate_payment` (0.90); return `duplicate_payment` (0.90).
- **Production pair:** `high_confidence_repeat`; category `duplicate_payment`; confidence 0.90; uncertain `False`.
- **First ticket:** > Really frustrating. Bought Arc neckband around 01-10-2025 from Amazon. battery drains very fast, barely lasts 2 hours. I already fully charged & discharged twice. Escalate this to someone senior
- **Return ticket:** > Hey, Bought Arc neckband around October 01 from Amazon. Double payment deducted. I want a replacement. Regards
- **Evidence from first:** “ely lasts 2 hours. i already fully charged & discharged twice. escalate this to someone senior”
- **Evidence from return:** “and around october 01 from amazon. double payment deducted. i want a replacement. re”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The first ticket is battery drain and the return is an actual double charge; “discharged twice” makes both look like duplicate payment.

### 13. Apparent false positive: `TK-253672` → `TK-253707`

- **Reference:** `different_issue`.
- **Production ticket classifications:** first `duplicate_payment` (0.90); return `duplicate_payment` (0.90).
- **Production pair:** `high_confidence_repeat`; category `duplicate_payment`; confidence 0.90; uncertain `False`.
- **First ticket:** > product: my pulse 2 order: vr894586 purchased: 11/05 issue: card charged two times tried: checked with bank expected: refund
- **Return ticket:** > product: my pulse 2 order: vr894586 purchased: 11 may issue: i have to charge it twice a day now, it used to last days tried: fully charged and discharged twice expected: fix
- **Evidence from first:** “r_id] purchased: 11/05 issue: card charged two times tried: checked with bank expected:”
- **Evidence from return:** “it used to last days tried: fully charged and discharged twice expected: fix”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The return explicitly says charge twice a day, but the word “twice” is treated as a duplicate charge rather than battery drain.

### 14. Apparent false positive: `TK-241812` → `TK-241875`

- **Reference:** `different_issue`.
- **Production ticket classifications:** first `invoice_request` (0.90); return `invoice_request` (0.90).
- **Production pair:** `high_confidence_repeat`; category `invoice_request`; confidence 0.90; uncertain `False`.
- **First ticket:** > HELLO MY COMPANY ACCOUNTS TEAM IS ASKING FOR THE TAX BILL PULSE EARBUDS HELLO??
- **Return ticket:** > Pathetic experience honestly. This is regarding Pulse earbuds. ordered black, got white, not what I asked for. I already checked the invoice. This is the last time I buy from you.
- **Evidence from first:** “ny accounts team is asking for the tax bill pulse earbuds hello??”
- **Evidence from return:** “i asked for. i already checked the invoice. this is the last time i buy from”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The return is a wrong-colour item; merely mentioning that the invoice was checked causes an invoice-request match.

### 15. Apparent false positive: `TK-244382` → `TK-244670`

- **Reference:** `uncertain_symptom_change` / `one_side_audio`.
- **Production ticket classifications:** first `one_sided_audio` (0.90); return `one_sided_audio` (0.90).
- **Production pair:** `high_confidence_repeat`; category `one_sided_audio`; confidence 0.90; uncertain `False`.
- **First ticket:** > Hey, Ordered the AirLite buds last week. Right earbud completely silent. I reset the buds. Waiting for your reply. Regards Bhavna Mittal
- **Return ticket:** > Hey, This is the second time I am writing about this. This is regarding AirLite. Left side has no audio at all. I reset the buds. Nothing changed. Please resolve asap. Regards,
- **Evidence from first:** “the airlite buds last week. right earbud completely silent. i reset the buds. waiting for you”
- **Evidence from return:** “t this. this is regarding airlite. left side has no audio at all. i reset the buds. nothing”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** Both contacts are one-sided audio, but the affected side changes from right to left; the reference keeps this uncertain.

### 16. Apparent false positive: `TK-244774` → `TK-244979`

- **Reference:** `uncertain_text`.
- **Production ticket classifications:** first `bluetooth_dropouts` (0.90); return `bluetooth_dropouts` (0.90).
- **Production pair:** `high_confidence_repeat`; category `bluetooth_dropouts`; confidence 0.90; uncertain `False`.
- **First ticket:** > hello vireo, orbit mini purchased recently, order vr909955. audio keeps disconnecting every few minutes. i truned off wifi. nothing changed. pelase advise. thanks & regards, rajat sidiqui
- **Return ticket:** > keeps losing my phone if i walk to the othr room vr909955 i want my money back
- **Evidence from first:** “tly, order [order_id]. audio keeps disconnecting every few minutes. i truned off”
- **Evidence from return:** “keeps losing my phone if i walk to the othr room [order_”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The reference text rules leave this wording uncertain, while offline-rules-v1 treats both as Bluetooth dropouts; this is not an adjudicated false positive.

### 17. Apparent false positive: `TK-240206` → `TK-240415`

- **Reference:** `uncertain_text`.
- **Production ticket classifications:** first `duplicate_payment` (0.90); return `duplicate_payment` (0.90).
- **Production pair:** `high_confidence_repeat`; category `duplicate_payment`; confidence 0.90; uncertain `False`.
- **First ticket:** > Hi team, I bought my Nexa Fit band on 13/12. Battery liife has dropped to almost nothing. I fully cahrged and discharged twice. Honestly regretting this purchase. Kindly look into it. Rgds, Karan Chopra
- **Return ticket:** > Hi team, My earlier ticket got closed without a fix. This is regarding my Nexa Fit band. The promised 45 hours is nowhere close, I get maybe 2. I fully charged and discharged twice. Need this sorted ths week. Rgds
- **Evidence from first:** “st nothing. i fully cahrged and discharged twice. honestly regretting this purchase”
- **Evidence from return:** “here close, i get maybe 2. i fully charged and discharged twice. need this sorted ths week. rgds”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** Both messages describe battery life, but “discharged twice” makes both duplicate-payment classifications; the reference itself is uncertain because its text labels are incomplete.

### 18. Apparent false positive: `TK-247231` → `TK-248358`

- **Reference:** `uncertain_text`.
- **Production ticket classifications:** first `firmware_update_failure` (0.90); return `firmware_update_failure` (0.90).
- **Production pair:** `high_confidence_repeat`; category `firmware_update_failure`; confidence 0.90; uncertain `False`.
- **First ticket:** > [IVR transcript] hello ji after teh update prompt it went dark and never came baack the pullse 2 earbuds anyone there
- **Return ticket:** > dear sir/madam, yet again. i am writing with reference to my orrder of pusle 2 placed on 28-10-2025. the progress bar has not moved sincce morning. i hvae keppt phone nearby. i request you to kindly arrange a replacement. sincerely, shreya arora
- **Evidence from first:** “ivr transcript] hello ji after teh update prompt it went dark and never came baack the pullse 2”
- **Evidence from return:** “pusle 2 placed on 28-10-2025. the progress bar has not moved sincce morning. i hvae keppt phone”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The model finds a plausible firmware repeat that the reference rules leave uncertain; this case needs human adjudication before calling it wrong.

### 19. Apparent false positive: `TK-243125` → `TK-243355`

- **Reference:** `uncertain_text`.
- **Production ticket classifications:** first `microphone_failure` (0.90); return `microphone_failure` (0.90).
- **Production pair:** `high_confidence_repeat`; category `microphone_failure`; confidence 0.90; uncertain `False`.
- **First ticket:** > same issue as before, it came back after 2 weeks. works for music but useless for meetings how do i get this fixed?
- **Return ticket:** > fourth time writing about the same thing. - works for musiic but useless for meetings - please help
- **Evidence from first:** “after 2 weeks. works for music but useless for meetings how do i get this fixed?”
- **Evidence from return:** “same thing. - works for musiic but useless for meetings - please help”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The model finds a plausible microphone repeat from “useless for meetings”; the reference rules leave the typo variant uncertain.

### 20. Apparent false positive: `TK-242143` → `TK-242503`

- **Reference:** `uncertain_text`.
- **Production ticket classifications:** first `missing_delivery_tracking` (0.90); return `missing_delivery_tracking` (0.90).
- **Production pair:** `high_confidence_repeat`; category `missing_delivery_tracking`; confidence 0.90; uncertain `False`.
- **First ticket:** > I bought AirLite on May 15. Pakage not delivered even after 18 days. I checked teh tracking page daily. Nothig changed. Need tihs sorted thiis week.
- **Return ticket:** > hi sir again the same thing. i haven't received my order bahut paareshan hu pls reply
- **Evidence from first:** “i bought airlite on may 15. pakage not delivered even after 18 days. i checked teh”
- **Evidence from return:** “hi sir again the same thing. i haven't received my order bahut paareshan hu pls reply”
- **Provider reason:** Offline development rules produced matching categories.
- **Disagreement reason:** The model finds a plausible missing-delivery repeat that the reference text rules leave uncertain; it is outside the validated positive set, not a proven error.

## Reference limitations affecting interpretation

1. `classified_returns.csv` has `confirmed=True` on 1,068 rows because it includes 29 `same_explicit_recontact` cases. The validated 1,039 set must be reconstructed from `same_explicit_order` and `same_inferred_order`, consistent with the memo.
2. The preserved issue-level CSV and the final memos are not fully synchronized. The CSV contains 199 high-confidence delivery returns and 193 mature delivery origins, while the final investigation and baseline state 188 and 186. The rate comparison above therefore uses the established memo numerators and denominators; it does not silently replace them with the later working-file counts.
3. The reviewed reference is designed as a conservative lower bound. Contacts in its uncertainty buckets cannot establish true false positives without additional human adjudication.
4. The manual review described in the investigation supports positive-tier precision but does not estimate recall. The comparison here measures reproduction of the completed investigation, not objective ground truth for every pair.

## Production suitability

Keep `offline-rules-v1` only as an offline development fixture or deterministic fallback. It is not suitable for the final production classifier because it misses 49.47% of reviewed positives, materially understates both operating baselines, uses uncalibrated fixed confidence, and has predictable pattern-order failures. Its strong apparent precision comes largely from returning `uncertain` often; that conservatism does not compensate for losing half of the repeat-contact signal the application is intended to surface.
