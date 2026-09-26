# Vireo Audio repeat-contact baseline and pilot target

## Observation window

The ticket export contains contacts through 30 June 2026. A ticket needs 30 complete days after resolution to determine whether it generated a repeat contact under the policy definition.

The analysis therefore includes resolved or auto-closed tickets where:

`corrected resolution timestamp + 30 days <= 1 July 2026 00:00 IST`

This makes 31 May 2026 the final eligible resolution date. Open and pending tickets, and tickets resolved from 1 June onward, are excluded from the denominator.

After removing re-import duplicates and correcting legacy resolution timestamps to IST, the mature cohort contains 10,485 completed tickets: 9,447 resolved and 1,038 auto-closed.

## Overall baseline

There are two useful views of the baseline.

### Conservative operational baseline

- Denominator: 10,485 mature resolved or auto-closed tickets.
- Numerator: 1,008 tickets followed by at least one high-confidence same-issue return contact within 30 days.
- Repeat-contact rate: `1,008 / 10,485 = 9.61%`.
- Corresponding first-contact resolution rate: `1 - 9.61% = 90.39%`.

This is the primary business baseline because it retains every mature completed ticket in the denominator. It is a lower bound: unresolved text or order linkage cannot create a confirmed numerator event.

### Evidence-complete diagnostic baseline

The mature cohort includes 1,029 tickets with no single clear complaint label and another 606 with weak or conflicting order evidence. Removing those cases leaves 8,850 evaluable tickets.

- Denominator: 8,850 mature tickets with one clear complaint and an explicit or uniquely inferable order.
- Numerator: 1,008 tickets followed by a confirmed same-issue return.
- Repeat-contact rate: `1,008 / 8,850 = 11.39%`.

The 9.61%-11.39% difference shows the measurement uncertainty created by incomplete text and order linkage. It is not appropriate to present 11.39% as the rate for all tickets.

The 1,008 failed-origin tickets produced 1,011 distinct repeat contacts in the observed window: 483 chat, 346 email, 77 voice and 105 social. Their historical support-capacity cost is:

`(483 x Rs 210) + (346 x Rs 260) + (77 x Rs 520) + (105 x Rs 240) = Rs 256,630`

The rate numerator counts original tickets that failed first-contact resolution; the cost calculation counts actual subsequent contacts, so the two counts need not be identical.

## Missing-delivery and stalled-tracking baseline

### Conservative operational baseline

- Denominator: 1,297 mature completed tickets whose opening complaint is missing delivery or stalled tracking.
- Numerator: 186 tickets followed by a high-confidence missing-delivery or stalled-tracking contact within 30 days.
- Repeat-contact rate: `186 / 1,297 = 14.34%`.
- Corresponding first-contact resolution rate: `1 - 14.34% = 85.66%`.

Missing delivery represents `1,297 / 10,485 = 12.37%` of the mature completed-ticket cohort.

### Evidence-complete diagnostic baseline

- Denominator: 1,238 mature missing-delivery tickets with reliable complaint and order evidence.
- Numerator: 186 tickets followed by a confirmed same-issue return.
- Repeat-contact rate: `186 / 1,238 = 15.02%`.

The 186 observed repeat contacts cost Rs 46,410 of historical support capacity. Their channel mix was 89 chat, 68 email, 11 voice and 18 social:

`(89 x Rs 210) + (68 x Rs 260) + (11 x Rs 520) + (18 x Rs 240) = Rs 46,410`

The average historical capacity cost for one missing-delivery repeat was:

`Rs 46,410 / 186 = Rs 249.52`

## Proposed quarterly pilot target

Use the conservative operational baseline for the target: reduce the missing-delivery repeat-contact rate by 25% relative, from 14.34% to 10.76% during a 13-week pilot.

`14.34% x (1 - 25%) = 10.76%`

This is a proposed operating threshold, not a forecast derived from a causal experiment. It is appropriate for testing a monitored delivery workflow because the earlier-ticket notes frequently show closure after a courier check, ETA, reshipment or refund initiation, before the downstream outcome is confirmed.

### Quarterly volume

Vireo's stated volume is approximately 650 tickets per week:

`650 x 13 weeks = 8,450 tickets per quarter`

Applying the observed missing-delivery share:

`8,450 x (1,297 / 10,485) = 1,045.27 expected missing-delivery tickets`

### Repeat contacts at baseline and target

Baseline:

`1,045.27 x (186 / 1,297) = 149.90 repeat contacts`

Pilot target:

`1,045.27 x 10.76% = 112.42 repeat contacts`

Difference:

`149.90 - 112.42 = 37.47`, or approximately **37 avoided repeat contacts per quarter**.

### Prospective support-capacity impact

Using the historical missing-delivery repeat-channel mix:

`37.47 x Rs 249.52 = Rs 9,351`

Rounded prospective impact: **approximately Rs 9,400 of support capacity per quarter** if the pilot reaches its target and the issue and channel mix remain comparable.

This is not a claim of Rs 9,400 in cash savings. It is capacity that could be reassigned to other contacts. It becomes cash savings only if Vireo can reduce paid staffing or another cash expense as a result.

If all other repeat issues remain unchanged, avoiding 37.47 contacts across 8,450 quarterly tickets would improve the overall conservative repeat-contact rate by about 0.44 percentage points:

`37.47 / 8,450 = 0.44 percentage points`

That would move the modeled overall rate from 9.61% to approximately 9.17%.

## Limits on the baseline and target

1. **The true repeat rate is not identifiable from this export.** Opening messages can be vague, follow-up conversation text is absent, and issue progressions are not counted. The 9.61% and 14.34% baselines are defensible lower bounds.
2. **Order linkage is incomplete.** Blank order IDs and customers with several orders for the same product create ambiguity. The evidence-complete rates show how much the denominator changes when those records are removed.
3. **June outcomes are right-censored.** Tickets resolved from 1 June onward do not have a full 30-day observation window and cannot enter the baseline.
4. **Identity changes are invisible.** Repeat contacts using a different customer ID, guest checkout, family account or unquoted product cannot be linked.
5. **Resolution does not prove the issue ended.** Auto-closure and an agent closing note describe helpdesk state. The export does not include courier delivery confirmation, refund settlement or complete ticket conversations.
6. **The legacy timestamp correction is inferred.** The exact 5 hour 30 minute difference across all 618 duplicated pairs strongly supports the UTC-to-IST correction, but the original event log was not supplied.
7. **The target is managerial, not causal.** Historical data can establish an opportunity and a measurement rule. It cannot show that a monitored workflow will achieve a 25% relative reduction. The pilot must test that.
8. **The capacity estimate assumes stable mix.** The calculation assumes 650 weekly tickets, a 12.37% missing-delivery share and the historical channel mix. Product launches, courier performance or channel shifts will change the result.
9. **Capacity value is not booked savings.** The policy's fully loaded channel rates measure planning capacity. Avoided contacts do not automatically reduce payroll or vendor invoices.

For pilot reporting, freeze the same eligibility and classification rules before launch, allow every ticket 30 days to mature, and compare the pilot with a seasonally comparable pre-period or a concurrent control group if operations permit.
