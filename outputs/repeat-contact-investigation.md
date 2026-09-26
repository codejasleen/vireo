# Vireo Audio repeat-contact investigation

## Result

Of 3,304 candidate return contacts, 1,039 can be classified with high confidence as the same issue. These contacts used Rs 263,740 of historical support-handling capacity at the policy's channel rates.

This is a conservative count, not a repeat-contact rate. It does not include 29 probable repeats where the customer explicitly referred to the same issue but the order could not be linked reliably. It also excludes issue progressions such as delivery failure followed by refund delay, even though they may belong to the same service episode.

## Cleaning and matching

1. Removed 653 re-imported duplicate ticket IDs, leaving 11,875 distinct tickets.
2. Added 5 hours 30 minutes to legacy resolution timestamps. Every one of the 618 duplicate pairs with two resolution timestamps showed exactly this offset.
3. Generated 3,304 candidate return contacts: same customer and product, created within 30 days after an earlier ticket's resolution. A return could have more than one eligible earlier ticket, producing 4,144 candidate pairs.
4. Classified the complaint in the customer's opening message. Intake tags and agent notes were supporting checks, not the primary label.
5. Counted a return as high confidence only when the complaint matched and the two tickets had either the same explicit order ID or the same uniquely inferable customer-product order.

The 3,304 candidates split as follows:

| Disposition | Return contacts |
|---|---:|
| Same issue, same explicit order | 654 |
| Same issue, same uniquely inferable order | 385 |
| **High-confidence same issue** | **1,039** |
| Explicit same-issue wording but weak order link | 29 |
| Uncertain | 1,026 |
| Different issue | 1,210 |
| **Total candidates** | **3,304** |

The uncertain group contains 526 contacts with insufficient complaint text, 458 plausible issue progressions, 27 same-symptom cases without enough linkage, 12 order conflicts, and 3 cases where the affected side or symptom changed.

## Cost calculation

The policy costs a return contact at the channel used: chat Rs 210, email Rs 260, voice Rs 520, social Rs 240.

| Channel | High-confidence repeats | Rate | Capacity cost |
|---|---:|---:|---:|
| Chat | 496 | Rs 210 | Rs 104,160 |
| Email | 357 | Rs 260 | Rs 92,820 |
| Voice | 79 | Rs 520 | Rs 41,080 |
| Social | 107 | Rs 240 | Rs 25,680 |
| **Total** | **1,039** |  | **Rs 263,740** |

Arithmetic: `(496 x 210) + (357 x 260) + (79 x 520) + (107 x 240) = Rs 263,740`.

These figures value consumed support capacity. They do not establish cash savings.

## Major high-confidence repeat issues

| Issue | Repeat contacts | Capacity cost |
|---|---:|---:|
| Delivery missing or tracking stalled | 188 | Rs 46,930 |
| Pairing or device discovery | 93 | Rs 24,500 |
| Refund pending | 79 | Rs 21,470 |
| Return pickup missed or pending | 70 | Rs 19,420 |
| Payment taken but order not created | 66 | Rs 16,000 |
| Battery drain | 58 | Rs 15,810 |
| Bluetooth dropouts | 50 | Rs 12,340 |
| Audio distortion | 46 | Rs 11,620 |
| Coupon or discount not applied | 43 | Rs 11,120 |
| App crash or failure to open | 48 | Rs 11,090 |
| Repair or warranty-status follow-up | 43 | Rs 10,180 |
| Firmware update failure | 41 | Rs 10,200 |
| Wrong item or variant | 37 | Rs 9,940 |
| Transit damage | 39 | Rs 9,140 |
| One-sided audio | 32 | Rs 8,570 |

The remaining seven categories account for 106 contacts and Rs 25,410.

## Highest-cost product, issue and channel combinations

