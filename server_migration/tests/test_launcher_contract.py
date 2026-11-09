from pathlib import Path
import unittest


class StartServerArgumentForwardingTests(unittest.TestCase):
    def test_study_options_reach_cpu_smoke_and_hpo_runner(self):
        script = Path(__file__).resolve().parents[1] / "start_server.sh"
        content = script.read_text(encoding="utf-8")
        self.assertIn('one_click_v11.py --mode smoke "$@"', content)
        self.assertIn('one_click_v11.py --mode run "$@"', content)


if __name__ == "__main__":
    unittest.main()
