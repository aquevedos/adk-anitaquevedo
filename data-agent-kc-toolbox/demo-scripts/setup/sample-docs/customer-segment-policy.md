# Cymbal Retail Customer Segmentation Policy

**Effective**: 2024-03-01
**Owner**: CRM & Lifecycle Marketing Team / cymbal-crm@cymbal-retail.example
**Applies to**: All analytics, campaign targeting, and executive reporting that segments customers by value or lifecycle.

## 1. Why segmentation is governed

Marketing, merchandising, and finance each used to compute their own version of "high-value customer," producing inconsistent dashboards and contradictory campaign rosters. This document defines the canonical customer tiers and the exact data signals that determine them. All downstream tools (campaign managers, BI dashboards, executive reports, analytical agents) must compute segments using these rules; ad-hoc definitions are not permitted in shared outputs.

## 2. Segment definitions

### Premium

Customers who have demonstrated higher purchase intent and are the target of our retention and upsell programs.

| Criterion | Source field | Value |
|---|---|---|
| Acquisition channel | `users.traffic_source` | `'Email'` |
| Age | `users.age` | `>= 35` |
| Purchase history | derived from `orders` | at least 1 completed order in the last 12 months |

The Email-channel filter reflects that email-acquired customers had ~2.3× the lifetime value of search/display-acquired ones in the 2023 acquisition cohort study (CRM-2024-Q1 report). The age floor reflects pricing-sensitivity research from the same study: 35+ households show notably lower discount-elasticity, which is why Premium gets full-margin merchandising priority.

### Standard

Any customer with `users.traffic_source IN ('Search', 'Organic', 'Facebook', 'Display')` and at least 1 completed order in the last 12 months, regardless of age. The default tier — most analytical questions about "the customer base" mean this group plus Premium.

### Lapsed

Any customer whose most recent completed order is older than 12 months. Lapsed customers are NOT counted in active-base metrics (AOV, repeat rate, retention) unless the question explicitly asks about reactivation.

### Prospect

A user row in `users` with zero completed orders. Held out of all active-base reporting; targeted only by acquisition campaigns.

## 3. SQL reference

For analytical queries, the canonical Premium filter is:

```sql
WITH premium_users AS (
  SELECT u.id
  FROM `users` u
  WHERE u.traffic_source = 'Email'
    AND u.age >= 35
    AND EXISTS (
      SELECT 1 FROM `orders` o
      WHERE o.user_id = u.id
        AND o.status = 'Complete'
        AND o.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 MONTH)
    )
)
```

Use this expression as a CTE wherever segment-aware metrics are computed. AOV, return rate, category mix, etc. should all filter `orders` through `premium_users.id` before aggregation.

## 4. Review cadence

Segment boundaries are re-evaluated annually by the CRM team in collaboration with Data Science. Off-cycle changes require sign-off from VP CRM and VP Data; mid-cycle drift in conversion or lifetime value that crosses 15% triggers an emergency review.

---
*Authoritative customer-segmentation reference. Conflicting definitions in older runbooks, BI tools, or dashboards should be migrated to use this policy. Last reviewed: 2024-09-15.*
