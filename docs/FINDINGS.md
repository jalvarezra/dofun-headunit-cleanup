# Findings

Everything here was measured on **one unit** over ADB on 2026-11-01. Other units and firmware may
differ. We saw where connections go, not what they carry.

## The unit

| | Settings screen | Measured |
|---|---|---|
| Android | 14 | **10** (SDK 29, security patch 2021-01-05) |
| RAM | 4 GB | **about 2 GB** (estimate) |
| Storage | 64 GB | 62.5 GB eMMC, 53 GB in `/data` |

- Chip: Allwinner A133 (`sun50iw10p1`), `product:ceres_b6`, 1280x800, no root.
- Firmware strings: MCU `T13.1.1-100-301-A6939D-250524(6)`, system `V13.1.1_20250901.101006_OS-EN`,
  boot `800x1280_M8_SAT935_90_0_20231117`.
- The RAM figure: `persist.meminfo.totalfake=40` exists, `/proc/meminfo` reports 4 GB, and
  `dumpsys meminfo` leaves about 2.1 GB of "Lost RAM" unexplained.
- Vendor car apps live in a separate read-only partition, `/system_tw`. They are signed with the
  vendor's own platform key (`O=TW`, SHA-1 `40:9D:30:5D:…`), not the public AOSP test key.

## Connections

| Destination | Owner | What stopped it |
|---|---|---|
| `47.236.26.231:1883`, later `47.236.251.111:1883` (Alibaba Cloud) | `uid 1000` | Disabling `com.tw.core`. The address changes between boots, so blocking one IP is not enough |
| `8.214.2.205:80` | `uid 1000` | Disabling `com.tw.coreservice`, as far as we can tell: 5 minutes with none after a reboot |
| `8.214.2.205:80`, `119.23.218.48:80` | `com.dofun.variety` (launcher) | Removing the launcher for the user |

After all of this, 4 minutes of measurement after a reboot showed no connections to those
destinations. Google and Spotify connections remain, as expected with those apps installed.

`com.tw.core` also kept a CSV of every installed app with its version at
`/sdcard/Android/data/com.tw.core/cache/apk.df`. We did not confirm whether it was sent.

## Malware reported through the same updater

Kaspersky reported on 2026-08-21 that `com.tw.core` (TWCore) on DoFun head units took update orders
over MQTT from a `cardoor.cn` broker, and in every case they observed, it was what installed the
JarService malware (ad fraud and a residential proxy, attributed to the MoYu Group). They describe
TWCore as a legitimate updater that was abused, and say the vendor reportedly fixed the issue.
Read the original: [First Android malware targeting automotive head units](https://securelist.com/android-head-unit-malware/121106/).

On this unit, `tools/headunit.py check` finds none of their indicators. Its TWCore
(`V7.3.0.240119`) does not match the three TWCore hashes they list. That does not prove the unit was
never infected.

## What memory did

| | Before | After |
|---|---|---|
| Used RAM | 1.42 GB | 0.96 GB |
| Free RAM | 0.68 GB | 1.09 GB |
| Launcher | 128-157 MB | 21-28 MB |

Not a controlled comparison: Maps was open in the "before" measurement.

## Behaviour worth knowing

- **Removing `com.dofun.variety`:** `pm disable-user` did not last; it came back enabled after a
  reboot. `pm uninstall -k --user 0` did last through a reboot.
- **Key off is sleep, not power off:** the MCU sends `what=202 arg1=1`, `com.tw.service` turns on
  airplane mode, and the unit sleeps. Uptime keeps counting across it. Sleep current was not measured.
- **Do not reboot over ADB with the key out.** After that, the unit stayed on with the car off, and
  a full key cycle put it back to normal. This is the likely cause, not a confirmed one, and it can
  drain the battery.
- **ADB prompt disappearing:** the authorization prompt closed quickly here. The `adb` server
  reconnects by itself, which we suspect dismisses it. Run `adb kill-server` before trying again,
  and choose "Always allow"; the key then survives a reboot.
- **ADB port:** this unit listens on `5100`, not `5555`, and announces itself over mDNS. Try
  `adb mdns services`.
- **Vendor launcher features you lose:** the radio and music card on the home screen, Maps in a
  floating window, themes, and its notification access.

## Not tested

- Steering controls beyond the owner's check, phone calls over a long drive, or other firmware.
- What happens after an over-the-air update or a factory reset. Assume they can undo all of this,
  and run `check` again afterwards.
- Long-term battery use while asleep.
