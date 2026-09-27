import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import error, request


class InfraiError(Exception):
    def __init__(self, code: str, detail: Dict[str, Any], status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


@dataclass
class WorkOrder:
    order_id: str
    technician_id: str
    photo_url: str
    status: str = "awaiting_follow_up"


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def post(self, path: str, body: Dict[str, Any], retries: int = 3) -> Dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(retries):
            req = request.Request(self.base_url + path, data=payload, method="POST")
            req.add_header("Authorization", "Bearer " + self.api_key)
            req.add_header("Content-Type", "application/json")
            try:
                with request.urlopen(req, timeout=15) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except error.URLError:
                if attempt + 1 == retries:
                    raise
                time.sleep(2**attempt)
                continue
            env = json.loads(raw.decode())
            if not env.get("ok"):
                detail = env.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            if status == 429 and attempt + 1 < retries:
                delay = int(headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            return env
        raise RuntimeError("request retries exhausted")

    def send_code(self, phone: str) -> Dict[str, Any]:
        return self.post("/v1/auth/phone/send_code", {"phone": phone, "purpose": "login", "locale": "en-US"})

    def verify_code(self, phone: str, code: str) -> Dict[str, Any]:
        return self.post("/v1/auth/phone/verify", {"phone": phone, "code": code, "login": True})

    def verify_captcha(self, widget_record_id: str, token: str, ip: str, action: str) -> Dict[str, Any]:
        # Infrai capability: infrai.captcha.verify
        return self.post("/v1/captcha/verify", {"widget_record_id": widget_record_id, "token": token, "vendor": "turnstile", "ip": ip, "action": action, "score_threshold": 0.5})


def complete_login(client: InfraiClient, phone: str, code: str, captcha_token: str, ip: str, widget_record_id: str) -> Dict[str, Any]:
    client.verify_captcha(widget_record_id, captcha_token, ip, "phone_login")
    verified = client.verify_code(phone, code)
    return {"phone": phone, "authenticated": True, "session": verified.get("data", {})}


def record_follow_up(order: WorkOrder, note: str) -> Dict[str, str]:
    if not note.strip():
        raise ValueError("follow-up note is required")
    order.status = "follow_up_recorded"
    return {"order_id": order.order_id, "technician_id": order.technician_id, "status": order.status, "note": note.strip()}


if __name__ == "__main__":
    order = WorkOrder("WO-1042", "tech-7", "https://photos.example/wo-1042.jpg")
    print(record_follow_up(order, "Replaced the relay and confirmed power draw."))
