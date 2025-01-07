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

