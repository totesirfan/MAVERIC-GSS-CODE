import re
import unittest
from dataclasses import dataclass
from pathlib import Path

from mav_gss_lib.platform.spec import DeclarativeWalker, parse_yaml


_FORBIDDEN = ("eps", "gnc", "nvg", "mtq", "tlm_beacon")


@dataclass(frozen=True, slots=True)
class _Pkt:
    args_raw: bytes
    header: dict


SPEC_ROOT = Path("mav_gss_lib/platform/spec")


def _read(rel: str) -> str:
    return (SPEC_ROOT / rel).read_text(encoding="utf-8")


class TestWalkerGenericityGrep(unittest.TestCase):
    def test_runtime_has_no_maveric_identifiers(self):
        text = _read("runtime.py").lower()
        for needle in _FORBIDDEN:
            # Look for word-boundary matches to avoid false positives in comments
            # like "eps" appearing inside an unrelated word.
            self.assertFalse(
                re.search(rf"\b{needle}\b", text),
                f"runtime.py mentions {needle!r} — must stay mission-agnostic",
            )

    def test_yaml_parse_has_no_maveric_identifiers(self):
        text = _read("yaml_parse.py").lower()
        for needle in _FORBIDDEN:
            self.assertFalse(
                re.search(rf"\b{needle}\b", text),
                f"yaml_parse.py mentions {needle!r}",
            )


FIXTURES = Path(__file__).parent / "fixtures" / "spec"


def _key_of(name: str) -> str:
    return name.split(".", 1)[1] if "." in name else name


class TestWalkerExecutionGenericity(unittest.TestCase):
    def test_echo_v2_decodes_through_walker(self):
        m = parse_yaml(FIXTURES / "echo_v2_mission.yml", plugins={})
        walker = DeclarativeWalker(m, plugins={})
        pkt = _Pkt(args_raw=b"hello", header={"cmd_id": "echo", "ptype": "RES"})
        updates = list(walker.extract(pkt, now_ms=0))
        self.assertEqual(len(updates), 1)
        # ParamUpdate.name is qualified with the container/parameter group.
        self.assertTrue(updates[0].name.startswith("echo."))

    def test_balloon_v2_decodes_through_walker(self):
        m = parse_yaml(FIXTURES / "balloon_v2_mission.yml", plugins={})
        walker = DeclarativeWalker(m, plugins={})
        pkt = _Pkt(args_raw=b"42 1013", header={"cmd_id": "telemetry", "ptype": "TLM"})
        updates = list(walker.extract(pkt, now_ms=0))
        self.assertEqual({_key_of(u.name) for u in updates}, {"altitude_m", "pressure_hpa"})


if __name__ == "__main__":
    unittest.main()
