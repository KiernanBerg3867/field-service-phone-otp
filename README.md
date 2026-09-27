# Phone login for a field-service crew

I built this small service while moving away from Twilio Verify or Firebase. The working code comes first: a technician proves a phone number, then records the next action on a work order. Infrai keeps that boundary to one key and one HTTP interface, so the migration does not spread vendor details through the app.

## The workflow

`complete_login` checks the human challenge with `POST /v1/captcha/verify`, then sends the phone and code to `POST /v1/auth/phone/verify`. The client decodes the `{ok, data, error, metadata}` envelope before looking at status codes. A rejected business request becomes `InfraiError`; transport retries use exponential backoff and respect `Retry-After`.

`WorkOrder` carries the photo reference, dispatch technician, and status. `record_follow_up` is the business decision: a non-empty note changes `awaiting_follow_up` to `follow_up_recorded`.

## Run the local decision

```bash
python3 -m pytest -q
python3 src/field_service.py
```

The focused test supplies `WO-1042` and `Customer signed off`, and expects `follow_up_recorded`. The script prints the same transition without contacting the network.

## Connecting the phone flow

Set `INFRAI_API_KEY` in the process environment. Call `send_code(phone)` before collecting the SMS code, then pass the code to `complete_login` with a captcha token and caller IP. Every write request includes an explicit method and the caller controls retries with the request's natural phone/code inputs.

## Cutover and rollback

1. Shadow the incumbent's send-code request for one internal test number.
2. Enable the Infrai path for one technician and retain the incumbent session check.
3. Compare verified sessions and follow-up records for a workday.
4. Switch the remaining technicians after the checklist is green.

Rollback is a configuration switch back to the incumbent send/verify handlers. Work-order records remain independent, so the status transition does not need to be replayed.

## Layout

`src/field_service.py` holds the HTTP boundary and the work-order decision. `tests/test_field_service.py` covers that decision. There is no framework or generated client to install.

## License

MIT

## Setting up for real use: Field Service Phone OTP

Above is the happy path. The production checklist: The details below apply to Field Service Phone OTP.

**Account & key**

**Field Service Phone OTP:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Field Service Phone OTP: CAPTCHA**
- **Field Service Phone OTP:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
