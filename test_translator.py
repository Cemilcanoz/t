"""Çeviri metnini bölme davranışı için ağ bağlantısı gerektirmeyen testler."""
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import requests
import threading

import translator
from deep_translator.exceptions import TooManyRequests


class SplitTextTests(unittest.TestCase):
    def test_short_text_stays_in_one_chunk(self):
        self.assertEqual(translator._split_text("Kısa bir metin.", 50), ["Kısa bir metin."])

    def test_short_text_keeps_line_breaks(self):
        text = "Birinci satır.\nİkinci satır."
        self.assertEqual(translator._split_text(text, 50), [text])

    def test_long_word_is_not_lost(self):
        text = "x" * 23
        chunks = translator._split_text(text, 10)
        self.assertTrue(all(len(chunk) <= 10 for chunk in chunks))
        self.assertEqual("".join(chunks), text)

    def test_words_are_split_at_spaces_when_possible(self):
        chunks = translator._split_text("alpha beta gamma delta", 11)
        self.assertEqual(chunks, ["alpha beta", "gamma delta"])

    def test_split_reconstruction_preserves_every_character_and_separator(self):
        source = "alpha  beta\n\ngamma\tdelta" + "x" * 20
        self.assertEqual("".join(chunk + separator for chunk, separator in translator._split_segments(source, 7)), source)

    @patch("translator.GoogleTranslator")
    def test_translate_sends_every_chunk(self, translator_cls):
        engine = translator_cls.return_value
        engine.translate.side_effect = lambda value: value.upper()

        with patch.object(translator, "MAX_CHARS", 10):
            result = translator.translate("alpha beta gamma delta")

        self.assertEqual(result, "ALPHA BETA GAMMA DELTA")
        self.assertEqual(engine.translate.call_count, 3)

    @patch("translator.time.sleep")
    @patch("translator.GoogleTranslator")
    def test_rate_limit_is_retried(self, translator_cls, sleep):
        engine = translator_cls.return_value
        engine.translate.side_effect = [TooManyRequests(), "çeviri"]

        self.assertEqual(translator.translate("translation"), "çeviri")
        sleep.assert_called_once_with(1.0)

    @patch("translator.time.sleep")
    @patch("translator.GoogleTranslator")
    def test_persistent_rate_limit_has_friendly_error(self, translator_cls, sleep):
        translator_cls.return_value.translate.side_effect = TooManyRequests()

        with self.assertRaisesRegex(RuntimeError, "çok yoğun"):
            translator.translate("translation")
        self.assertEqual(sleep.call_count, 2)

    @patch("translator.GoogleTranslator")
    def test_paragraphs_survive_chunking(self, translator_cls):
        translator_cls.return_value.translate.side_effect = str.upper
        with patch.object(translator, "MAX_CHARS", 10):
            result = translator.translate("alpha beta gamma\n\ndelta epsilon\nlast")
        self.assertEqual(result, "ALPHA BETA GAMMA\n\nDELTA EPSILON\nLAST")

    @patch("translator.GoogleTranslator")
    def test_short_multiline_text_uses_one_request(self, translator_cls):
        translator_cls.return_value.translate.side_effect = str.upper
        text = "first sentence.\nsecond sentence.\n\nlast paragraph."
        self.assertEqual(translator.translate(text), text.upper())
        translator_cls.return_value.translate.assert_called_once_with(text)

    @patch("translator.time.sleep")
    @patch("translator.GoogleTranslator")
    def test_timeout_retries_then_recovers(self, translator_cls, sleep):
        translator_cls.return_value.translate.side_effect = [requests.Timeout(), "çeviri"]
        self.assertEqual(translator.translate("test"), "çeviri")
        self.assertEqual(sleep.call_count, 1)

    @patch("translator.time.sleep")
    @patch("translator.GoogleTranslator")
    def test_empty_second_chunk_never_returns_partial_success(self, translator_cls, sleep):
        translator_cls.return_value.translate.side_effect = ["ilk", "", None, "   "]
        with patch.object(translator, "MAX_CHARS", 5):
            with self.assertRaisesRegex(RuntimeError, "geçerli bir çeviri"):
                translator.translate("one\nsecond")
        self.assertEqual(translator_cls.return_value.translate.call_count, 4)

    @patch("translator.time.sleep")
    @patch("translator.GoogleTranslator")
    def test_persistent_network_failure_has_bounded_attempts(self, translator_cls, sleep):
        translator_cls.return_value.translate.side_effect = requests.ConnectionError("private text")
        with self.assertRaisesRegex(RuntimeError, "bağlanılamadı") as error:
            translator.translate("private text")
        self.assertNotIn("private text", str(error.exception))
        self.assertEqual(translator_cls.return_value.translate.call_count, 3)

    @patch("translator.GoogleTranslator")
    def test_cancellation_before_start_makes_no_request(self, translator_cls):
        event = threading.Event()
        event.set()
        with self.assertRaises(translator.TranslationCancelled):
            translator.translate("test", cancel_event=event)
        translator_cls.assert_not_called()

    @patch("translator.GoogleTranslator")
    def test_cancellation_during_request_prevents_retry(self, translator_cls):
        event = threading.Event()
        def fail(text):
            event.set()
            raise requests.Timeout()
        translator_cls.return_value.translate.side_effect = fail
        with self.assertRaises(translator.TranslationCancelled):
            translator.translate("test", cancel_event=event)
        self.assertEqual(translator_cls.return_value.translate.call_count, 1)

    @patch("translator.GoogleTranslator")
    def test_cancellation_on_success_prevents_next_chunk(self, translator_cls):
        event = threading.Event()
        def complete(text):
            event.set()
            return "first"
        translator_cls.return_value.translate.side_effect = complete
        with patch.object(translator, "MAX_CHARS", 5):
            with self.assertRaises(translator.TranslationCancelled):
                translator.translate("one two three", cancel_event=event)
        self.assertEqual(translator_cls.return_value.translate.call_count, 1)

    @patch("translator.GoogleTranslator")
    def test_cancellation_interrupts_backoff(self, translator_cls):
        event = Mock()
        event.is_set.side_effect = [False, False, False, True]
        translator_cls.return_value.translate.side_effect = requests.Timeout()
        with self.assertRaises(translator.TranslationCancelled):
            translator.translate("test", cancel_event=event)
        event.wait.assert_called_once_with(1.0)
        self.assertEqual(translator_cls.return_value.translate.call_count, 1)


