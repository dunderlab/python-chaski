"""
==========================================================
Certificate Authority Security Infrastructure Test Suite
==========================================================

This module provides a comprehensive test suite for validating the functionality
of the CertificateAuthority class within the Chaski communication framework.
It tests the complete PKI (Public Key Infrastructure) workflow including:

1. Creation and verification of Certificate Authority (CA) certificates
2. Generation of private keys for clients and servers
3. Creation of Certificate Signing Requests (CSRs)
4. Signing of CSRs by the CA
5. Verification of certificate signatures
6. Integration with the Chaski network communication system

The tests ensure secure and reliable TLS/SSL communication can be established
between Chaski nodes by verifying the cryptographic operations and certificate
management functions work correctly.
"""

import os
import sys
import time
import ipaddress
import subprocess

import pytest
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.base import Certificate, CertificateSigningRequest

from chaski.streamer import ChaskiStreamer
from chaski.utils.auto import run_transmission
from chaski.utils.certificate_authority import CertificateAuthority


@pytest.fixture(scope="class")
def setup_ca(request: pytest.FixtureRequest) -> None:
    """
    Setup a Certificate Authority server process for testing.

    This fixture starts the Certificate Authority server script as a separate process
    and ensures it's available for the duration of the test suite. The server provides
    certificate services for the tests, including certificate signing and validation.

    Args:
        request: The pytest fixture request object

    Returns:
        None
    """
    path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(sys.path + [path])

    process_streamer = subprocess.Popen(
        [sys.executable, f"{path}/chaski/scripts/certificate_authority.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    time.sleep(1)  # Allow time for the CA server to start


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_ca")
class TestCertificateAuthority:
    """
    Test suite for the CertificateAuthority class functionality.

    This class contains test cases for validating the security infrastructure provided
    by the CertificateAuthority class, including certificate creation, signing,
    verification, and secure communication establishment.

    Attributes:
        SSL_CERTIFICATES_LOCATION: Directory where test certificates will be stored
        TEST_NAME: Identifier used for naming test certificates
    """

    # Class-level constants
    SSL_CERTIFICATES_LOCATION: str = "ssl_certificates_location"
    TEST_NAME: str = "Test-ID"

    @classmethod
    def setup_class(cls) -> None:
        """
        Set up the test environment for Certificate Authority tests.

        Creates a directory for storing SSL certificates if it doesn't already exist.
        This method runs once before any test in the class is executed.
        """
        if not os.path.exists(cls.SSL_CERTIFICATES_LOCATION):
            os.mkdir(cls.SSL_CERTIFICATES_LOCATION)

    @pytest.fixture
    def certificate_authority(self) -> CertificateAuthority:
        """
        Create and configure a CertificateAuthority instance for testing.

        This fixture instantiates a CertificateAuthority object with predefined
        configurations suitable for testing purposes, including identification,
        network address, certificate storage location, and certificate attributes.

        Returns:
            CertificateAuthority: A configured instance ready for testing
        """
        ca = CertificateAuthority(
            self.TEST_NAME,
            ipaddress.IPv4Address("127.0.0.1"),
            ssl_certificates_location=self.SSL_CERTIFICATES_LOCATION,
            ssl_certificate_attributes={
                "Country Name": "CO",
                "Locality Name": "Manizales",
                "Organization Name": "DunderLab",
                "State or Province Name": "Caldas",
                "Common Name": "Chaski-Confluent",
            },
        )
        return ca

    @pytest.mark.asyncio
    async def test_ca(self, certificate_authority: CertificateAuthority) -> None:
        """
        Test the creation and validation of CA certificate and private key.

        This test verifies that the CertificateAuthority can correctly generate
        a Certificate Authority certificate and private key pair, save them to the
        specified location, and use them for cryptographic operations. It validates
        the key pair by signing and verifying a test message.

        Args:
            certificate_authority: The CertificateAuthority fixture instance

        Raises:
            AssertionError: If certificate paths don't exist or key verification fails
        """
        ca = certificate_authority
        ca.setup_certificate_authority()

        assert os.path.exists(
            ca.ca_certificate_path
        ), "CA certificate path does not exist"
        assert os.path.exists(
            ca.ca_private_key_path
        ), "CA private key path does not exist"

        certificate: Certificate = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.ca_certificate_path), default_backend()
        )

        private_key: rsa.RSAPrivateKey = serialization.load_pem_private_key(
            ca.load_certificate(ca.ca_private_key_path),
            password=None,
            backend=default_backend(),
        )

        public_key = certificate.public_key()

        try:
            message = b"Test message"
            signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
            public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
            assert True, "The private key corresponds to the certificate."
        except Exception as e:
            pytest.fail(
                f"The private key does not correspond to the certificate: {str(e)}"
            )

    @pytest.mark.asyncio
    async def test_csr(self, certificate_authority: CertificateAuthority) -> None:
        """
        Test the generation of private keys and Certificate Signing Requests.

        This test verifies that the CertificateAuthority can correctly generate
        private keys and corresponding Certificate Signing Requests (CSRs) for
        both client and server entities. It validates that the generated keys and
        CSRs have matching cryptographic properties (moduli).

        Args:
            certificate_authority: The CertificateAuthority fixture instance

        Raises:
            AssertionError: If files don't exist or moduli don't match
        """
        ca = certificate_authority
        ca.generate_key_and_csr()

        assert os.path.exists(ca.private_key_paths["client"]), "Client key not found"
        assert os.path.exists(ca.private_key_paths["server"]), "Server key not found"
        assert os.path.exists(ca.certificate_paths["client"]), "Client CSR not found"
        assert os.path.exists(ca.certificate_paths["server"]), "Server CSR not found"

        def key_modulus(key: bytes) -> int:
            """Extract modulus from a private key."""
            private_key: rsa.RSAPrivateKey = serialization.load_pem_private_key(
                key, password=None, backend=default_backend()
            )
            modulus = private_key.private_numbers().public_numbers.n
            return modulus

        def csr_modulus(key: bytes) -> int:
            """Extract modulus from a Certificate Signing Request."""
            csr: CertificateSigningRequest = x509.load_pem_x509_csr(
                key, backend=default_backend()
            )
            public_key = csr.public_key()
            modulus = public_key.public_numbers()
            return modulus.n

        client_key_modulus = key_modulus(
            ca.load_certificate(ca.private_key_paths["client"])
        )
        client_csr_modulus = csr_modulus(
            ca.load_certificate(ca.certificate_paths["client"])
        )
        assert (
            client_key_modulus == client_csr_modulus
        ), "Client key modulus does not match client CSR modulus"

        server_key_modulus = key_modulus(
            ca.load_certificate(ca.private_key_paths["server"])
        )
        server_csr_modulus = csr_modulus(
            ca.load_certificate(ca.certificate_paths["server"])
        )
        assert (
            server_key_modulus == server_csr_modulus
        ), "Server key modulus does not match Server CSR modulus"

    @pytest.mark.asyncio
    async def test_sign(self, certificate_authority: CertificateAuthority) -> None:
        """
        Test the signing of Certificate Signing Requests by the CA.

        This test verifies that the CertificateAuthority can correctly sign
        Certificate Signing Requests (CSRs) and generate valid certificates.
        It loads the CA certificate and private key, then signs client and server
        CSRs, and finally verifies that the resulting certificates have valid
        signatures from the CA.

        Args:
            certificate_authority: The CertificateAuthority fixture instance

        Raises:
            AssertionError: If certificates aren't properly signed by the CA
        """
        ca = certificate_authority

        ca.load_ca(
            ca_key_path=os.path.join(self.SSL_CERTIFICATES_LOCATION, "ca.key.pem"),
            ca_cert_path=os.path.join(self.SSL_CERTIFICATES_LOCATION, "ca.crt.pem"),
        )

        ca.load_key_and_csr(
            private_key_client_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"client_{self.TEST_NAME}.key.pem"
            ),
            certificate_client_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"client_{self.TEST_NAME}.csr.pem"
            ),
            private_key_server_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"server_{self.TEST_NAME}.key.pem"
            ),
            certificate_server_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"server_{self.TEST_NAME}.csr.pem"
            ),
        )

        with open(ca.certificate_signed_paths["client"], "wb") as file:
            file.write(
                ca.sign_csr(
                    ca.load_certificate(ca.certificate_paths["client"]), role="client"
                )
            )

        with open(ca.certificate_signed_paths["server"], "wb") as file:
            file.write(
                ca.sign_csr(
                    ca.load_certificate(ca.certificate_paths["server"]), role="server"
                )
            )

        ca_cert: Certificate = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.ca_certificate_path), default_backend()
        )
        ca_public_key = ca_cert.public_key()

        client_cert: Certificate = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.certificate_signed_paths["client"]),
            default_backend(),
        )
        server_cert: Certificate = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.certificate_signed_paths["server"]),
            default_backend(),
        )

        try:
            ca_public_key.verify(
                client_cert.signature,
                client_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                client_cert.signature_hash_algorithm,
            )
        except Exception as e:
            pytest.fail(f"The client certificate was NOT signed by the CA: {str(e)}")

        try:
            ca_public_key.verify(
                server_cert.signature,
                server_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                server_cert.signature_hash_algorithm,
            )
        except Exception as e:
            pytest.fail(f"The server certificate was NOT signed by the CA: {str(e)}")

    @pytest.mark.asyncio
    async def test_ssl_certificate_CA(self) -> None:
        """
        Test end-to-end certificate request and secure transmission flow.

        This test validates the complete process of requesting certificates from
        the Certificate Authority and using them for secure communication between
        Chaski nodes. It creates producer and consumer nodes, requests certificates
        for both, and then performs a secure data transmission between them.

        Raises:
            AssertionError: If certificate requests fail or secure transmission fails
        """
        producer = ChaskiStreamer(
            port=65443,
            name="Producer",
            subscriptions=["topic1"],
            reconnections=None,
            ssl_certificates_location="tmp_certs_ca",
        )

        consumer = ChaskiStreamer(
            port=65444,
            name="Consumer",
            subscriptions=["topic1"],
            reconnections=None,
            ssl_certificates_location="tmp_certs_ca",
        )

        await producer.request_ssl_certificate(
            os.getenv("CHASKI_CERTIFICATE_AUTHORITY", "ChaskiCA@127.0.0.1:65432")
        )
        await consumer.request_ssl_certificate(
            os.getenv("CHASKI_CERTIFICATE_AUTHORITY", "ChaskiCA@127.0.0.1:65432")
        )

        # Use this test instance as parent for the transmission test
        await run_transmission(producer, consumer, parent=self)
