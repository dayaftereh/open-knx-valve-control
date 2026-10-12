# ETS6 product-data baseline and generation audit

**Historische Baseline (2026-10-09):** Diese Bestandsaufnahme beschreibt die Produkt-XML **vor** KNX015. Seit 12.10.2026 dokumentiert [KNX015_TEMPERATURE_PUBLISH.md](KNX015_TEMPERATURE_PUBLISH.md) die abgeleitete ApplicationVersion 2 mit zwei neuen Parametern, KO34/35 und Generator-Makrobereinigung. Das fruehere KO-/Parameterinventar bleibt bewusst zur Migrationspruefung erhalten.

**Date:** 2026-10-09

**Sources:** [existing OpenKNX product XML](../assets/open-knx-valve-control.xml), [generated header currently tracked](../include/knxprod.hpp), [OpenKNXproducer PlatformIO script](../assets/open-knx-producer.py), ETS6 detected on LLO Desktop (6.4.1). This is a product-generation review, **not** an ETS6 import or functional KNX telegram test.

## 1. Existing XML - exact inventory (before any restructuring)

The existing XML has application name `open-knx-valve-control`, manufacturer reference `M-00FA`, `ApplicationNumber=55531` (hexadecimal `D8EB`), application version **1**, `MaskVersion=MV-07B0` and minimum ETS version **5.0**. It uses generator placeholders such as `%AID%`, `%ProductId%` and `%MemorySize%`.

| Existing declaration | Present count | Meaning |
| --- | ---: | --- |
| `ParameterType` | 6 | Delay, selection, Yes/No, Open/Close, Percentage, temperature types |
| `Parameter` / `ParameterRef` | 19 / 19 | Two startup settings; Drive1..8Active; Drive1..8ControlLoop; PrePostTemperaturesOutput |
| `ComObject` / `ComObjectRef` | 33 / 33 | Already defined in the XML; not proof of firmware support |
| Dynamic ETS `Channel` | **1** | `Stellmotor 1` only; the other seven are not configured as equivalent dynamic channels |
| Dynamic `ParameterRefRef` / `ComObjectRefRef` | 12 / 12 | Current ETS UI exposes only a subset of declared static objects/parameters |

The `DriveNControlLoop` enumeration contains `Open=0` and `Close=1`. **This is not yet a well-defined ETS choice between temperature regulation and direct 0..100% valve position.**

### Current group object numbering, as declared

| Numbers | KNX XML names | Declared DPT | Intended usage |
| --- | --- | --- | --- |
| 1..8 | `Soll-Temperatur 1` .. `8` | `DPST-9-1` = 9.001 | Temperature setpoint per motor (existing design) |
| 9..16 | `Ist-Temperatur 1` .. `8` | `DPST-9-1` = 9.001 | Actual temperature per motor (existing design) |
| 17..24 | `Stell-Wert 1` .. `8` (some use underscores) | `DPST-5-4` = **5.004** | Valve demand / relative value (existing design) |
| 25..33 | `T0` .. `T8` | `DPST-9-1` = 9.001 | Nine local temperature values |

`assets/Sensor.xml` is a **separate temperature/humidity example**, not an automatic include in the product XML.

## 2. DPT 5.004 versus DPT 5.001 - migration decision required

The intended external bus command is a valve position **0..100%**. These are different, *incompatible without mapping* KNX 1-byte encodings:

| Physical example | DPT 5.001 (Scaling, 0..100%) | DPT 5.004 (Percent U8, 0..255%) |
| --- | --- | --- |
| 50% | raw 128 (`0x80`, approximate) | raw 50 (`0x32`) |
| 100% | raw 255 (`0xFF`) | raw 100 (`0x64`) |

Reference: KNX Association Interworking Datapoint Types, DPT 5.001 and 5.004, https://support.knx.org/hc/tr/article_attachments/15392631105682 (published spec; verify applicable version in ETS). These DPTs must never be treated as interchangeable just because both payloads are one byte.

**Proposed:** use 5.001 for conventional external KNX 0..100% position demand and feedback, and explicitly document any backwards-compatibility conversion if a legacy controller already sends 5.004. Decide this before renumbering or releasing product data. The existing XML remains **unchanged** during this audit.

## 3. Actual local OpenKNXproducer 3.12.2 test

Executable found at `C:\ASH\Tools\OpenKNXproducer-3.12.2\OpenKNXproducer.exe` (in PATH).

