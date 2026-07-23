import unittest
from unittest.mock import patch

from scripts.demo.telegram_inbound_bridge import (
    ApiError,
    BridgeConfig,
    EXAMPLE_MESSAGE,
    LLMExtractionError,
    ParsedCustomerRequest,
    UnsupportedMixedRequest,
    WorkflowCreationResult,
    build_workflow_create_payload,
    config_from_env,
    extract_customer_request,
    follow_up_message,
    greeting_message,
    is_greeting_message,
    parse_args,
    parse_llm_extraction_result,
    parse_customer_request,
    sender_display_name,
    telegram_run_failed_reply,
    telegram_workflow_reply,
    unsupported_mixed_item_message,
)


class TelegramInboundBridgeParserTests(unittest.TestCase):
    def config(self, *, sales: bool = False, llm: bool = False) -> BridgeConfig:
        return BridgeConfig(
            telegram_bot_token=None,
            backend_api_base_url="http://localhost:8000/api/v1",
            frontend_base_url="http://localhost:3000",
            manager_email="manager@example.test",
            manager_password="DemoPassword123!",
            poll_interval_seconds=2.0,
            allowed_chat_id=None,
            dry_run=True,
            once=True,
            auto_run=True,
            llm_extraction_enabled=llm,
            llm_provider="ollama",
            llm_model="qwen2.5:7b-instruct-q4_K_M",
            llm_base_url="http://localhost:11434",
            llm_timeout_seconds=30,
            sales_replies_enabled=sales,
        )

    def test_board_demo_phrase_parses_quantity_and_laptops(self) -> None:
        parsed = parse_customer_request(EXAMPLE_MESSAGE)

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.item_name, "Standard business laptop")
        self.assertEqual(parsed.language, "en")

    def test_parser_accepts_simple_laptop_variations(self) -> None:
        examples = [
            ("50 laptops", 50),
            ("purchase 20 laptops", 20),
            ("buy 10 laptops", 10),
            ("quote for 5 business laptops", 5),
            ("quotation for 7 standard business laptops", 7),
        ]

        for text, expected_quantity in examples:
            with self.subTest(text=text):
                parsed = parse_customer_request(text)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.quantity, expected_quantity)
                self.assertEqual(parsed.item_name, "Standard business laptop")

    def test_parser_accepts_vietnamese_laptop_request_with_office_365(self) -> None:
        parsed = parse_customer_request(
            "tôi muốn mua 50 cái máy tính xách tay doanh nhân tiêu chuẩn "
            "có cài sẵn office 365"
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.item_name, "Standard business laptop")
        self.assertEqual(parsed.language, "vi")
        self.assertEqual(parsed.requested_addons, ("office_365",))
        self.assertEqual(parsed.options_summary, "Office 365")

    def test_parser_accepts_vietnamese_laptop_variations(self) -> None:
        examples = [
            ("tôi muốn mua 50 máy tính xách tay", 50),
            ("cần báo giá 50 laptop", 50),
            ("báo giá cho 30 máy tính xách tay", 30),
            ("mua 20 laptop cho phòng kinh doanh", 20),
            ("cần 15 laptop doanh nhân", 15),
            ("50 máy tính xách tay có cài office 365", 50),
        ]

        for text, expected_quantity in examples:
            with self.subTest(text=text):
                parsed = parse_customer_request(text)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.quantity, expected_quantity)
                self.assertEqual(parsed.item_name, "Standard business laptop")
                self.assertEqual(parsed.language, "vi")

    def test_greetings_do_not_parse_as_procurement_requests(self) -> None:
        for text in ["xin chào", "hello", "hi"]:
            with self.subTest(text=text):
                self.assertTrue(is_greeting_message(text))
                self.assertIsNone(parse_customer_request(text))

    def test_parser_rejects_missing_quantity_or_item(self) -> None:
        self.assertIsNone(parse_customer_request("please send a quotation"))
        self.assertIsNone(parse_customer_request("quote for laptops"))
        self.assertIsNone(parse_customer_request("quote for 12"))
        self.assertIsNone(parse_customer_request("tôi muốn mua máy tính xách tay"))
        self.assertIsNone(parse_customer_request("cần báo giá laptop"))
        self.assertIsNone(parse_customer_request("quote for 10 ergonomic chairs"))

    def test_office_365_addon_detection(self) -> None:
        examples = [
            "50 máy tính xách tay có cài office 365",
            "50 laptop có office",
            "50 laptop microsoft 365",
            "50 laptop cài sẵn office",
        ]

        for text in examples:
            with self.subTest(text=text):
                parsed = parse_customer_request(text)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.requested_addons, ("office_365",))

    def test_workflow_payload_matches_existing_create_contract(self) -> None:
        parsed = parse_customer_request("quote for 50 standard business laptops")
        assert parsed is not None

        payload = build_workflow_create_payload(
            parsed,
            customer_name="Ada Customer",
            chat_id="12345",
            message_id="67890",
        )

        self.assertEqual(payload["workflow_type"], "procurement_quotation")
        self.assertEqual(payload["domain"], "it_equipment")
        self.assertEqual(payload["request"]["source"], "telegram")
        self.assertEqual(
            payload["request"]["request_text"],
            "quote for 50 standard business laptops",
        )
        self.assertEqual(payload["request"]["customer"]["name"], "Ada Customer")
        self.assertEqual(
            payload["request"]["items"],
            [{"name": "Standard business laptop", "quantity": 50}],
        )
        self.assertEqual(payload["request"]["requested_addons"], [])
        self.assertEqual(payload["metadata"]["state_version"], 1)
        self.assertEqual(payload["metadata"]["tags"]["source"], "telegram")
        self.assertTrue(payload["metadata"]["attributes"]["demo"])
        self.assertEqual(payload["metadata"]["attributes"]["language"], "en")
        self.assertEqual(payload["metadata"]["attributes"]["requested_addons"], [])
        self.assertEqual(
            payload["metadata"]["attributes"]["parser_version"],
            "telegram-demo-parser-v3",
        )
        self.assertEqual(
            payload["metadata"]["attributes"]["extraction_mode"],
            "deterministic",
        )
        self.assertEqual(
            payload["metadata"]["attributes"]["telegram_chat_id"],
            "12345",
        )
        self.assertEqual(
            payload["metadata"]["attributes"]["telegram_message_id"],
            "67890",
        )

    def test_vietnamese_payload_includes_language_and_requested_addons(self) -> None:
        parsed = parse_customer_request("cần báo giá 50 laptop có office")
        assert parsed is not None

        payload = build_workflow_create_payload(
            parsed,
            customer_name="Vietnamese Customer",
            chat_id="12345",
            message_id="67890",
        )

        self.assertEqual(payload["metadata"]["attributes"]["language"], "vi")
        self.assertEqual(
            payload["metadata"]["attributes"]["requested_addons"],
            ["office_365"],
        )
        self.assertEqual(payload["request"]["requested_addons"], ["office_365"])

    def test_reply_summary_mentions_parsed_request_and_addons(self) -> None:
        parsed = parse_customer_request("cần báo giá 50 laptop có office")
        assert parsed is not None
        config = BridgeConfig(
            telegram_bot_token=None,
            backend_api_base_url="http://localhost:8000/api/v1",
            frontend_base_url="http://localhost:3000",
            manager_email="manager@example.test",
            manager_password="DemoPassword123!",
            poll_interval_seconds=2.0,
            allowed_chat_id=None,
            dry_run=True,
            once=True,
            auto_run=True,
            llm_extraction_enabled=False,
            llm_provider="ollama",
            llm_model="qwen2.5:7b-instruct-q4_K_M",
            llm_base_url="http://localhost:11434",
            llm_timeout_seconds=30,
            sales_replies_enabled=False,
        )

        reply = telegram_workflow_reply(
            config=config,
            parsed=parsed,
            workflow_id="workflow-123",
            status="WAITING_APPROVAL",
            auto_run=True,
        )

        self.assertIn("Parsed: 50 x Standard business laptop", reply)
        self.assertIn("Options: Office 365", reply)
        self.assertIn("Human approval is required before resume", reply)

    def test_mixed_laptop_and_printer_request_does_not_create_workflow(self) -> None:
        parsed = extract_customer_request(
            "báo giá 20 cái laptop và 5 cái máy in hp",
            self.config(),
        )

        self.assertIsInstance(parsed, UnsupportedMixedRequest)
        assert isinstance(parsed, UnsupportedMixedRequest)
        self.assertIsNotNone(parsed.supported)
        assert parsed.supported is not None
        self.assertEqual(parsed.supported.quantity, 20)
        self.assertEqual(parsed.supported.item_name, "Standard business laptop")
        self.assertEqual(parsed.unsupported_summary, "5 x máy in HP")

    def test_technical_mixed_item_reply_mentions_supported_and_unsupported(self) -> None:
        parsed = extract_customer_request(
            "báo giá 20 cái laptop và 5 cái máy in hp",
            self.config(),
        )
        assert isinstance(parsed, UnsupportedMixedRequest)

        reply = unsupported_mixed_item_message(self.config(), parsed)

        self.assertIn("Supported: 20 x Standard business laptop", reply)
        self.assertIn("Unsupported: 5 x máy in HP", reply)
        self.assertIn("Please send a request with supported items only", reply)
        self.assertIn("laptop quotation only", reply)

    def test_sales_mixed_item_reply_is_customer_friendly(self) -> None:
        parsed = extract_customer_request(
            "báo giá 20 cái laptop và 5 cái máy in hp",
            self.config(sales=True),
        )
        assert isinstance(parsed, UnsupportedMixedRequest)

        reply = unsupported_mixed_item_message(self.config(sales=True), parsed)

        self.assertIn("Em đã nhận được yêu cầu gồm 20 x laptop", reply)
        self.assertIn("5 x máy in HP", reply)
        self.assertIn("demo chỉ hỗ trợ xử lý báo giá laptop", reply)
        self.assertIn("chưa tạo báo giá để tránh thiếu thông tin", reply)
        self.assertIn("báo giá 20 laptop văn phòng tiêu chuẩn", reply)

    def test_llm_laptop_only_result_is_blocked_when_original_mentions_printer(self) -> None:
        llm_only_laptop = ParsedCustomerRequest(
            original_text="báo giá 20 cái laptop và 5 cái máy in hp",
            quantity=20,
            item_name="Standard business laptop",
            language="vi",
            extraction_mode="llm",
            llm_provider="ollama",
            llm_model="qwen2.5:7b-instruct-q4_K_M",
        )

        parsed = extract_customer_request(
            "báo giá 20 cái laptop và 5 cái máy in hp",
            self.config(llm=True),
            llm_extractor=lambda _text, _config: llm_only_laptop,
        )

        self.assertIsInstance(parsed, UnsupportedMixedRequest)
        assert isinstance(parsed, UnsupportedMixedRequest)
        self.assertEqual(parsed.supported_summary, "20 x Standard business laptop")
        self.assertEqual(parsed.unsupported_summary, "5 x máy in HP")

    def test_laptop_only_vietnamese_request_still_creates_request(self) -> None:
        parsed = extract_customer_request("báo giá 20 laptop", self.config())

        self.assertIsInstance(parsed, ParsedCustomerRequest)
        assert isinstance(parsed, ParsedCustomerRequest)
        self.assertEqual(parsed.quantity, 20)
        self.assertEqual(parsed.item_name, "Standard business laptop")

    def test_laptop_with_office_still_creates_request(self) -> None:
        parsed = extract_customer_request(
            "tôi muốn mua 50 cái máy tính xách tay doanh nhân tiêu chuẩn có cài sẵn office 365",
            self.config(),
        )

        self.assertIsInstance(parsed, ParsedCustomerRequest)
        assert isinstance(parsed, ParsedCustomerRequest)
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.requested_addons, ("office_365",))

    def test_greeting_and_missing_quantity_remain_followups(self) -> None:
        self.assertTrue(is_greeting_message("xin chào"))
        self.assertIsNone(extract_customer_request("xin chào", self.config()))
        self.assertIsNone(extract_customer_request("tôi muốn mua laptop", self.config()))

    def test_mixed_item_reply_does_not_expose_raw_llm_or_provider_payload(self) -> None:
        parsed = extract_customer_request(
            "báo giá 20 cái laptop và 5 cái máy in hp",
            self.config(sales=True),
        )
        assert isinstance(parsed, UnsupportedMixedRequest)

        reply = unsupported_mixed_item_message(self.config(sales=True), parsed).lower()

        self.assertNotIn("prompt", reply)
        self.assertNotIn("provider_payload", reply)
        self.assertNotIn("raw_response", reply)
        self.assertNotIn("traceback", reply)

    def test_sender_display_name_uses_safe_telegram_profile_fields(self) -> None:
        self.assertEqual(
            sender_display_name(
                {"from": {"first_name": "Ada", "last_name": "Lovelace"}}
            ),
            "Ada Lovelace",
        )
        self.assertEqual(
            sender_display_name({"from": {"username": "procurement_user"}}),
            "@procurement_user",
        )
        self.assertEqual(sender_display_name({}), "Telegram Customer")