| Product | Issue | Return channel | Repeats | Capacity cost |
|---|---|---|---:|---:|
| Pulse 2 earbuds | Delivery missing | Email | 16 | Rs 4,160 |
| Pulse earbuds | Delivery missing | Chat | 17 | Rs 3,570 |
| Pulse 2 earbuds | Delivery missing | Chat | 12 | Rs 2,520 |
| Nexa 2 smartwatch | Delivery missing | Chat | 12 | Rs 2,520 |
| Pulse 2 earbuds | Bluetooth dropouts | Email | 9 | Rs 2,340 |
| Pulse 2 earbuds | Return pickup | Email | 9 | Rs 2,340 |
| Nexa 2 smartwatch | Delivery missing | Email | 9 | Rs 2,340 |
| Strata 3 headphones | Delivery missing | Chat | 11 | Rs 2,310 |
| Pulse 2 earbuds | Refund pending | Chat | 10 | Rs 2,100 |
| AirLite earbuds | Delivery missing | Email | 8 | Rs 2,080 |
| Pulse earbuds | Delivery missing | Email | 8 | Rs 2,080 |
| Pulse 2 earbuds | Pairing | Email | 8 | Rs 2,080 |
| Pulse 2 earbuds | Payment taken, no order | Email | 8 | Rs 2,080 |
| Pulse 2 earbuds | Battery drain | Voice | 4 | Rs 2,080 |
| Pulse 2 earbuds | Refund pending | Voice | 4 | Rs 2,080 |

Example arithmetic: `16 Pulse 2 delivery repeats by email x Rs 260 = Rs 4,160`.

## Strongest actionable opportunity

The strongest single opportunity is premature closure of unresolved delivery cases.

Delivery missing or stalled tracking is the largest confirmed issue: 188 repeat contacts and Rs 46,930 of historical support capacity. The channel calculation is `(89 chat x Rs 210) + (70 email x Rs 260) + (11 voice x Rs 520) + (18 social x Rs 240) = Rs 46,930`.

It appears across every product family rather than only one device. Pulse 2 has the largest product subtotal at 34 repeat contacts and Rs 8,400, followed by Pulse earbuds at 29 and Rs 6,890, and Nexa 2 at 23 and Rs 5,340.

The earlier closing notes show a process pattern. Among the 188 earlier-ticket links, 141 mention checking the courier or AWB, 81 mention reshipment, 48 give a delivery confirmation or ETA, 46 mention a refund, and 63 include explicit closure language. These counts overlap. They indicate that agents often record an action and close the ticket before the downstream outcome is confirmed.

The actionable intervention to evaluate is a monitored delivery-case workflow: keep the ticket pending, or create a scheduled follow-up, until delivery, reshipment, or refund is confirmed. This investigation does not set a target or claim prospective savings.

## Representative tickets

### Missing delivery after a refund was initiated

- `TK-253297` concerned Pulse 2 order `VR906313`: "I haven't received my order." The closing note says a refund was initiated as lost in transit.
- `TK-253925` opened 14.08 days after resolution for the same order: "Writing again because the issue is back... order not delivered, tracking not updating." It arrived by email and therefore represents Rs 260 of repeat-contact capacity.

### Missing delivery after a courier ETA

- `TK-252100` concerned Orbit Mini order `VR888416`: the courier marked it delivered, but the customer had not received it. The note says the courier confirmed delivery for 14 April and the ticket was closed.
- `TK-252853` opened 22.42 days after resolution: "I haven't received my order." This email return represents Rs 260.

### Refund pending

- `TK-253271` for Strata 3 order `VR883322`: "The return was accepted but the amount is nowhere in my account."
- `TK-253800` returned for the same order: "This was supposedly sorted by your team last time... the amount is nowhere in my account." This chat return represents Rs 210.

### Pairing failure

- `TK-249302` for Orbit order `VR900864`: "Cannot pair... with my laptop."
- `TK-250267` returned for the same order: "My phone just doesn't see it in the list anymore." This chat return represents Rs 210.

### Excluded because it is a different issue

- `TK-249196` concerns refund not received for order `VR904527`.
- `TK-249413`, six days later for the same order, concerns a firmware update stuck at 67%. The customer and product match, but the complaint does not. It is not counted as a repeat contact.

## Validation and limitations

A fixed, issue-stratified sample of 68 classified pairs was reviewed manually. All 67 sampled pairs from the two high-confidence tiers were consistent with the same issue. This is 0 observed errors in 67, but it does not prove a zero error rate; the simple rule-of-three upper bound is about 4.5%. One sampled pair from the weaker explicit-recontact tier had conflicting product wording; that finding is why the 29 cases in that tier are excluded from the headline.

This review sample supports the precision of the conservative rule but does not measure recall. The method deliberately misses valid repeats when descriptions are vague, when an issue progresses from delivery to refund or pickup, or when order linkage is ambiguous. It also relies on the exported customer and product identifiers being correct. The 1,039 count should therefore be treated as a defensible lower bound within the 3,304 candidates.
