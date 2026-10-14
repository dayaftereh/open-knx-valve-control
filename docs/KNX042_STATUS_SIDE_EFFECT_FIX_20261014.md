# KNX042: STATUS-Befehl hat den M1-Test vorzeitig gestoppt

**14.10.2026 – Softwarefehler reproduziert und im PC-Host korrigiert. Elektrische M1-/LED-Funktion weiterhin nicht nachgewiesen.**

## Ursache

Im bisherigen `tools/knx042_motor_led_control.py` wurde im `finally`-Block selbst nach einer rein lesenden `STATUS`-Abfrage ein zusätzliches `STOP` gesendet, solange `hold_confirmed` im aktuellen Prozess `False` war. Das Flag wurde nur bei `hold` gesetzt, nicht bei `status`. Eine erfolgreich beantwortete `STATUS`-Abfrage beendete daher die vorherige HOLD-Ansteuerung.

**Konkreter Retest nach dem Umlöten:**

- 16:56:40 MESZ: `ARM LEDS_ONLY` und `HOLD M1 F 180s` vom Controller quittiert.
- 16:56:54 MESZ: `STATUS` meldete `armed=0 active=1`. Anschließend versendete das alte Hostskript bei Verbindungsabbau `STOP` samt Flush.
- Der M1-/OPEN-Signaltest wurde damit sehr wahrscheinlich schon nach ungefähr 14 Sekunden statt nach maximal 180 Sekunden abgeschaltet.
- Der Nutzer sah später weder die M1- noch die OPEN-LED leuchten; die genaue Beobachtungszeit ist unbekannt. Das ist mit dem ungewollten STOP vereinbar und **beweist weder einen falsch eingelöteten LED-Pol noch einen defekten GPIO**.

Diese Nebenwirkung trat auch bei früheren M1-Tests mit zwischenzeitlichem `STATUS` auf. Späteres `active=0` ist kein unabhängiger Nachweis für das 180-Sekunden-Auto-Stop.

## Softwarekorrektur und Nachweis

Der Host sendet ein Cleanup-`STOP` jetzt nur noch bei motorverändernden Aktionen (`pulse` und nicht erfolgreich bestätigtem `hold`). Ein `status` bleibt read-only, `stop` sendet nur ein einziges STOP.

Neues Regressionstest-Modul: `tools/test_knx042_status_read_only.py` mit simuliertem seriellen Gerät. Vor Korrektur schlugen 2 von 3 Tests fehl (Folgebefehle `STATUS, STOP` und `STOP, STOP`). Nach Korrektur bestanden **alle 10 KNX042-Tests** (7 bestehende, 3 neue); ASH-Workflow 30/30 PASS.

Auf dem RP2040 wurde **keine** Firmware verändert, es gab **keine** weitere GPIO-Ansteuerung, **keine** KNX-Aktivierung und **keinen** GitHub-Push.

## Nächster sinnvoller Test

Nur nach erneutem Auftrag bei physisch abgezogenem KNX-Bus, USB-only und ohne Motoren: Einen befristeten `HOLD M1 F` starten; `STATUS` jetzt ohne Seiteneffekt abfragen; die LEDs frühzeitig beobachten. Ein zusätzlicher gemessener Pegel an GPIO10/M1_EN sowie GPIO18/IN_1 mit geeignetem Multimeter (ohne Kurzschluss der Pins) ist der belastbarere elektrische Nachweis. Die 180 Sekunden bleiben ein Softwarelimit, keine hardwareseitige STO-Funktion.
