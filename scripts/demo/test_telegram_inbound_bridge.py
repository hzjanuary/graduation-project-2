import unittest

from scripts.demo.telegram_inbound_bridge import (
    EXAMPLE_MESSAGE,
    build_workflow_create_payload,
    parse_customer_request,
    sender_display_name,
)


class TelegramInboundBridgeParserTests(unittest.TestCase):
    def test_board_demo_phrase_parses_quantity_and_laptops(self) -> None:
        parsed = parse_customer_request(EXAMPLE_MESSAGE)

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.quantity, 50)
        self.assertEqual(parsed.item_name, "Standard business laptop")

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

    def test_parser_rejects_missing_quantity_or_item(self) -> None:
        self.assertIsNone(parse_customer_request("please send a quotation"))
        self.assertIsNone(parse_customer_request("quote for laptops"))
        self.assertIsNone(parse_customer_request("quote for 12"))

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
        self.assertEqual(payload["request"]["customer"]["name"], "Ada Customer")
        self.assertEqual(
            payload["request"]["items"],
            [{"name": "Standard business laptop", "quantity": 50}],
        )
        self.assertEqual(payload["metadata"]["state_version"], 1)
        self.assertEqual(payload["metadata"]["tags"]["source"], "telegram")
        self.assertTrue(payload["metadata"]["attributes"]["demo"])
        self.assertEqual(
            payload["metadata"]["attributes"]["telegram_chat_id"],
            "12345",
        )
        self.assertEqual(
            payload["metadata"]["attributes"]["telegram_message_id"],
            "67890",
        )

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


if __name__ == "__main__":
    unittest.main()
