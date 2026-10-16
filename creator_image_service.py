"""HTTP entry point for the creator asset delivery example."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from openai import APIStatusError
from pydantic import BaseModel, Field

from creator_delivery import CreatorDelivery, DeliveryReceipt, InfraiImageGenerator


class CreatorImageRequest(BaseModel):
    asset_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    creator_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    prompt: str = Field(min_length=3, max_length=2000)
    subscriber_ids: list[str] = Field(min_length=1)


class DeliveryResponse(BaseModel):
    asset_id: str
    creator_id: str
    subscriber_ids: list[str]
    image_path: str
    status: str


@lru_cache
def delivery_service() -> CreatorDelivery:
    asset_dir = Path(os.environ.get("ASSET_DIR", "var/creator-assets"))
    return CreatorDelivery(InfraiImageGenerator(), asset_dir)


app = FastAPI(title="Creator image delivery")


@app.post("/creator-images", response_model=DeliveryResponse, status_code=201)
def create_creator_image(
    request: CreatorImageRequest,
    service: Annotated[CreatorDelivery, Depends(delivery_service)],
) -> DeliveryReceipt:
    try:
        return service.publish(
            asset_id=request.asset_id,
            creator_id=request.creator_id,
            prompt=request.prompt,
            subscriber_ids=request.subscriber_ids,
        )
    except APIStatusError as error:
        if 400 <= error.status_code < 500:
            raise HTTPException(status_code=error.status_code, detail="Image request was rejected") from error
        raise
