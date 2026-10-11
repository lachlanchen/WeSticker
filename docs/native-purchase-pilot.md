# Native Purchase Pilot

The native test lane is distinct from web Stripe sales. Store catalog activation
and signed TEST notifications do not verify a purchase or restore.

## Exact-Account Setup

1. Confirm the installed native app's authenticated account matches the retained
   app identity. Do not infer this from an Apple/Google email address.
2. Verify TestFlight/Sandbox or Google license-testing and the actual no-charge
   instrument before purchasing. Internal-track enrollment alone is insufficient.
3. Prepare a private candidate for one provider, with its existing app/product/
   notification settings unchanged and exactly that account in both purchase and
   sandbox-delivery lists.
4. Use `scripts/prepare_native_pilot.py` to merge only that provider's four pilot
   fields into a separate current-runtime configuration. Review the difference
   and activate through the normal queue-idle, backed-up deployment.

```sh
.venv/bin/python scripts/prepare_native_pilot.py \
  --config .config/creator.json \
  --pilot-config .config/native-billing-apple-pilot.json \
  --provider apple --user-id "$VERIFIED_APP_ACCOUNT_ID" \
  --output .config/creator-pilot-staged.json
```

The helper performs no provider action or deployment. It refuses changed
credentials/catalog/notifications, broad purchase audiences and overwriting an
existing rollout. Stripe, generation, shared identity and the other native
provider are preserved. Previous sandbox-delivery accounts remain eligible for
receipt recovery; only the selected owner can begin a new purchase.

## Verification

Capture actual product lookup, native purchase result, provider receipt, one-time
credit delivery, store finish/acknowledgement, restart/restore and relevant
renewal/cancellation/expiry events. Retain exact pending attempts after uncertain
outcomes. Sign-out/account-switch checks must not transfer another account's
purchase. Record provider truth and app delivery separately.

Closing new purchase access must retain verification, restore, notifications and
the sandbox-delivery audience while test lineage remains active. Do not use the
notification-only preparation helper to replace an active pilot. Public native
sales stay separate until their app-specific qualification is complete.
