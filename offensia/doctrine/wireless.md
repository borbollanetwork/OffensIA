# OffensIA Doctrine — Wireless & Radio

Applies to Wi-Fi, Bluetooth/BLE, NFC/RFID, and other RF where it is in scope.
Wireless testing is physically local and legally sensitive: only interact with
networks/devices the engagement authorizes, minimize disruption, and never touch
third-party or bystander traffic. Prefer capture-and-validate over active
disruption.

## What to look for
- **Wi-Fi**: weak/legacy encryption (WEP/WPA-TKIP), WPA2/WPA3 handshake capture and
  offline analysis of authorized creds, PMKID exposure, WPS weaknesses, rogue/evil-twin
  and management-frame handling, client probe leakage, guest/segmentation gaps.
- **Enterprise Wi-Fi (802.1X/EAP)**: certificate validation on clients, credential
  relay, misconfigured EAP methods.
- **Bluetooth/BLE**: pairing/bonding weaknesses, unauthenticated GATT characteristics,
  static keys, replay of commands, MITM during pairing.
- **NFC/RFID**: cloneable/predictable tags, weak card auth, replayable access tokens.
- **Generic RF**: unauthenticated or replayable control signals (map device findings
  into `iot.md`).

## When it applies / preconditions
- Requires physical proximity and explicit authorization for the specific SSIDs /
  devices / frequencies. A confirmed finding requires a reproduction against the
  authorized target with a negative control (e.g. a correctly configured client
  rejects the evil twin), not merely a captured frame.

## Evidence required
- The capture/artifact tied to the authorized target, the demonstrated effect
  (association, decryption of *authorized* traffic, command replay), and the negative
  control. Sanitize and scope every capture to the engagement's own assets.

## Refuting false positives
A visible SSID or a captured handshake is OBSERVATION, not a finding. A legacy cipher
advertised is HARDENING unless exploited within scope. Client-side protections that
actually reject the attack make it FALSE_POSITIVE.

## Chaining
Wireless foothold → internal network reach (`internal.md`); or cloned access token →
physical/logical access. Record each hop and the compensating controls (segmentation,
NAC, 802.1X) that would break the chain.
