import base64
from decimal import Decimal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.test import SimpleTestCase, override_settings

from payments.providers import (
    PaymentProviderError,
    PaymentProviderRequest,
    PaymentProviderStatus,
    get_payment_provider,
)
from payments.providers.mpesa import MpesaConfig, MpesaProvider


class RecordingTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, *, headers, payload, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return self.response


class MpesaProviderTests(SimpleTestCase):
    def setUp(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.config = MpesaConfig(
            enabled=True,
            environment="sandbox",
            base_url="https://openapi.example.test/sandbox/",
            api_key="sandbox-api-key",
            public_key=public_key.decode("ascii"),
            service_provider_code="123456",
            timeout_seconds=7,
        )
        self.payment = PaymentProviderRequest(
            amount=Decimal("5000"),
            currency="TZS",
            payer_phone_number="0700 000 001",
            reference="BAHASHA-2026-0001",
            description="Ahadi week 40",
            conversation_id="bahasha-0001",
        )

    def test_initiate_builds_vodacom_c2b_request_and_authorization(self):
        transport = RecordingTransport(
            {
                "output_ResponseCode": "0",
                "output_ResponseDesc": "Request processed successfully",
                "output_ConversationID": "provider-conversation",
                "output_TransactionID": "transaction-1",
            }
        )
        provider = MpesaProvider(self.config, transport)

        result = provider.initiate(self.payment)

        self.assertEqual(result.status, PaymentProviderStatus.PENDING_CUSTOMER_ACTION)
        self.assertEqual(result.transaction_id, "transaction-1")
        call = transport.calls[0]
        self.assertEqual(
            call["url"],
            "https://openapi.example.test/sandbox/ipg/v2/vodacomTZN/"
            "c2bPayment/singleStage/",
        )
        self.assertEqual(call["payload"]["input_Amount"], "5000.00")
        self.assertEqual(call["payload"]["input_CustomerMSISDN"], "255700000001")
        self.assertEqual(call["payload"]["input_ServiceProviderCode"], "123456")
        encrypted = base64.b64decode(call["headers"]["Authorization"].split()[1])
        decrypted = self.private_key.decrypt(encrypted, padding.PKCS1v15())
        self.assertEqual(decrypted, b"sandbox-api-key")

    def test_query_uses_provider_reference_and_maps_success(self):
        transport = RecordingTransport(
            {
                "output_ResponseCode": "0",
                "output_ResponseDesc": "Transaction completed",
                "output_TransactionID": "transaction-1",
            }
        )
        provider = MpesaProvider(self.config, transport)

        result = provider.query(self.payment)

        self.assertEqual(result.status, PaymentProviderStatus.SUCCEEDED)
        self.assertEqual(
            transport.calls[0]["payload"]["input_QueryReference"],
            "BAHASHA-2026-0001",
        )

    def test_unconfigured_provider_fails_before_network_request(self):
        config = MpesaConfig(
            enabled=False,
            environment="sandbox",
            base_url="https://openapi.example.test/sandbox/",
            api_key="",
            public_key="",
            service_provider_code="",
        )
        transport = RecordingTransport({})

        with self.assertRaises(PaymentProviderError) as raised:
            MpesaProvider(config, transport).initiate(self.payment)

        self.assertEqual(raised.exception.code, "MPESA_NOT_CONFIGURED")
        self.assertEqual(transport.calls, [])

    def test_invalid_phone_is_rejected_before_network_request(self):
        transport = RecordingTransport({})
        payment = PaymentProviderRequest(
            amount=self.payment.amount,
            currency=self.payment.currency,
            payer_phone_number="123",
            reference=self.payment.reference,
            description=self.payment.description,
            conversation_id=self.payment.conversation_id,
        )

        with self.assertRaises(PaymentProviderError) as raised:
            MpesaProvider(self.config, transport).initiate(payment)

        self.assertEqual(raised.exception.code, "MPESA_PHONE_INVALID")
        self.assertEqual(transport.calls, [])

    @override_settings(PAYMENT_PROVIDER="vodacom_m_pesa")
    def test_factory_returns_mpesa_adapter(self):
        self.assertIsInstance(get_payment_provider(), MpesaProvider)

    @override_settings(PAYMENT_PROVIDER="unknown")
    def test_factory_rejects_unknown_provider(self):
        with self.assertRaises(PaymentProviderError) as raised:
            get_payment_provider()

        self.assertEqual(raised.exception.code, "PAYMENT_PROVIDER_UNKNOWN")