class TelegramInboundBridgeLLMExtractionTests(unittest.TestCase):
    def config(self, *, enabled: bool = True) -> BridgeConfig:
        return BridgeConfig(
            telegram_bot_token=None,
            backend_api_base_url="http://localhost:8000/api/v1",
            frontend_base_url="http://localhost:3000",
            manager_email="manager@example.test",
            manager_password="DemoPassword123!",
            poll_interval_seconds=2.0,
            allowed_chat_id=None,
            dry_run=True,
            once=True,
            auto_run=True,
            llm_extraction_enabled=enabled,
            llm_provider="ollama",
            llm_model="qwen2.5:7b-instruct-q4_K_M",
            llm_base_url="http://localhost:11434",
            llm_timeout_seconds=30,
            sales_replies_enabled=False,
        )

    def test_llm_json_parses_when_clean(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"vi","intent":"procurement_rfq","items":[{"name":"laptop","quantity":50}],"requested_addons":["office_365"],"needs_follow_up":false,"follow_up_question":""}',
            original_text="cần báo giá 50 laptop có office 365",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.item_name, "Standard business laptop")
        self.assertEqual(parsed.requested_addons, ("office_365",))
        self.assertEqual(parsed.extraction_mode, "llm")
        self.assertEqual(parsed.llm_provider, "ollama")

    def test_llm_json_parses_when_fenced(self) -> None:
        parsed = parse_llm_extraction_result(
            '```json\n{"language":"en","intent":"procurement_rfq","items":[{"name":"notebook","quantity":"12"}],"requested_addons":[],"needs_follow_up":false,"follow_up_question":""}\n```',
            original_text="please quote 12 notebooks",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 12)
        self.assertEqual(parsed.item_name, "Standard business laptop")
        self.assertEqual(parsed.language, "en")

    def test_llm_missed_office_addon_but_normalizer_adds_it(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"vi","intent":"procurement_rfq","items":[{"name":"máy tính xách tay","quantity":50}],"requested_addons":[],"needs_follow_up":false,"follow_up_question":""}',
            original_text="50 máy tính xách tay có cài office 365",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.requested_addons, ("office_365",))

    def test_llm_long_item_name_normalizes_to_standard_laptop(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"en","intent":"procurement_rfq","items":[{"name":"premium business laptop with office 365 preinstalled","quantity":25}],"requested_addons":[],"needs_follow_up":false,"follow_up_question":""}',
            original_text="quote 25 premium business laptop with office 365 preinstalled",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.item_name, "Standard business laptop")
        self.assertEqual(parsed.requested_addons, ("office_365",))

    def test_llm_invalid_json_falls_back_to_deterministic_parser(self) -> None:
        parsed = extract_customer_request(
            "quote for 50 standard business laptops",
            self.config(),
            llm_extractor=lambda _text, _config: (_ for _ in ()).throw(
                LLMExtractionError("bad json")
            ),
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.extraction_mode, "fallback")
        self.assertEqual(parsed.llm_provider, "ollama")

    def test_llm_timeout_error_falls_back_to_deterministic_parser(self) -> None:
        def timeout_extractor(_text: str, _config: BridgeConfig) -> None:
            raise LLMExtractionError("timeout")

        parsed = extract_customer_request(
            "cần báo giá 50 laptop",
            self.config(),
            llm_extractor=timeout_extractor,
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.extraction_mode, "fallback")

    def test_missing_quantity_follow_up_does_not_create_request(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"vi","intent":"procurement_rfq","items":[{"name":"laptop","quantity":0}],"requested_addons":[],"needs_follow_up":true,"follow_up_question":"Bạn cần bao nhiêu laptop?"}',
            original_text="tôi muốn mua laptop",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNone(parsed)

    def test_unsupported_item_follow_up_does_not_create_request(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"en","intent":"procurement_rfq","items":[{"name":"ergonomic chair","quantity":10}],"requested_addons":[],"needs_follow_up":true,"follow_up_question":"Which supported item?"}',
            original_text="quote for 10 chairs",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNone(parsed)

    def test_extraction_metadata_is_bounded_and_safe(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"en","intent":"procurement_rfq","items":[{"name":"laptop","quantity":50}],"requested_addons":[],"needs_follow_up":false,"follow_up_question":""}',
            original_text="quote for 50 laptops",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )
        assert parsed is not None

        payload = build_workflow_create_payload(
            parsed,
            customer_name="Ada Customer",
            chat_id="12345",
            message_id="67890",
        )
        attributes = payload["metadata"]["attributes"]

        self.assertEqual(attributes["extraction_mode"], "llm")
        self.assertEqual(attributes["llm_provider"], "ollama")
        self.assertEqual(attributes["llm_model"], "qwen2.5:7b-instruct-q4_K_M")
        serialized = str(attributes).lower()
        self.assertNotIn("prompt", serialized)
        self.assertNotIn("provider_payload", serialized)
        self.assertNotIn("raw_response", serialized)

    def test_no_workflow_creation_for_greeting(self) -> None:
        parsed = parse_llm_extraction_result(
            '{"language":"vi","intent":"greeting","items":[],"requested_addons":[],"needs_follow_up":true,"follow_up_question":"Bạn cần mua gì?"}',
            original_text="xin chào",
            provider="ollama",
            model="qwen2.5:7b-instruct-q4_K_M",
        )

        self.assertIsNone(parsed)


