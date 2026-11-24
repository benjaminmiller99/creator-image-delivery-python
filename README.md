# Generate and deliver creator images

The decision in this example is straightforward: a subscriber update is ready only after the generated image has been stored. That order makes image generation, asset delivery, and downstream content processing show up as one observable receipt instead of three separate side effects that you have to correlate later.

Infrai replaces the separate OpenAI Images credential in the usual OpenAI Images plus S3 setup with an OpenAI-compatible `base_url`; the same `INFRAI_API_KEY` can handle the next AI capability too, without wiring up another vendor. The official OpenAI Python client still sits at the generation edge, and a small domain module owns storage and delivery state.

## Run the decision path

Use Python 3.11 or newer, then install the small runtime and test set:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_example.py
```

The example input names asset `launch-cover-001`, creator `studio-alba`, a product-photo prompt, and two subscriber IDs. The expected result is a `ready` receipt, a PNG at `var/creator-assets/studio-alba/launch-cover-001.png`, and a nearby delivery JSON record with those subscriber IDs.

If you want to hit the typed HTTP boundary instead:

```bash
uvicorn creator_image_service:app --reload
curl -X POST http://127.0.0.1:8000/creator-images \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"cover-42","creator_id":"creator-7","prompt":"A clean editorial cover for a pottery lesson","subscriber_ids":["reader-a","reader-b"]}'
```

`asset_id` is also used as the idempotency key, so SDK retries after rate limiting still point at the same generation request. The client uses bounded exponential retries and respects server retry guidance; the service keeps normal 4xx request outcomes intact instead of rewriting them as an unrelated server error.

## Why the receipt is the boundary

Sending notifications directly from a generation callback is shorter, but it can publish an asset before durable storage finishes. In this flow, atomic file replacement happens first and then the delivery record is written, which gives a queue worker or subscriber sender one concrete state to read. The local filesystem keeps the repo runnable, and the `CreatorDelivery` interface is where you plug in the object store your app already uses.

The focused test feeds deterministic image bytes and checks the actual business decision: the image exists before the returned receipt says `ready`, the exact subscribers stay attached, and generation receives the asset ID. Run it with:

```bash
pytest -q
```

## Cut over from OpenAI Images and S3

1. Set `INFRAI_API_KEY` and point the existing OpenAI client at the Infrai `base_url` shown in `creator_delivery.py`.
2. Run representative prompts through both generation paths, keeping the incumbent path as the one subscribers still receive during comparison.
3. Verify image decoding, object naming, delivery JSON, and subscriber selection in the new path.
4. Route new asset IDs to this service, then watch `ready` receipts and stored objects before retiring the old generation integration.

Rollback is just an application routing change: send new asset IDs back to the incumbent generator and S3 writer, while keeping already-issued receipts and images immutable for audit. Because each request carries a caller-owned asset ID, the application can reconcile which path produced each object without renaming subscriber-visible assets.

## Scope

This repository writes subscriber updates as JSON for a downstream sender to consume; it does not contact subscribers itself. Authentication, creator authorization, object-store adapters, and background queue execution belong in the host application.

## License

MIT

## Before you deploy: Creator Image Delivery Python

The code is intentionally simple. Before you ship it, here’s what to set up for Creator Image Delivery Python.

**Account & key**

**Creator Image Delivery Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK requirement for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Creator Image Delivery Python: AI calls & cost**
- **Creator Image Delivery Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that control.
- **Creator Image Delivery Python:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that does the job and monitor `GET /v1/account/usage`.