- A standalone `check assets\open-knx-valve-control.xml` on the **raw generator template** prints a misleading mixed old/new application-ID warning and says no additional checks can run; it still exits with code **0**. Do not treat exit code 0 of that command as a successful sanity check.
- An isolated `create` run against a **copy** of the XML in `C:\ASH\Workspace\Temp\openknx-ets-audit-20261009` resolves `%AID%` to `M-00FA_A-D8EB-01-0000`, successfully passes its many homogeneity/reference/parameter checks, and generates a ZIP-valid `candidate.knxprod` plus `knxprod.hpp`.
- Generated package: **102,984 bytes**, ZIP integrity check OK, **6 ZIP entries** (including `knx_master.xml`, Catalog, Hardware and application XML), SHA-256 `3db120c6ced4d88a8ba584c3136d16e0761e220e4c0fac9440a437986ae4dfd2`. It is a **test candidate**, not a released KNX product.
- Producer reports **WARN 008**: channel `Stellmotor 1` uses `Number="1"` and may need `Number="%PREFIX%"` in the current producer's module/prefix architecture.
- The newly generated header differs from the tracked `include/knxprod.hpp`: in particular the tracked communication-object macros have empty positions, whereas the test-generated header contains numbers 1..33.
- **Important: macro-name issue.** The generated header contains **42 non-C-identifier Ko-family macro names** (two macro families for 21 hyphenated ComObject names), such as `#define KoSoll-Temperatur_1 1`. In C/C++, a hyphen is not part of an identifier: these directives cannot be used as intended and may cause redefinitions or compiler errors. Before firmware integration, adopt identifier-safe `ComObject Name` values (e.g. `Zone1TargetTemperature`), while keeping user-facing German descriptions in the `Text` attributes.
- The PlatformIO prebuild script `assets/open-knx-producer.py` suppresses `subprocess.CalledProcessError` with `pass`: it can leave a stale generated header without failing the build. Harden this script once the canonical product-generator flow is selected.

**Nothing was imported into ETS6**, no KNX telegrams were sent, and this pass did not overwrite the canonical product XML, header, firmware or schematic. The candidate was generated in the temp directory, not committed.

## 4. Recommended ETS V2 model (design target, not current implementation)

Separate **physical outputs** from **rooms**:

- **8 physical actuator channels**: enable; zone assignment (none or Zone1..Zone8); reversed polarity; calibrated close/open runtimes; endpoint sensing policy; max run timeout; fault and estimated position feedback.
- **Up to 8 logical heating zones**: enable; operating mode `temperature regulation` or `direct 0..100% KNX demand`; temperature source (external KNX sensor or an appropriately installed T0..T8 probe), setpoint, actual temperature, control coefficients/deadband, sensor timeout, frost/failsafe.
- Many motors (e.g. M1, M2, M3) may reference the **same zone**; each member receives the zone demand but moves sequentially, one at a time.
- For zone-based objects, expose `Zone N Soll-Temperatur`, `Zone N Ist-Temperatur` and `Zone N Stellwert` only as appropriate for that zone's selected mode. Give each motor separate position-estimate/calibration/error feedback. Decide number assignments before shipping since group-object renumbering can break existing ETS projects.
- The PCB has nine local sensor inputs for eight motors; the ninth is **not** automatically a room. Clarify actual sensor placement and intended use.
- Explicitly version the new application and migration plan. Do not silently reuse an existing application version after changing parameter layout or communication objects.

See [ETS_AND_CONTROL_CONCEPT.md](ETS_AND_CONTROL_CONCEPT.md) for control-state machines and [PCB_V1_2_AUDIT.md](PCB_V1_2_AUDIT.md) for wiring constraints.

## 5. Gate checklist before a released product

1. Confirm desired DPT 5.001/5.004 interoperability policy and object naming/numbering with one real ETS project.
2. Design a safe per-channel parameter layout and room-to-channel assignment, with sane defaults and limits.
3. Replace unsafe generated C/C++ macro names, regenerate XML/header and verify they compile against the firmware.
4. Make producer generation **fail on errors**, and add repeatable product checks in CI.
5. Generate `.knxprod` in an isolated build, check ZIP/metadata, import it into an **isolated ETS6 test project**, visually verify eight channel pages/zone pages and linkable group objects.
6. Confirm actual KNX programming/download, DPT encode/decode, temperature status and 0..100% control on an electrically qualified target board.
