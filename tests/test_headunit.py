import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import headunit  # noqa: E402

IOCS = json.loads(headunit.IOC_FILE.read_text())
BAD_MD5 = IOCS["md5"][0].lower()


class FakeAdb:
    """Answers shell commands by prefix and records them."""

    def __init__(self, answers):
        self.answers = answers
        self.commands = []

    def shell(self, command, timeout=120):
        self.commands.append(command)
        for prefix, answer in self.answers.items():
            if command.startswith(prefix):
                return answer
        return ""


def clean_answers():
    return {
        "pm list packages -f -u": "package:/data/app/com.good-abc==/base.apk=com.good\n",
        "pm list packages -e": "package:com.good\npackage:com.tw.core\n",
        "pm list packages -d": "",
        "pm list packages -U": "package:com.good uid:10100\n",
        "md5sum": f"{'0' * 32}  /data/app/com.good-abc==/base.apk\n",
    }


class Parsers(unittest.TestCase):
    def test_package_path_keeps_equals_signs(self):
        # Paths under /data/app end in "==". Splitting on the first "=" silently skips those APKs.
        paths = headunit.parse_package_paths("package:/data/app/com.x-Ab12==/base.apk=com.x\n")
        self.assertEqual(paths, {"/data/app/com.x-Ab12==/base.apk": "com.x"})

    def test_connections_read_ipv4_and_mapped_ipv6(self):
        text = (
            "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid\n"
            "   0: 0A01A8C0:C000 C9F3D990:0050 01 00000000:00000000 00:00000000 00000000 10122\n"
            "   1: 00000000000000000000000000000000:0000 "
            "0000000000000000FFFF000001020304:075B 01 00000000:00000000 00:00000000 00000000 1000\n"
        )
        self.assertEqual(
            headunit.parse_connections(text),
            [("144.217.243.201", 80, "10122"), ("4.3.2.1", 1883, "1000")],
        )

    def test_connections_skip_listeners_and_loopback(self):
        text = (
            "   0: 00000000:13EC 00000000:0000 0A 00000000:00000000 00:00000000 00000000 2000\n"
            "   1: 0100007F:13EC 0100007F:C000 01 00000000:00000000 00:00000000 00000000 2000\n"
        )
        self.assertEqual(headunit.parse_connections(text), [])

    def test_list_ignores_comments(self):
        packages = headunit.read_list(headunit.DISABLE_LIST)
        self.assertIn("com.tw.core", packages)
        self.assertFalse(any("#" in package or " " in package for package in packages))


class Check(unittest.TestCase):
    def test_clean_device_has_no_findings(self):
        self.assertEqual(headunit.check(FakeAdb(clean_answers()), IOCS, ["com.tw.core"]), [])

    def test_check_never_changes_the_device(self):
        adb = FakeAdb(clean_answers())
        headunit.check(adb, IOCS, ["com.tw.core"])
        for command in adb.commands:
            self.assertNotRegex(command, r"disable|enable |uninstall|install|rm |reboot|settings put")

    def test_finds_named_package(self):
        answers = clean_answers()
        answers["pm list packages -f -u"] += "package:/data/app/j-a==/base.apk=com.tw.jar1\n"
        findings = headunit.check(FakeAdb(answers), IOCS, [])
        self.assertTrue(any("com.tw.jar1" in finding for finding in findings))

    def test_finds_hash_of_apk_under_data_app(self):
        answers = clean_answers()
        answers["md5sum"] = f"{BAD_MD5}  /data/app/com.good-abc==/base.apk\n"
        findings = headunit.check(FakeAdb(answers), IOCS, [])
        self.assertTrue(any(BAD_MD5 in finding for finding in findings))

    def test_finds_connection_to_listed_ip(self):
        answers = clean_answers()
        answers["cat /proc/net"] = (
            "   0: 0A01A8C0:C000 C9F3D990:0050 01 00000000:00000000 00:00000000 00000000 10100\n"
        )
        findings = headunit.check(FakeAdb(answers), IOCS, [])
        self.assertTrue(any("144.217.243.201" in finding for finding in findings))

    def test_finds_loader_thread_in_logs(self):
        answers = clean_answers()
        answers["logcat -d"] = "I/x: started mosdk-host-loader\n"
        findings = headunit.check(FakeAdb(answers), IOCS, [])
        self.assertTrue(any("mosdk-host-loader" in finding for finding in findings))


class Apply(unittest.TestCase):
    def test_dry_run_changes_nothing(self):
        adb = FakeAdb(clean_answers())
        headunit.apply_list(adb, ["com.tw.core"], dry_run=True)
        self.assertFalse(any("disable-user" in command for command in adb.commands))

    def test_apply_only_touches_listed_enabled_packages(self):
        adb = FakeAdb(clean_answers())
        headunit.apply_list(adb, ["com.tw.core", "com.absent"], assume_yes=True)
        disabled = [command for command in adb.commands if "disable-user" in command]
        self.assertEqual(disabled, ["pm disable-user --user 0 com.tw.core"])

    def test_revert_enables_only_disabled_packages(self):
        answers = clean_answers()
        answers["pm list packages -d"] = "package:com.tw.core\n"
        adb = FakeAdb(answers)
        headunit.revert_list(adb, ["com.tw.core", "com.other"])
        enabled = [command for command in adb.commands if command.startswith("pm enable")]
        self.assertEqual(enabled, ["pm enable com.tw.core"])


if __name__ == "__main__":
    unittest.main()
