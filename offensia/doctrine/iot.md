# OffensIA Doctrine — IoT & Embedded

Applies to connected devices and their firmware, hardware, and companion
services. Three surfaces interact: firmware/software, physical/hardware, and the
cloud/mobile backend the device trusts. Only test devices and endpoints in scope,
and treat physical access steps as authorized actions on the engagement's own units.

## What to look for
- **Firmware**: extractable images (OTA, flash dumps), hardcoded credentials/keys,
  private keys and certs, debug/backdoor accounts, insecure update mechanism (no
  signature/rollback protection), known-vulnerable components.
- **Services**: exposed telnet/SSH/UART shells, web admin with default creds,
  unauthenticated management endpoints, custom binary services.
- **Hardware**: UART/JTAG/SWD debug ports, SPI/I2C flash readout, glitching surfaces
  — as far as the rules of engagement allow.
- **Radio/protocols**: BLE, Zigbee, Z-Wave, LoRa, proprietary RF — pairing, auth,
  and replay (coordinate with `wireless.md`).
- **Trust with backend**: device identity, provisioning secrets, MQTT/CoAP auth,
  and whether the cloud enforces what the device assumes (bridge into `cloud.md`).

## When it applies / preconditions
- Firmware analysis requires an authorized image (dump or vendor OTA). A confirmed
  finding requires demonstrating the effect on an in-scope device or its backend,
  not just spotting a string in the image.

## Evidence required
- Extracted secret: the firmware offset/file plus proof it authenticates something.
- Insecure update: a crafted (inert, test-signed) image accepted by the device, with
  a negative control showing a tampered image should be rejected.
- Exposed service: the connection/auth bypass and its observed effect.

## Refuting false positives
A key in firmware is INFORMATIONAL until shown to be used and reachable. A debug
port present is HARDENING unless access yields a real capability. Vendor
compensating controls (secure boot, signed updates that actually verify) turn
scary-looking findings into FALSE_POSITIVE.

## Chaining
Firmware key → backend/device auth → fleet-wide access; or debug port → firmware
dump → key → cloud identity. Record each hop with evidence in the attack graph.
