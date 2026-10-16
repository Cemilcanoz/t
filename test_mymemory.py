import threading
import unittest
from unittest.mock import Mock, patch

import translator


class MyMemoryTests(unittest.TestCase):
    def response(self, data, status=200):
        r = Mock(status_code=status)
        r.json.return_value = data
        return r

    def test_unicode_byte_limit_and_exact_reconstruction(self):
        text = ("世界 🐍 Türkçe çeviri.\n\n" * 100).strip()
        parts = list(translator._byte_segments(text))
        self.assertEqual("".join(a+b for a,b in parts), text)
        self.assertTrue(all(0 < len(a.encode('utf-8')) <= 500 for a,b in parts))

    def test_long_unbroken_unicode(self):
        parts = list(translator._byte_segments("🐍" * 400))
        self.assertEqual("".join(a+b for a,b in parts), "🐍" * 400)
        self.assertTrue(all(len(a.encode('utf-8')) <= 500 for a,b in parts))

    @patch('translator.requests.get')
    def test_source_language_and_timeout_are_sent(self, get):
        r = self.response({'responseStatus': 200, 'responseData': {'translatedText': 'Merhaba'}})
        get.return_value = r
        self.assertEqual(translator.translate('Hello', provider='mymemory', source='en'), 'Merhaba')
        self.assertEqual(get.call_args.kwargs['params']['langpair'], 'en|tr')
        self.assertEqual(get.call_args.kwargs['timeout'], translator.REQUEST_TIMEOUT)
        r.close.assert_called_once()

    @patch('translator.requests.get')
    def test_quota_is_not_retried_or_shown_as_translation(self, get):
        get.return_value = self.response({'responseStatus': 429, 'quotaFinished': True,
                                         'responseData': {'translatedText': 'QUERY LIMIT'}})
        with self.assertRaisesRegex(RuntimeError, 'kota'):
            translator.translate('Hello', provider='mymemory')
        self.assertEqual(get.call_count, 1)

    @patch('translator.requests.get')
    def test_http_quota_is_not_retried(self, get):
        get.return_value = self.response({}, status=429)
        with self.assertRaisesRegex(RuntimeError, 'kota'):
            translator.translate('Hello', provider='mymemory')
        self.assertEqual(get.call_count, 1)

    @patch('translator.time.sleep')
    @patch('translator.requests.get')
    def test_invalid_response_never_becomes_partial_success(self, get, sleep):
        get.side_effect = [self.response({'responseStatus':200,'responseData':{'translatedText':'bir'}}),
                          self.response(None), self.response(None), self.response(None)]
        with self.assertRaisesRegex(RuntimeError, 'geçerli bir çeviri'):
            translator.translate('a' * 600, provider='mymemory')
        self.assertEqual(get.call_count, 4)

    @patch('translator.requests.get')
    def test_cancel_between_chunks(self, get):
        event = threading.Event()
        def respond(*args, **kwargs):
            event.set()
            return self.response({'responseStatus':200,'responseData':{'translatedText':'bir'}})
        get.side_effect = respond
        with self.assertRaises(translator.TranslationCancelled):
            translator.translate('a' * 600, provider='mymemory', cancel_event=event)
        self.assertEqual(get.call_count, 1)

    @patch('translator.requests.get')
    def test_same_language_does_not_spend_quota(self, get):
        self.assertEqual(translator.translate('Merhaba', provider='mymemory', source='tr'), 'Merhaba')
        get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
