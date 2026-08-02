# Cymbal Retail Vendor SLA Template

**Document type**: Template — used as the baseline for negotiating new supplier agreements.
**Owner**: Procurement Team / cymbal-procurement@cymbal-retail.example
**Version**: 2024-Q3

## 1. Purpose

This template defines the **default** service-level expectations Cymbal Retail negotiates with new vendors. Active vendor agreements override the template where they explicitly do so; otherwise the template terms apply.

## 2. Default shipping windows

| Period | Standard window | Notes |
|---|---|---|
| Standard ops (Feb 1 – Sep 30) | 5 business days | From PO acknowledgement to carrier scan-in |
| Peak surge (Oct 15 – Nov 30) | 8 business days | Allowance for capacity constraints |
| Holiday freeze (Dec 1 – Dec 31) | 12 business days | New POs discouraged; expedites priced separately |

## 3. Default penalty structure

- Late-shipment fee: **$25** per PO line item exceeding the contractual window.
- Active suppliers (Apollo Athletic Goods is an example) negotiate higher windows in exchange for higher per-incident penalties — see individual agreements.

## 4. Defect rate threshold

- Default acceptable defect rate: **1.0%** of shipped units.
- A category-specific override applies for outerwear (0.8%) because customer dissatisfaction with defective jackets disproportionately drives returns.

## 5. Breach escalation

> A breach is defined as exceeding the contractual late-shipment threshold for two consecutive months. On a confirmed breach, Cymbal Retail may suspend new POs, source from alternate vendors at up to 15% above contract price, or terminate for cause with 30 days written notice.

The Data Team's monthly supplier-SLA reconciliation report uses `order_items.shipped_at` minus `orders.created_at` as the ship-time signal, filtered to category and SKU prefixes per vendor.

---
*Template only. Do not cite this document for active vendor questions — refer to the signed agreement for that vendor instead.*
