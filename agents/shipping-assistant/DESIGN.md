# Shipping Assistant — Design Notes

## Marketplace promise

> Track shipments, notify stakeholders, and handle exceptions for logistics and distribution SMEs.  
> ▸ ShipStation · UPS · FedEx · USPS  
> Full order-to-delivery flow · fewer WISMO tickets  

## Why ShipStation as primary hub

| Criterion | ShipStation | Direct carrier APIs only | Store-native shipping only |
|-----------|-------------|--------------------------|----------------------------|
| SMB adoption | High | Dev-heavy | Channel-limited |
| Multi-carrier | UPS, FedEx, USPS, more | One API each | Limited |
| Multi-channel orders | Amazon, eBay, Shopify, etc. | No | Single store |
| Matches SHIP card | Yes | Secondary | Incomplete |

**Decision:** ShipStation is the system of record; carriers are reached through ShipStation for MVP.

## Product principles

1. **ShipStation = order/shipment system of record**  
2. **Track + exception queue + stakeholder notify drafts**  
3. **HITL** for cancel, address change, label buy  
4. **Demo mode** without API keys  
5. **Orchestration-ready** with Email Assistant (WISMO replies) and CRM (activity log)  

## MVP scope

| Feature | Status |
|---------|--------|
| List/sync orders & shipments (API or sample) | Yes |
| Track status + ETA summary | Yes |
| Exception detection | Yes |
| Stakeholder notification drafts | Yes |
| WISMO answer pack | Yes |
| HITL queue for destructive actions | Yes |
| Rate shop / create label | Stub + approval |

## Positioning

> Matrixly drafts tracking updates and exception playbooks — humans approve cancels, label changes, and outbound customer email.