class TelegramInboundBridgeSalesReplyTests(unittest.TestCase):
    def config(self, *, sales: bool = False) -> BridgeConfig:
        return BridgeConfig(
            telegram_bot_token=None,
            backend_api_base_url="http://localhost:8000/api/v1",
            frontend_base_url="http://localhost:3000",
            manager_email="manager@example.test",
            manager_password="DemoPassword123!",
            poll_interval_seconds=2.0,
            allowed_chat_id=None,
            dry_run=True,
            once=True,
            auto_run=True,
            llm_extraction_enabled=False,
            llm_provider="ollama",
            llm_model="qwen2.5:7b-instruct-q4_K_M",
            llm_base_url="http://localhost:11434",
            llm_timeout_seconds=30,
            sales_replies_enabled=sales,
        )

    def vietnamese_parsed_request(self) -> object:
        parsed = parse_customer_request("cần báo giá 50 laptop có office 365")
        assert parsed is not None
        return parsed

    def test_default_technical_reply_remains_available(self) -> None:
        parsed = parse_customer_request("quote for 50 standard business laptops")
        assert parsed is not None

        reply = telegram_workflow_reply(
            config=self.config(),
            parsed=parsed,
            workflow_id="workflow-123",
            status="WAITING_APPROVAL",
            auto_run=True,
        )

        self.assertIn("Parsed: 50 x Standard business laptop", reply)
        self.assertIn("The workflow was created and run to the approval boundary.", reply)
        self.assertIn("Human approval is required before resume", reply)

    def test_sales_replies_flag_enables_sales_response(self) -> None:
        args = parse_args(["--sales-replies"])
        with patch.dict("os.environ", {}, clear=True):
            config = config_from_env(args)

        self.assertTrue(config.sales_replies_enabled)

    def test_sales_replies_env_enables_sales_response(self) -> None:
        args = parse_args([])
        with patch.dict("os.environ", {"TELEGRAM_SALES_REPLY_ENABLED": "true"}, clear=True):
            config = config_from_env(args)

        self.assertTrue(config.sales_replies_enabled)

    def test_vietnamese_success_sales_reply_is_customer_friendly(self) -> None:
        parsed = self.vietnamese_parsed_request()

        reply = telegram_workflow_reply(
            config=self.config(sales=True),
            parsed=parsed,
            workflow_id="workflow-123",
            status="WAITING_APPROVAL",
            auto_run=True,
        )

        self.assertIn("Cảm ơn anh/chị", reply)
        self.assertIn("50 x Standard business laptop", reply)
        self.assertIn("Office 365", reply)
        self.assertIn("workflow-123", reply)
        self.assertIn("WAITING_APPROVAL", reply)
        self.assertIn("http://localhost:3000/workflows/workflow-123", reply)
        self.assertIn(
            "http://localhost:3000/agent-monitor?workflowId=workflow-123",
            reply,
        )
        self.assertIn("Đây chưa phải báo giá cuối cùng", reply)

    def test_sales_run_failed_reply_hides_raw_backend_error_json(self) -> None:
        parsed = self.vietnamese_parsed_request()
        reply = telegram_run_failed_reply(
            config=self.config(sales=True),
            parsed=parsed,
            workflow=WorkflowCreationResult("workflow-123", "CREATED"),
            error=ApiError('HTTP 500: {"traceback":"secret stack","detail":"raw"}'),
        )

        self.assertIn("workflow-123", reply)
        self.assertIn("http://localhost:3000/workflows/workflow-123", reply)
        self.assertIn("chưa hoàn tất", reply)
        self.assertNotIn("traceback", reply)
        self.assertNotIn("HTTP 500", reply)
        self.assertNotIn('{"', reply)

    def test_technical_run_failed_reply_keeps_error_detail(self) -> None:
        parsed = parse_customer_request("quote for 50 standard business laptops")
        assert parsed is not None

        reply = telegram_run_failed_reply(
            config=self.config(),
            parsed=parsed,
            workflow=WorkflowCreationResult("workflow-123", "CREATED"),
            error=ApiError("HTTP 500: backend unavailable"),
        )

        self.assertIn("Run error: HTTP 500: backend unavailable", reply)

    def test_sales_greeting_reply_does_not_create_workflow(self) -> None:
        self.assertIsNone(parse_customer_request("xin chào"))
        reply = greeting_message(self.config(sales=True), "xin chào")

        self.assertIn("Em chào anh/chị", reply)
        self.assertIn("báo giá 50 laptop", reply)

    def test_sales_missing_quantity_reply_does_not_create_workflow(self) -> None:
        self.assertIsNone(parse_customer_request("tôi muốn mua laptop"))
        reply = follow_up_message(self.config(sales=True), "tôi muốn mua laptop")

        self.assertIn("Em cần thêm số lượng", reply)
        self.assertIn("báo giá 50 laptop", reply)

    def test_sales_unsupported_item_reply_does_not_create_workflow(self) -> None:
        self.assertIsNone(parse_customer_request("quote for 10 ergonomic chairs"))
        reply = follow_up_message(self.config(sales=True), "quote for 10 ergonomic chairs")

        self.assertIn("Please include quantity and item", reply)
        self.assertIn("standard business laptops", reply)

    def test_sales_replies_do_not_contain_forbidden_claims(self) -> None:
        parsed = self.vietnamese_parsed_request()
        reply = telegram_workflow_reply(
            config=self.config(sales=True),
            parsed=parsed,
            workflow_id="workflow-123",
            status="WAITING_APPROVAL",
            auto_run=True,
        ).lower()

        forbidden = (
            "final approved quote",
            "approved quote",
            "delivery date",
            "ships by",
            "email sent",
            "usd",
            "$",
            "stock available",
        )
        for claim in forbidden:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, reply)


if __name__ == "__main__":
    unittest.main()
