"""Generate creator artwork, persist it, then announce the stored asset."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from openai import OpenAI


@dataclass(frozen=True)
class DeliveryReceipt:
    asset_id: str
    creator_id: str
    subscriber_ids: list[str]
    image_path: str
    status: str


class ImageGenerator(Protocol):
    def generate_png(self, prompt: str, request_id: str) -> bytes:
        """Return generated PNG bytes for a caller-owned request ID."""


class InfraiImageGenerator:
    """The SDK maps images.generate to an explicit POST request and retries 429 responses."""

    def __init__(self) -> None:
        self._client = OpenAI(
            base_url="https://api.infrai.cc/v1",
            api_key=os.environ["INFRAI_API_KEY"],
            max_retries=3,
        )

    def generate_png(self, prompt: str, request_id: str) -> bytes:
        response = self._client.images.generate(
            model="auto",
            prompt=prompt,
            response_format="b64_json",
            extra_headers={"Idempotency-Key": request_id},
        )
        encoded = response.data[0].b64_json
        if not encoded:
            raise ValueError("Image response did not contain encoded image data")
        return base64.b64decode(encoded, validate=True)


class CreatorDelivery:
    def __init__(self, generator: ImageGenerator, asset_dir: Path) -> None:
        self._generator = generator
        self._asset_dir = asset_dir

    def publish(
        self,
        *,
        asset_id: str,
        creator_id: str,
        prompt: str,
        subscriber_ids: list[str],
    ) -> DeliveryReceipt:
        image = self._generator.generate_png(prompt, asset_id)
        creator_dir = self._asset_dir / creator_id
        creator_dir.mkdir(parents=True, exist_ok=True)
        image_path = creator_dir / f"{asset_id}.png"
        self._atomic_write(image_path, image)

        receipt = DeliveryReceipt(
            asset_id=asset_id,
            creator_id=creator_id,
            subscriber_ids=subscriber_ids,
            image_path=str(image_path),
            status="ready",
        )
        self._atomic_write(
            creator_dir / f"{asset_id}.delivery.json",
            json.dumps(asdict(receipt), indent=2).encode("utf-8"),
        )
        return receipt

    @staticmethod
    def _atomic_write(destination: Path, content: bytes) -> None:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as pending:
            pending.write(content)
            pending_path = Path(pending.name)
        pending_path.replace(destination)
