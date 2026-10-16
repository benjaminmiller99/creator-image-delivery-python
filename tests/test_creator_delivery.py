from pathlib import Path

from creator_delivery import CreatorDelivery


class RecordingGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate_png(self, prompt: str, request_id: str) -> bytes:
        self.calls.append((prompt, request_id))
        return b"deterministic-png"


def test_subscribers_are_updated_only_for_a_stored_asset(tmp_path: Path) -> None:
    generator = RecordingGenerator()
    delivery = CreatorDelivery(generator, tmp_path)

    receipt = delivery.publish(
        asset_id="cover-42",
        creator_id="creator-7",
        prompt="A clean cover photograph",
        subscriber_ids=["reader-a", "reader-b"],
    )

    assert generator.calls == [("A clean cover photograph", "cover-42")]
    assert Path(receipt.image_path).read_bytes() == b"deterministic-png"
    assert receipt.status == "ready"
    assert receipt.subscriber_ids == ["reader-a", "reader-b"]
    assert (tmp_path / "creator-7" / "cover-42.delivery.json").exists()
