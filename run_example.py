"""Run one delivery without starting the HTTP server."""

from pathlib import Path

from creator_delivery import CreatorDelivery, InfraiImageGenerator


receipt = CreatorDelivery(InfraiImageGenerator(), Path("var/creator-assets")).publish(
    asset_id="launch-cover-001",
    creator_id="studio-alba",
    prompt="Editorial product photograph of a handmade ceramic mug on a white table",
    subscriber_ids=["subscriber-17", "subscriber-29"],
)
print(receipt)
