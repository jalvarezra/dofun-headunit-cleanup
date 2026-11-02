# DoFun head unit cleanup

Tools for owners of Chinese Android car radios built on the DoFun/TS platform (packages named
`com.tw.*` and `com.dofun.*`) who are comfortable with ADB:

- **`tools/headunit.py check`**: read-only report of what your radio really is, the state of its
  vendor apps, and a check against malware indicators published by Kaspersky.
- **`lists/disable.txt`**: vendor apps with telemetry or remote-install ability, to disable.
- **`launcher/`**: a minimal home screen with no permissions, using 21-28 MB instead of 128-157 MB.

[Español](README.es.md) · [What we measured](docs/FINDINGS.md)

> [!WARNING]
> Tested on **one unit**. This can break features on yours, including the **reverse camera**. Work
> parked, change one thing at a time, and test the camera and audio after each. You lose the
> vendor's over-the-air updates. No warranty; see the [license](LICENSE).

## Why

Kaspersky [reported in August 2026](https://securelist.com/android-head-unit-malware/121106/) that
the updater on DoFun units, `com.tw.core`, was used to install malware. On our unit, that same app
held an open connection to Alibaba Cloud on port 1883, and the launcher connected out over plain
HTTP. Our unit also claims Android 14 and 4 GB of RAM, and really has Android 10 and about 2 GB.
Details and limits are in [FINDINGS](docs/FINDINGS.md).

## Requirements

Python 3 and [Android platform-tools](https://developer.android.com/tools/releases/platform-tools).
No root. To build the launcher: a JDK and the Android SDK.

## 1. Connect

Turn on USB or wireless debugging in Developer options. Then find the radio; it may not use port
5555:

```bash
adb mdns services
adb connect <radio-ip>:<port>
```

If the prompt on the radio closes too fast, run `adb kill-server` and connect again. Choose
**Always allow**.

## 2. Check

Read-only:

```bash
python3 tools/headunit.py check <radio-ip>:<port>
```

"No indicators found" does not prove the unit is clean. Exit code `2` means something matched.

## 3. Disable the apps

Asks before each one. Test the camera and audio in between:

```bash
python3 tools/headunit.py apply <radio-ip>:<port> --dry-run
python3 tools/headunit.py apply <radio-ip>:<port>
```

To undo:

```bash
python3 tools/headunit.py revert <radio-ip>:<port>
```

## 4. Replace the launcher (optional)

Edit `SHORTCUTS` in `launcher/src/headunit/launcher/Home.java` if your apps differ. The layout is
for landscape screens only.

```bash
launcher/build.sh
adb -s <radio-ip>:<port> install -r launcher/build/launcher.apk
adb -s <radio-ip>:<port> shell cmd package set-home-activity headunit.launcher/.Home
```

Use it for a while first. Then remove the vendor launcher, because disabling it did not last through
a reboot on our unit. The package stays on the system:

```bash
adb -s <radio-ip>:<port> shell pm uninstall -k --user 0 com.dofun.variety
```

To go back:

```bash
adb -s <radio-ip>:<port> shell cmd package install-existing com.dofun.variety
adb -s <radio-ip>:<port> shell cmd package set-home-activity com.dofun.variety/com.dofun.overseasvariety.Launcher
```

## Things to watch

- **Do not reboot over ADB with the key out.** Our unit then stayed on with the car off, which can
  drain the battery. Cycling the key fixed it.
- **After a factory reset or firmware update,** run `check` again: the apps may be back.
- **Telemetry may exist in apps not listed here.** This list only covers what we measured.

## Help wanted

Reports from other units are the most useful contribution: chip, firmware strings and what `check`
printed, with anything personal removed. A custom ROM is not part of this project today. If that is
what you want, look at [LibreHU](https://librehu.github.io/), which replaces this kind of software
on a different chip.

## Credits and license

Malware indicators in `iocs/` are from Kaspersky's report. Not affiliated with DoFun or Kaspersky.
Code under the [MIT license](LICENSE).
