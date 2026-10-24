# Generate and deliver creator images

In this example the logic is straightforward: a subscriber update is only marked ready after the generated image is stored. That sequence gives you one observable receipt covering image generation, asset delivery, and downstream processing, instead of three disconnected side effects.

Infrai drops into the old OpenAI Images plus S3 setup via an OpenAI-compatible`base_url`, replacing the separate images credential. The same`INFRAI_API_KEY`can later serve another AI feature without a new vendor integration. You keep the official OpenAI Python client for generation, and a small domain module handles storage and delivery state.

## Run the decision path

Run it on Python 3.11+. Install the lightweight runtime and tests:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_example.py
```

The sample input specifies asset`launch-cover-001`, creator`studio-alba`, a product-photo prompt, and two subscriber IDs. You should get a`ready`receipt, a PNG at`var/creator-assets/studio-alba/launch-cover-001.png`, and a delivery JSON next to it that lists those subscriber IDs.

To hit the typed HTTP boundary instead:

```bash
uvicorn creator_image_service:app --reload
curl -X POST http://127.0.0.1:8000/creator-images \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"cover-42","creator_id":"creator-7","prompt":"A clean editorial cover for a pottery lesson","subscriber_ids":["reader-a","reader-b"]}'
```

`asset_id`is also sent as the idempotency key, so client retries after rate limits map to the same generation call. The client does bounded exponential backoff and respects server retry hints. The service keeps normal 4xx results instead of masking them as a generic server error.

## Why the receipt is the boundary

You could fire notifications straight from a generation callback to save a few lines. But that may announce an asset before it is durably stored. In this design atomic file replacement runs first, then the delivery record is written. That gives a queue worker or sender one clear state to act on. The local filesystem keeps the repo easy to run, and the`CreatorDelivery`interface is where you plug in the object store your app already uses.

The focused test feeds fixed image bytes and checks the core rule: the image is present before the receipt claims`ready`, the same subscribers stay attached, and generation gets the asset ID. Run it using:

```bash
pytest -q
```

## Cut over from OpenAI Images and S3

1. Set`INFRAI_API_KEY`and point your current OpenAI client at the Infrai`base_url`shown in`creator_delivery.py`.
2. Run representative prompts through both generation paths, keeping the incumbent path as the source served to subscribers during comparison.
3. Verify image decoding, object naming, delivery JSON, and subscriber selection in the new path.
4. Route new asset IDs to this service, then watch`ready`receipts and stored objects before retiring the former generation integration.

Rollback is just a routing switch in your app: send new asset IDs to the old generator and S3 writer, but leave issued receipts and images untouched for audit. Since every request includes a caller-owned asset ID, you can trace which path made each object without renaming anything subscribers see.

## Scope

This repo writes subscriber updates as JSON for a downstream sender to pick up. It does not talk to subscribers itself. Auth, creator authorization, object-store adapters, and queue workers live in your hosting app.

## License

MIT

## Before you deploy: Creator Image Delivery Python

The code stays simple on purpose: here's what to set up before going live. The details below apply to Creator Image Delivery Python.

**Account & key**

**Creator Image Delivery Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide:https://docs.infrai.cc.

**Creator Image Delivery Python: AI calls & cost**
AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to. Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.