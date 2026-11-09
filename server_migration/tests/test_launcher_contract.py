from pathlib import Path
import unittest


class StartServerArgumentForwardingTests(unittest.TestCase):
    def test_study_options_reach_cpu_smoke_and_hpo_runner(self):
        script = Path(__file__).resolve().parents[1] / "start_server.sh"
        content = script.read_text(encoding="utf-8")
        self.assertIn('one_click_v11.py --mode smoke "$@"', content)
        self.assertIn('one_click_v11.py --mode run "$@"', content)


class WindowsCpuProfileTests(unittest.TestCase):
    def test_auto_profile_is_host_specific_and_resource_only(self):
        text = (Path(__file__).resolve().parents[1] / "start_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("7945HX", text)
        self.assertIn('$ramBytes -ge 30GB', text)
        self.assertIn('"--prefetch-workers" = "12"', text)
        self.assertIn('"--prefetch-batches" = "4"', text)
        self.assertIn('"--worker-peak-cache" = "64"', text)
        self.assertIn('"--native-threads" = "1"', text)
        self.assertIn('"--prefetch-workers" = "2"', text)  # unknown hosts
        self.assertIn('$provided -notcontains [string]$flag', text)  # explicit overrides
        self.assertIn('$availableGiB -lt 14', text)  # alert for pressure; don't mutate HPO contract
        self.assertIn('one_click_v11.py", "--mode", "plan"', text)
        self.assertIn('one_click_v11.py", "--mode", "run"', text)


if __name__ == "__main__":
    unittest.main()
