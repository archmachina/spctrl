
import sys
import subprocess
import pytest
import spctrl

class TestCli:
    def test_1(self):
        sys.argv = ["spctrl", "--help"]

        with pytest.raises(SystemExit):
            res = spctrl.cli.main()

    def test_2(self):
        # Test running the entrypoint
        ret = subprocess.call(["/work/bin/entrypoint", "--help"])

        assert ret == 0

