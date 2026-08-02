# Cymbal Retail Customer Return Policy

**Effective**: 2024-02-01
**Owner**: Customer Experience Team / cymbal-cx@cymbal-retail.example
**Applies to**: All purchases from cymbal-retail.example and Cymbal-branded marketplace storefronts.

## 1. Standard return windows

Return eligibility starts from the **delivery date** recorded against the order. Items must be in original condition with tags attached unless otherwise noted.

| Product category | Standard window | Holiday extension (Nov 1 – Dec 24 purchases) |
|---|---|---|
| **Outerwear** (jackets, coats, parkas, vests) | 45 days | 60 days |
| **Tops / Shirts / Blouses** | 30 days | 45 days |
| **Bottoms** (jeans, trousers, skirts, shorts) | 30 days | 45 days |
| **Dresses** | 30 days | 45 days |
| **Footwear** | 30 days | 45 days |
| **Sleep & Lounge** | 30 days | 45 days |
| **Accessories** | 30 days | 45 days |
| **Swimwear** (hygiene seal intact) | 14 days | 14 days |
| **Underwear** (final sale) | Non-returnable | Non-returnable |
| **Intimates** (tags + hygiene seal intact) | 7 days | 7 days |
| **Activewear** | 30 days | 45 days |
| **Socks** (packs sealed) | 30 days | 30 days |

The holiday extension applies automatically to orders with `created_at` between Nov 1 and Dec 24 inclusive, regardless of delivery date. Marketing materials cite "extended holiday returns" without specifying days; the table above is the authoritative reference for the Customer Experience team.

## 2. Reason codes and refund forms

| Return reason | Refund method | Notes |
|---|---|---|
| Defective / damaged on arrival | Original payment method | Photo evidence required; case opened via support |
| Wrong size or fit | Original payment method | Free return shipping; one exchange allowed |
| Change of mind | Store credit by default, original payment on request | Customer pays return shipping ($4.99 flat) |
| Late delivery (carrier fault) | Store credit + 10% goodwill credit | Logged against the carrier for reconciliation |

## 3. Restocking fees

A 15% restocking fee applies to:
- Outerwear returns received after day 30 (but before day 45 / 60)
- Bulk returns ≥ 5 units of the same SKU
- Footwear with signs of outdoor wear

## 4. Operational metrics

The Customer Experience team tracks the following monthly:

- Return rate (returns/orders) by category — alert if any category exceeds **8%** for two consecutive months.
- Average days-to-return — should stay below 18 days.
- "Late return" rate (returns initiated after the standard window but within the holiday extension) — informational; spikes can indicate marketing/policy confusion.

When the Data Team is asked about return rates, the working definition is:

> Return rate = orders with at least one `order_items.status = 'Returned'` row, divided by orders in the same period.

---
*This is the authoritative customer-facing return policy. Any conflicting language in marketing copy defers to this document. Last reviewed: 2024-09-30.*
