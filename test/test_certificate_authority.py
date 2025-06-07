"""
=============================================
Pytest tests for the CertificateAuthority class
=============================================

These tests ensure the correct functionality of the CertificateAuthority,
including the creation of certificate authority (CA) certificates, private keys,
certificate signing requests (CSRs), and the signing of CSRs.

Dependencies:
- os
- pytest
- ipaddress
- cryptography (x509, default_backend, padding, hashes, serialization)
- chaski.utils.certificate_authority (CertificateAuthority)
"""

import os
import pytest
import ipaddress
import subprocess
import sys
import time
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

from chaski.utils.certificate_authority import CertificateAuthority
from chaski.utils.auto import run_transmission
from chaski.streamer import ChaskiStreamer


@pytest.fixture(scope="class")
def setup_ca(request):
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
    time.sleep(1)


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_ca")
class TestCertificateAuthority:
    """Test suite for the CertificateAuthority class using pytest."""

    # Class-level constants
    SSL_CERTIFICATES_LOCATION = "ssl_certificates_location"
    TEST_NAME = "Test-ID"
    # TEST_NAME = "3ea4e610-f276-4715-aa52-88d1cf14a295"
    # TEST_NAME = "4c535672-949e-480f-9df4-9548a4cc2c1f"

    @classmethod
    def setup_class(cls):
        """Set up the class for the Certificate Authority tests.

        This method is a class-level setup method that prepares the
        environment for testing the Certificate Authority (CA). It
        creates a directory for storing SSL certificates if it does
        not already exist.
        """
        if not os.path.exists(cls.SSL_CERTIFICATES_LOCATION):
            os.mkdir(cls.SSL_CERTIFICATES_LOCATION)

    @pytest.fixture
    def certificate_authority(self):
        """Create and return a CertificateAuthority instance.

        This fixture instantiates a CertificateAuthority object with preset
        configurations for testing purposes. The attributes include an ID,
        an IP address, the SSL certificates location, and SSL certificate
        attributes like the country, locality, organization, state, and common name.

        Returns
        -------
        CertificateAuthority
            An instance of CertificateAuthority configured for testing.
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
    async def test_ca(self, certificate_authority):
        """Test the creation of CA certificate and private key.

        This test verifies the functionality of the `setup_certificate_authority` method
        in the `CertificateAuthority` class. It ensures that the CA certificate and private key
        are generated and saved correctly. Additionally, it performs a validation to check
        if the private key corresponds to the generated certificate by signing and verifying a message.
        """
        ca = certificate_authority
        ca.setup_certificate_authority()

        assert os.path.exists(
            ca.ca_certificate_path
        ), "ca_certificate_path does not exist"
        assert os.path.exists(
            ca.ca_private_key_path
        ), "ca_private_key_path does not exist"

        certificate = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.ca_certificate_path), default_backend()
        )

        private_key = serialization.load_pem_private_key(
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
    async def test_csr(self, certificate_authority):
        """Test the generation of private keys and CSRs.

        This test verifies the functionality of the `generate_key_and_csr` method
        in the `CertificateAuthority` class. It ensures that both client and server
        private keys and certificate signing requests (CSRs) are generated and saved correctly.
        It also verifies that the moduli of the private keys match those of the corresponding CSRs.
        """
        ca = certificate_authority
        ca.generate_key_and_csr()

        assert os.path.exists(ca.private_key_paths["client"])
        assert os.path.exists(ca.private_key_paths["server"])
        assert os.path.exists(ca.certificate_paths["client"])
        assert os.path.exists(ca.certificate_paths["server"])

        def key_modulus(key: bytes) -> int:
            private_key = serialization.load_pem_private_key(
                key, password=None, backend=default_backend()
            )
            modulus = private_key.private_numbers().public_numbers.n
            return modulus

        def csr_modulus(key: bytes) -> int:
            csr = x509.load_pem_x509_csr(key, backend=default_backend())
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
    async def test_sign(self, certificate_authority):
        """Test signing of client and server CSRs by the CA.

        This test verifies the functionality of the `sign_csr` method
        in the `CertificateAuthority` class. It ensures that the client and server
        certificate signing requests (CSRs) are signed correctly by the CA.
        After signing the CSRs, it checks that the signatures on the resulting
        certificates are valid and were created by the CA's private key.
        """
        ca = certificate_authority

        ca.load_ca(
            ca_key_path=os.path.join(self.SSL_CERTIFICATES_LOCATION, "ca.key"),
            ca_cert_path=os.path.join(self.SSL_CERTIFICATES_LOCATION, "ca.cert"),
        )

        ca.load_key_and_csr(
            private_key_client_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"client_{self.TEST_NAME}.key"
            ),
            certificate_client_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"client_{self.TEST_NAME}.csr"
            ),
            private_key_server_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"server_{self.TEST_NAME}.key"
            ),
            certificate_server_path=os.path.join(
                self.SSL_CERTIFICATES_LOCATION, f"server_{self.TEST_NAME}.csr"
            ),
        )

        with open(ca.certificate_signed_paths["client"], "wb") as file:
            file.write(ca.sign_csr(ca.load_certificate(ca.certificate_paths["client"])))

        with open(ca.certificate_signed_paths["server"], "wb") as file:
            file.write(ca.sign_csr(ca.load_certificate(ca.certificate_paths["server"])))

        ca_cert = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.ca_certificate_path), default_backend()
        )
        ca_public_key = ca_cert.public_key()

        client_cert = x509.load_pem_x509_certificate(
            ca.load_certificate(ca.certificate_signed_paths["client"]),
            default_backend(),
        )
        server_cert = x509.load_pem_x509_certificate(
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
    async def test_ssl_certificate_CA(self):
        """
        Test requesting SSL certificates from the Certificate Authority (CA).

        This test method validates the process of requesting and obtaining
        SSL/TLS certificates from a Certificate Authority for both producer
        and consumer nodes. The steps include:

        1. Initialize a ChaskiStreamer instance for the producer with the CA's address.
        2. Initialize a ChaskiStreamer instance for the consumer with the CA's address.
        3. Request SSL certificates for both producer and consumer from the CA.
        4. Run a secure transmission between producer and consumer to validate the
           successful acquisition and usage of the SSL certificates.
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

        # Ahora podemos usar self como parent (disponible en clase)
        await run_transmission(producer, consumer, parent=self)
