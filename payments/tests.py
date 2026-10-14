import base64
from decimal import Decimal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.test import SimpleTestCase, override_settings

from payments.providers import (
    AirtelMoneyProvider,
    MixxProvider,
    PaymentProviderError,
    PaymentProviderRequest,
    PaymentProviderStatus,
    get_payment_provider,
)
from payments.providers.airtel import AirtelMoneyConfig
from payments.providers.mixx import MixxConfig
from payments.providers.mpesa import MpesaConfig, MpesaProvider


class RecordingTransport:
    def __init__(self, response):
        self.responses = list(response) if isinstance(response, list) else [response]
        self.calls = []

    def post(self, url, *, headers, payload, timeout):
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)

    def get(self, url, *, headers, timeout):
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


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


class AirtelMoneyProviderTests(SimpleTestCase):
    def setUp(self):
        self.config = AirtelMoneyConfig(
            enabled=True,
            environment="sandbox",
            base_url="https://airtel.example.test/",
            client_id="airtel-client",
            client_secret="airtel-secret",
            timeout_seconds=8,
        )
        self.payment = PaymentProviderRequest(
            amount=Decimal("7250"),
            currency="TZS",
            payer_phone_number="0684 000 001",
            reference="BAHASHA-2026-0002",
            description="Jengo week 41",
            conversation_id="bahasha-0002",
        )

    def test_initiate_authenticates_and_builds_collection_request(self):
        transport = RecordingTransport(
            [
                {"access_token": "airtel-token"},
                {
                    "status": {"success": True, "response_code": "DP00800001000"},
                    "data": {
                        "transaction": {
                            "id": "bahasha-0002",
                            "status": "TIP",
                            "message": "Transaction is pending",
                        }
                    },
                },
            ]
        )

        result = AirtelMoneyProvider(self.config, transport).initiate(self.payment)

        self.assertEqual(
            result.status,
            PaymentProviderStatus.PENDING_CUSTOMER_ACTION,
        )
        self.assertEqual(transport.calls[0]["url"], "https://airtel.example.test/auth/oauth2/token")
        collection = transport.calls[1]
        self.assertEqual(collection["url"], "https://airtel.example.test/merchant/v1/payments/")
        self.assertEqual(collection["headers"]["Authorization"], "Bearer airtel-token")
        self.assertEqual(collection["headers"]["X-Country"], "TZ")
        self.assertEqual(collection["payload"]["subscriber"]["msisdn"], "255684000001")
        self.assertEqual(collection["payload"]["transaction"]["amount"], "7250.00")

    def test_query_uses_transaction_identifier_and_maps_success(self):
        transport = RecordingTransport(
            [
                {"access_token": "airtel-token"},
                {"data": {"transaction": {"id": "bahasha-0002", "status": "TS"}}},
            ]
        )

        result = AirtelMoneyProvider(self.config, transport).query(self.payment)

        self.assertEqual(result.status, PaymentProviderStatus.SUCCEEDED)
        self.assertEqual(transport.calls[1]["method"], "GET")
        self.assertEqual(
            transport.calls[1]["url"],
            "https://airtel.example.test/standard/v1/payments/bahasha-0002",
        )

    def test_unconfigured_adapter_stops_before_authentication(self):
        config = AirtelMoneyConfig(
            enabled=False,
            environment="sandbox",
            base_url="https://airtel.example.test/",
            client_id="",
            client_secret="",
        )
        transport = RecordingTransport({})

        with self.assertRaises(PaymentProviderError) as raised:
            AirtelMoneyProvider(config, transport).initiate(self.payment)

        self.assertEqual(raised.exception.code, "AIRTEL_NOT_CONFIGURED")
        self.assertEqual(transport.calls, [])

    @override_settings(PAYMENT_PROVIDER="airtel_money")
    def test_factory_returns_airtel_adapter(self):
        self.assertIsInstance(get_payment_provider(), AirtelMoneyProvider)


class MixxProviderTests(SimpleTestCase):
    def setUp(self):
        self.config = MixxConfig(
            enabled=True,
            environment="sandbox",
            base_url="https://mixx.example.test/api/",
            client_id="mixx-client",
            client_secret="mixx-secret",
            merchant_code="BAHASHA-MERCHANT",
            token_path="oauth/token",
            collection_path="collections",
            query_path="collections/{transaction_id}",
            timeout_seconds=9,
        )
        self.payment = PaymentProviderRequest(
            amount=Decimal("3000"),
            currency="TZS",
            payer_phone_number="0713 000 002",
            reference="BAHASHA-2026-0003",
            description="Ahadi missing week",
            conversation_id="bahasha-0003",
        )

    def test_initiate_uses_onboarding_paths_and_merchant_identity(self):
        transport = RecordingTransport(
            [
                {"data": {"access_token": "mixx-token"}},
                {
                    "responseCode": "0",
                    "message": "Request accepted",
                    "data": {
                        "transactionId": "bahasha-0003",
                        "status": "PENDING",
                    },
                },
            ]
        )

        result = MixxProvider(self.config, transport).initiate(self.payment)

        self.assertEqual(
            result.status,
            PaymentProviderStatus.PENDING_CUSTOMER_ACTION,
        )
        self.assertEqual(transport.calls[0]["url"], "https://mixx.example.test/api/oauth/token")
        collection = transport.calls[1]
        self.assertEqual(collection["url"], "https://mixx.example.test/api/collections")
        self.assertEqual(collection["headers"]["Authorization"], "Bearer mixx-token")
        self.assertEqual(collection["payload"]["merchantCode"], "BAHASHA-MERCHANT")
        self.assertEqual(collection["payload"]["customer"]["msisdn"], "255713000002")
        self.assertEqual(collection["payload"]["amount"], "3000.00")

    def test_query_uses_configured_path_and_maps_completed(self):
        transport = RecordingTransport(
            [
                {"access_token": "mixx-token"},
                {"data": {"transactionId": "bahasha-0003", "status": "COMPLETED"}},
            ]
        )

        result = MixxProvider(self.config, transport).query(self.payment)

        self.assertEqual(result.status, PaymentProviderStatus.SUCCEEDED)
        self.assertEqual(transport.calls[1]["method"], "GET")
        self.assertEqual(
            transport.calls[1]["url"],
            "https://mixx.example.test/api/collections/bahasha-0003",
        )

    def test_missing_onboarding_contract_blocks_network_access(self):
        config = MixxConfig(
            enabled=True,
            environment="sandbox",
            base_url="",
            client_id="",
            client_secret="",
            merchant_code="",
            token_path="",
            collection_path="",
            query_path="",
        )
        transport = RecordingTransport({})

        with self.assertRaises(PaymentProviderError) as raised:
            MixxProvider(config, transport).initiate(self.payment)

        self.assertEqual(raised.exception.code, "MIXX_NOT_CONFIGURED")
        self.assertEqual(transport.calls, [])

    @override_settings(PAYMENT_PROVIDER="mixx_by_yas")
    def test_factory_returns_mixx_adapter(self):
        self.assertIsInstance(get_payment_provider(), MixxProvider)
