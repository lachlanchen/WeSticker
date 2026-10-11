# Subscriber Collection Downloads

The public catalog stays anonymous and makes no account request during browsing.
An explicit **Get collection** checks the current WeSticker account and downloads
the selected Chinese, English or Japanese ZIP through the app-owned entitlement
endpoint. It no longer sends a subscriber to the independent AYA storefront.

Guests go to the single app-level login with Account as the return destination.
Free or expired accounts go to Account. Access is checked again by the server;
expiry between the account check and download returns to Account without creating
a purchase. A failed download stays in the catalog with an inline error.
AYA purchases, orders and website behavior are unchanged.

Verification:

```bash
VITE_PUBLIC_CATALOG_ONLY=true npm run build
.venv/bin/python scripts/test_studio_isolated.py downloads
```

The browser fixtures cover guest, free, expired, subscribed, unavailable-account,
revoked-access and unavailable-ZIP states. All three lettering languages produce
browser downloads for the subscribed fixture. They also check zero anonymous
account traffic, no AYA checkout navigation and no JavaScript errors. These are
access/UI fixtures, not additional Stripe purchases.

All 30 configured production ZIPs (10 packs in three languages) passed archive
CRC validation locally. Provider payment qualification is recorded separately in
[Stripe qualification](stripe-qualification.md).

Deployed static release `f8cc441b16b6cba5`. Live 390-pixel browser verification
confirmed the public catalog fits its viewport and Get collection opens the root
login. Shared ingress and firewall were unchanged.
