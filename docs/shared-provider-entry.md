# Shared Provider Entry

Google, Apple and GitHub may use the maintained shared issuer while preserving
one WeSticker identity. This is separate from app-specific direct OAuth clients.

## Adapter

- `providers.lazyingart.selected_providers` is an explicit operator allowlist.
  Its default is empty. It accepts the four established provider names only.
- The optional SDK public availability method supplies validated enabled names.
  Missing SDK support or failed discovery leaves ordinary LazyingArt sign-in
  available without advertising the new social entry points.
- Bootstrap caches presentation for 30 seconds. Every selected authorization
  calls the SDK again with fresh discovery; cached UI is never authority.
- `/auth/google/start`, `/auth/apple/start` and `/auth/github/start` dispatch to
  `Client.authorize(provider=..., reuse_consent=True)`, not separate app clients.
  All return through the registered shared `/auth/lazyingart/callback`.
- Explicit provider selection does not reuse an unrelated existing app session.
  Neutral LazyingArt can reuse a validated app session and restore its tab.
- Native selection retains its independent one-use S256 return link. The
  currently delivered native binaries already render the advertised providers.
- A failed new entry preserves the previous browser binding and destination.
  Cancellation, callback replay and cross-browser rejection retain their guards.

No provider credential, callback token or customer identity belongs in this
repository. Shared identity does not grant a paid tier or merge AYA purchases.

## Activation Boundary

The adapter is prepared behind the empty allowlist. Installation must use the
owner-delivered SDK with public `available_authorization_providers()` and the
live issuer's exact `provider-select-v1` contract. Source fixtures alone do not
enable social buttons. Verify one-click provider continuation, actual callbacks,
account preservation and neutral consent reuse before recording qualification.
GitHub can remain unavailable while independently qualified providers proceed.

The app-boundary tests inject the SDK availability/authorization boundary; they
are not live provider or SDK-deployment evidence. Run the pinned SDK contract
tests and actual browser acceptance separately when the owner delivers it.

```sh
.venv/bin/python -m pytest -q tests/test_shared_identity.py tests/test_native_login_gate.py
```
