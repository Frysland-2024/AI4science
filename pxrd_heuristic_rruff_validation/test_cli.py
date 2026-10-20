from unittest.mock import patch
from pxrd_heuristic_rruff_validation import __main__ as cli

def test_dispatch_preserves_failed_child_exit():
    with patch.object(cli.subprocess, 'run') as run:
        run.return_value.returncode = 7
        assert cli.dispatch('verify', 'e2') == 7
        assert run.call_args.kwargs['timeout'] == 10800
        assert run.call_args.args[0][-1] == 'pxrd_heuristic_rruff_validation.e2_verify'
