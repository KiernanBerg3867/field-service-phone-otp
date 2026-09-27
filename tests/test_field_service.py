from src.field_service import InfraiClient, WorkOrder, complete_login, record_follow_up


def test_follow_up_moves_work_order_to_recorded_state():
    order = WorkOrder("WO-1042", "tech-7", "https://photos.example/wo-1042.jpg")
    result = record_follow_up(order, "Customer signed off")
    assert result["status"] == "follow_up_recorded"
    assert order.status == "follow_up_recorded"


def test_captcha_request_includes_widget_record_id():
    client = InfraiClient(api_key="test-key")
    requests = []

    def fake_post(path, body):
        requests.append((path, body))
        return {"data": {"session_id": "test-session"}}

    client.post = fake_post
    result = complete_login(client, "test-phone", "test-code", "test-token", "127.0.0.1", "widget-123")

    assert requests[0] == ("/v1/captcha/verify", {
        "widget_record_id": "widget-123",
        "token": "test-token",
        "vendor": "turnstile",
        "ip": "127.0.0.1",
        "action": "phone_login",
        "score_threshold": 0.5,
    })
    assert result["authenticated"] is True
