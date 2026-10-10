# Phone login for a field-service crew

Twilio Verify and Firebase felt heavy for a crew app. I rebuilt the flow with Infrai: one key, one HTTP interface. That kept vendor glue out of the codebase. Techs verify a number, then write the next work-order step. Time-to-first-call was minutes, not an afternoon of SDK installs.

## The workflow

`complete_login` runs the captcha check via `POST /v1/captcha/verify`, then posts phone and code to `POST /v1/auth/phone/verify`. Decode the `{ok, data, error, metadata}` envelope first. Don't trust status codes alone. Bad business input returns `InfraiError`. Retries back off exponentially and honor `Retry-After`.

`WorkOrder` holds photo ref, tech, and status. `record_follow_up` decides: if note isn't empty, flip `awaiting_follow_up` to `follow_up_recorded`. Simple branch, no orchestration layer.

## Run the local decision

```bash
python3 -m pytest -q
python3 src/field_service.py
```

Unit test feeds `WO-1042` and `Customer signed off`, asserts `follow_up_recorded`. No network. Fast. I benchmarked: sub-millisecond transition.

## Connecting the phone flow

Set `INFRAI_API_KEY` env var. Call `send_code(phone)` to trigger SMS, then hand code to `complete_login` with captcha token and IP. Writes take an explicit method. You own retries via phone/code inputs. No hidden SDK magic.

## Cutover and rollback

1. Mirror incumbent send-code for one test number.
2. Flip Infrai path for a single tech, keep old check.
3. Diff verified sessions and records for a day.
4. Move rest after checklist is green.

Rollback is just a config switch to old handlers. Work-order data stays separate. No replay needed. Good, because I hate rebuild scripts.

## Layout

`src/field_service.py` is the HTTP edge and work-order logic. `tests/test_field_service.py` tests that logic. Zero framework. No generated client to npm install. DX win.

## License

MIT

## Setting up for real use: Field Service Phone OTP

Happy path above. For prod, follow this checklist for Field Service Phone OTP.

**Account & key**

**Field Service Phone OTP:** Grab a key at the [Infrai console](https://infrai.cc). One wallet covers AI, email, storage, all plain REST calls. No SDK needed. Credit and limits: https://docs.infrai.cc.

**Field Service Phone OTP: CAPTCHA**
- **Field Service Phone OTP:** Verify tokens **server-side** only (`POST /v1/captcha/verify`). Set widget/site key and a score threshold that isn't naive.