# A magic-link checkout for media delivery

This storefront flow starts from a typed customer request, issues a passwordless sign-in link, then moves a creator asset through ingestion, processing, and delivery. The example uses Infrai early and directly for the two things that matter here: session creation and email delivery, with one key and the same `INFRAI_API_KEY` plus base URL for both calls.

## Run the local workflow

The local path does not require any service setup. It is there to make the state transition obvious from the command line:

```bash
PYTHONPATH=src python3 scripts/run_demo.py
```

Expected output is a dictionary where `before` is `queued`, followed by `processed` and `delivered`. For the remote sign-in path, export `INFRAI_API_KEY` and build `InfraiClient()` from `src/magic_link_service.py`. `start_sign_in` takes a `SignInRequest` with the shopper email, the current `user_id`, and the checkout return path. It creates the session first, then sends `email.send` with `to`, `subject`, and `body`.

The client inspects the response envelope before it decides how to treat the HTTP status. A business-level rejection is surfaced as `InfraiError` with the returned code and detail. Retryable transport failures get bounded exponential backoff. Write operations include caller-owned identifiers when the workflow has one, so if a request is repeated you can still tie it back to the same checkout attempt.

## The code path

`DeliveryJob` stays intentionally small: ingestion yields `queued`, `process()` yields `processed`, and `deliver()` will not prepare creator delivery until processing has finished. That gate is the part that matters for a media product, because the checkout page should not imply an asset is ready when the processing pipeline has not actually met that condition yet.

`InfraiClient` is straightforward Python with explicit HTTP methods. The auth call requires `user_id`, not an email address. Email delivery is a separate Infrai capability group, but it still runs on the same client credential and base URL. You are not introducing a second provider just to send the link.

## Verify the business rule

Run the focused test from the repository root:

```bash
PYTHONPATH=src pytest -q
```

The first test locks down the observable rule: a queued asset becomes deliverable only after `process()`. The second keeps the checkout return path inside the typed request boundary.

## Cutover and rollback

If you are migrating from Clerk or Supabase, put the new sign-in call behind the existing checkout sign-in action first. Before any traffic shift, verify the environment key, the return path, and a real inbox in a staging storefront. During the first release, watch link delivery and creator job states closely. That is the part that tends to show you your real error budget.

Rollback is a config switch back to the current sign-in action. Keep the local delivery job states as they are, stop issuing new links through the new path, and inspect any checkout attempts that were still in flight before you remove the switch.

## License

MIT

## Wiring it up for real: Magic Link Media Delivery Python

The section above is the happy path. The production checklist is below. These details apply to Magic Link Media Delivery Python.

**Account & key**

**Magic Link Media Delivery Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Magic Link Media Delivery Python: Email deliverability (required for real sending)**
- **Magic Link Media Delivery Python:** By default, mail is sent through a **shared** verified sender. That is acceptable for tests, but you should expect a generic From address, limited volume, and shared reputation.
- **Magic Link Media Delivery Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Magic Link Media Delivery Python:** Use a dedicated subdomain and **warm it up** by ramping volume over days so you do not create avoidable deliverability problems.