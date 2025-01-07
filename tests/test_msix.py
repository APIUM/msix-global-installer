import math
import pytest
import pathlib
from src import msix

class TestMsix:
    """Class to test MSIX functions."""

    def test_get_msix_metadata(self):
        """Test we get the required metadata from a given test file."""
        path = pathlib.Path("tests/TestMsixPackage.msix")
        data = msix.get_msix_metadata(path)
        assert data.package_name == 'MyEmployees'
        assert data.version == '9.0.0.0'
        assert data.publisher == 'Contoso Corporation'

    def test_install(self):
        """Test we can install with a subprocess."""
        path = pathlib.Path("tests/TestMsixPackage.msix")
        msix.install_msix(path)

    def test_count_percentage(self):
        """Test we can count the progress."""
        test_start = r"    [                                                                    ]      \r\n"
        test_progress1 = r'    [oooo                                                                ]      \r\n'
        test_progress2 = r'    [ooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo   ]      \r\n'
        test_complete = r'    [oooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo]      \r\n'
        assert msix.count_progress(test_start, 68) == 0.0
        assert msix.count_progress(test_progress1, 68) == math.ceil(4/68*100)
        assert msix.count_progress(test_progress2, 68) == 96
        assert msix.count_progress(test_complete, 68) == 100.0