class TransportTests(unittest.TestCase):
    @staticmethod
    def response(status=200, html='<div class="result-container">Merhaba dünya.</div>', data=None):
        response = Mock(status_code=status, text=html)
        response.json.return_value = data
        return response

    @patch("translator.requests.get")
    def test_html_request_has_timeout_and_closes_response(self, get):
        response = self.response()
        get.return_value = response
        self.assertEqual(translator.GoogleTranslator(source="auto", target="tr").translate("Hello world."), "Merhaba dünya.")
        self.assertEqual(get.call_args.kwargs["timeout"], translator.REQUEST_TIMEOUT)
        response.close.assert_called_once()

    @patch("translator.time.sleep")
    @patch("translator.requests.get")
    def test_rate_limit_uses_same_provider_json_fallback(self, get, sleep):
        limited = self.response(status=429)
        success = self.response(data=[[["Merhaba ", "Hello ", None], ["dünya.", "world.", None]], None, "en"])
        get.side_effect = [limited, success]
        self.assertEqual(translator.translate("Hello world."), "Merhaba dünya.")
        self.assertIn("translate.googleapis.com", get.call_args.args[0])
        limited.close.assert_called_once()
        success.close.assert_called_once()

    @patch("translator.time.sleep")
    @patch("translator.requests.get")
    def test_challenge_and_malformed_json_fail_without_silent_loss(self, get, sleep):
        responses = [self.response(html="<html>Consent required</html>"),
                     self.response(data=[[["partial", "one"], [None, "two"]]]),
                     self.response(html="<div class='t0'> </div>")]
        get.side_effect = responses
        with self.assertRaisesRegex(RuntimeError, "geçerli bir çeviri"):
            translator.translate("one two")
        self.assertEqual(get.call_count, 3)
        for response in responses:
            response.close.assert_called_once()

    @patch("translator.time.sleep")
    @patch("translator.requests.get")
    def test_server_failure_retries(self, get, sleep):
        get.side_effect = [self.response(status=503),
                           self.response(data=[[["çeviri", "text"]]])]
        self.assertEqual(translator.translate("text"), "çeviri")

    @patch("translator.requests.get")
    def test_invalid_target_does_not_request_network(self, get):
        with self.assertRaises(Exception):
            translator.translate("test", target="invalid-language-code")
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
