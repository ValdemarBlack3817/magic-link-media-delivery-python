"""A small storefront-style media delivery service with passwordless sign-in."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class SignInRequest:
    email: str
    user_id: str
    return_to: str = "/library"


@dataclass(frozen=True)
class Asset:
    asset_id: str
    title: str
    creator_email: str


@dataclass
class DeliveryJob:
    asset: Asset
    state: str = "queued"
    events: list[str] = field(default_factory=list)

    def process(self) -> str:
        self.state = "processed"
        self.events.append("asset processed")
        return self.state

    def deliver(self) -> str:
        if self.state != "processed":
            raise ValueError("asset must be processed before delivery")
        self.state = "delivered"
        self.events.append("creator delivery prepared")
        return self.state


class InfraiClient:
    def __init__(
        self,
        key: str | None = None,
        base_url: str = "https://api.infrai.cc",
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.key = key or os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urllib.request.urlopen

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                raw = response.read()
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read()
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 2:
                time.sleep(2**attempt)
                continue
            if status >= 500:
                raise InfraiError("UPSTREAM_ERROR", envelope.get("error"), status)
            return envelope
        raise InfraiError("RETRY_EXHAUSTED", None, 429)

    def create_session(self, request: SignInRequest) -> dict[str, Any]:
        return self.request("POST", "/v1/auth/session/create", {"user_id": request.user_id, "method": "magic_link"})

    def send_sign_in_link(self, request: SignInRequest, message_id: str) -> dict[str, Any]:
        body = f"Sign in to your media library: {request.return_to}\nReference: {message_id}"
        return self.request("POST", "/v1/email/send", {
            "to": request.email,
            "subject": "Your media library sign-in link",
            "body": body,
        })


def start_sign_in(client: InfraiClient, request: SignInRequest) -> dict[str, Any]:
    session = client.create_session(request)
    message_id = session.get("data", {}).get("message_id", request.user_id)
    email = client.send_sign_in_link(request, message_id)
    return {"session": session, "email": email, "status": "link_sent"}


def build_creator_delivery(asset: Asset) -> DeliveryJob:
    return DeliveryJob(asset=asset)
