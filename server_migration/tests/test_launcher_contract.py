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
        self.assertIn('$resolvedProfile = "conservative"', text)
        self.assertNotIn('minimal2', text)
        self.assertNotIn('$ramBytes -lt 30GB', text)
        self.assertIn('"performance12"', text)  # cuifa preliminary baseline
        self.assertIn('"aggressive16"', text)  # optional unverified CPU scale
        self.assertIn('"--prefetch-workers" = "16"', text)
        self.assertIn('"--worker-peak-cache" = "32"', text)
        self.assertIn('"--prefetch-workers" = "12"', text)
        self.assertIn('"--prefetch-batches" = "4"', text)
        self.assertIn('"--worker-peak-cache" = "64"', text)
        self.assertIn('"--native-threads" = "1"', text)
        self.assertNotIn('"--prefetch-workers" = "2"', text)
        self.assertIn('if ($resolvedProfile -in @("conservative", "ryzen7945hx", "performance12"))', text)
        self.assertIn('$provided -notcontains [string]$flag', text)  # explicit overrides
        self.assertIn('$availableGiB -lt $thresholdGiB', text)
        self.assertIn('if ($resolvedProfile -eq "aggressive16") { 18 } else { 14 }', text)
        self.assertIn('$Mode -eq "hpo" -and $resolvedProfile -eq "aggressive16"', text)
        self.assertIn('one_click_v11.py", "--mode", "plan"', text)
        self.assertIn('one_click_v11.py", "--mode", "run"', text)


if __name__ == "__main__":
    unittest.main()
