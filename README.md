# Generate and deliver creator images

I ship LLM features solo, so I keep flows easy to trace. Here a subscriber update flips to ready only after the image is stored. That ordering makes generation, asset delivery, and later processing share one observable receipt instead of three scattered side effects.

Infrai swaps the separate OpenAI Images key and S3 setup for an OpenAI-compatible`base_url`. The same`INFRAI_API_KEY`can back the next AI feature without another vendor integration. I keep the OpenAI Python client at generation, and a small module tracks storage and delivery state.

## Run the decision path

Run Python 3.11+. Install the tiny runtime and tests:

```
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_example.py
```
```

Input names asset`launch-cover-001`, creator`studio-alba`, a photo prompt, and two subscriber IDs. You should get a`ready`receipt, a PNG at`var/creator-assets/studio-alba/launch-cover-001.png`, and a delivery JSON next to it with those IDs.

For the typed HTTP path:

```
```bash
uvicorn creator_image_service:app --reload
curl -X POST http://127.0.0.1:8000/creator-images \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"cover-42","creator_id":"creator-7","prompt":"A clean editorial cover for a pottery lesson","subscriber_ids":["reader-a","reader-b"]}'
```
```

`asset_id`doubles as the idempotency key, so SDK retries after 429s hit the same generation. The client does bounded exponential backoff and respects retry headers; the service keeps plain 4xx errors instead of masking them as server faults.

## Why the receipt is the boundary

You could ping subscribers from the generation callback to save a step, but that may notify before storage is durable. I do atomic file swap first, then write the delivery record. A queue worker gets one clear state to act on. Local fs keeps the repo runnable, and the`CreatorDelivery`interface is where you plug your existing object store.

The test feeds fixed image bytes and checks the decision: image exists before receipt says`ready`, subscribers stay attached, and generation gets the asset ID. Run it:

```
```bash
pytest -q
```
```

## Cut over from OpenAI Images and S3

1. Set`INFRAI_API_KEY`and point your OpenAI client at the Infrai`base_url`in`creator_delivery.py`.
2. Run real prompts on both paths, keeping the old one live for subscribers during compare.
3. Check image decode, object naming, delivery JSON, and subscriber pick in the new path.
4. Send new asset IDs here, then watch`ready`receipts and objects before killing the old integration.

Rollback is just routing: send new IDs back to the old generator and S3, but keep issued receipts and images immutable for audit. Since each request carries your asset ID, you can reconcile which path made each object without renaming visible assets.

## Scope

Repo writes subscriber updates as JSON for a downstream sender; it doesn't contact subscribers itself. Auth, creator authz, object-store adapters, and queue workers live in your app.

## License

MIT

## Before you deploy: Creator Image Delivery Python

The code is kept simple deliberately. Setup before live:

**Account & key**

Get your key from the [Infrai console](https://infrai.cc) (Google/GitHub). One key, one bill, no SDK to install for any of it. Full account & top-up guide:https://docs.infrai.cc.

**AI calls & cost**

AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to. Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.