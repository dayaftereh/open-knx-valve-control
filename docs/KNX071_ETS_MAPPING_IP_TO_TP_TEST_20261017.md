# KNX071 – ETS metadata import and one controlled KNX/IP → TP1 RX validation

**Date:** 2026-10-17. **Status: PASS.** Hardware receiver stays RX-only.

## ETS mapping

An existing local ETS v23 `.knxproj` was parsed read-only; it contained:
- **201** defined group addresses and DPT metadata across seven functional main groups;
- **57** KNX device instances;
- **371** associations from ETS group addresses to device communication objects.

The standalone, standard-library-only extractor is `tools/knx071_ets_group_map.py`.
The complete room/zone names, device physical addresses, device identifiers, original
ETS source path and annotated house telegrams are **intentionally NOT committed to
this PUBLIC repository**. They are stored in the user's separate private LLO Home
Downloads evidence directory under `KNX071_Private_ETS_20261017`.

`tools/knx071_annotate_tp.py` enriches KNX070 physical telegrams with ETS
names, datapoint types and decoded DPT9 temperature/humidity values. All private
result CSV/JSON is kept outside the repo.

## Controlled one-frame KNX/IP test

`tools/knx071_ip_test_once.py`:
- requires an explicit `--execute` flag (otherwise print-only dry-run);
- checks the source ETS file against its saved SHA-256 inventory to reject stale exports;
- refuses a test GA already defined in ETS or a main group already present in ETS;
- sends exactly **one** 1-bit GroupValueWrite using the existing KNX/IP *tunneling*
  interface, not the prototype board's KNX_TX pin;
- disconnects the IP tunnel after the test.

**Live result:**
- Receiver was armed via USB serial `ARM LISTEN_ONLY` + `START LISTEN` on RP2040 GPIO1.
- One specifically chosen ETS-unallocated, non-production test group address
  was written once by KNX/IP.
- The physical receiver independently decoded **exactly one** corresponding
  valid TP1 frame at the correct time, with matching destination and bit value.
- That frame passed start/stop, even parity, checksum and link ACK checks.
- Full monitoring interval: **26 decoded telegrams; 26/26 valid**,
  **4,124 firmware RX edges** and **0 dropped**.
- The receiver was stopped with `STOP`, and both serial and IP resources were released.
- The other 25 telegrams in this run mapped to existing ETS group names and
  DPTs, with plausible engineering-unit values.

This verifies the complete receive chain **KNX/IP sender → KNX TP bus →
STKNX U9 → RP2040 GPIO1 → USB serial edge log → TP1 and ETS-aware decoder**.

The IP sender's own receive callback did not need to echo its outgoing frame:
the prototype's independently decoded TP1 frame is the decisive evidence.

## Reproduce

Use an isolated Python interpreter with `xknx==4.0.0` for the optional IP sender.
The ETS importer, annotator, TP1 decoder and unit tests use the Python standard library.
All gateway IPs and project file paths must be supplied explicitly at runtime.

```text
python tools/knx071_ets_group_map.py --project <private.knxproj> --csv <private.csv> --json <private.json> --devices-csv <private_devices.csv>
python tools/knx071_annotate_tp.py --tp-json <tp_decode.json> --ets-json <private.json> --csv <private_annotated.csv>
python tools/knx071_ip_test_once.py --map <private.json> --gateway <ip> --local-ip <ip> --group <unused_ga> --output <private_result.json>
```

The final command is **dry-run only**. The explicit `--execute` flag is required
for even one real KNX telegram, and ETS absence cannot rule out separately
programmed subscribers or IP automation. No automatic repeated sends.

Tests: `python -m unittest discover -s tests -p "test_knx07*.py" -v`
(**16/16 tests passed**: KNX070 + KNX071).

## Hardware safety gates remain OPEN

Historical **U11 overheating**, **D1 bypass/backfeed** and GPIO0 TX idle on
RP2040 reset/BOOTSEL remain unresolved. Success receiving an IP-originated
telegram **does not authorize prototype-originated KNX transmission** or
production controller firmware deployment.

No GitHub push was performed.
