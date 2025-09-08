import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import os

from cryptography import x509
from cryptography.x509.oid import NameOID

from arpx import certs as cert_utils

class TestCerts(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_self_signed_cert(self):
        """Test the generation of a self-signed certificate."""
        cert_path, key_path = cert_utils.generate_self_signed_cert(
            self.output_dir,
            common_name="test.lan",
            sans=["test.lan", "192.168.1.100"]
        )

        self.assertTrue(cert_path.exists())
        self.assertTrue(key_path.exists())

        # Check cert content
        with open(cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        
        self.assertEqual(
            cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
            "test.lan"
        )

        sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        dns_sans = sans.get_values_for_type(x509.DNSName)
        ip_sans = sans.get_values_for_type(x509.IPAddress)

        self.assertIn("test.lan", dns_sans)
        self.assertEqual(str(ip_sans[0]), "192.168.1.100")

    @patch('subprocess.run')
    def test_generate_mkcert_cert_success(self, mock_run):
        """Test successful generation of a certificate using mkcert."""
        # Mock `command -v mkcert` and `mkcert ...` calls
        mock_run.return_value = MagicMock(returncode=0)

        # Create dummy files to simulate mkcert's output
        (self.output_dir / 'cert.pem').touch()
        (self.output_dir / 'key.pem').touch()

        cert_path, key_path = cert_utils.generate_mkcert_cert(self.output_dir, ["test.dev"])

        self.assertTrue(cert_path.exists())
        self.assertTrue(key_path.exists())
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_generate_mkcert_not_installed(self, mock_run):
        """Test that mkcert generation fails if the tool is not installed."""
        # Mock `command -v mkcert` to fail
        mock_run.return_value = MagicMock(returncode=1)
        with self.assertRaisesRegex(RuntimeError, "mkcert is not installed"):
            cert_utils.generate_mkcert_cert(self.output_dir, ["test.dev"])

if __name__ == '__main__':
    unittest.main()
