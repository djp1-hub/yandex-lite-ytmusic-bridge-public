import contextlib
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest
from unittest.mock import patch

from station_music.core import BridgeError, ManualText, QuasarSource, Track, query_from_text, run
from station_music.ha import HomeAssistant, MusicAssistant
from station_music.cli import main
from station_music.quasar import QuasarLogEvents
from station_music.watch import watch


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.calls.append((self.path, None, self.headers.get('Authorization')))
        if self.path == '/api/services':
            result = [{'domain': 'music_assistant', 'services': {'search': {}, 'play_media': {}}}]
        else:
            result = {'state': self.server.player_state}
        self.reply(result)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.calls.append((self.path, payload, self.headers.get('Authorization')))
        if self.server.status == 302:
            self.send_response(302)
            self.send_header('Location', '/must-not-follow')
            self.end_headers()
            return
        self.reply({'service_response': {'tracks': self.server.tracks}}
                   if 'search?' in self.path else [])

    def reply(self, data):
        self.send_response(self.server.status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.calls = []
        self.server.status = 200
        self.server.player_state = 'idle'
        self.server.tracks = [{'uri': 'spotify://track/wrong', 'name': 'wrong'},
                              {'uri': 'ytmusic://track/test', 'name': 'test'}]
        self.ha = HomeAssistant(f'http://127.0.0.1:{self.server.server_port}', 'test-secret', True)
        self.ma = MusicAssistant(self.ha, 'entry', 'media_player.station_lite_ma')
        self.source = ManualText('Алиса, включи на ютубе тест')

    def test_http_vertical_slice(self):
        self.ma.preflight()
        result = run(self.source, self.ma, self.ma, execute=True)
        self.assertEqual(result['status'], 'submitted')
        self.assertEqual(len(self.server.calls), 4)
        search = self.server.calls[2]
        self.assertEqual(search[0], '/api/services/music_assistant/search?return_response')
        self.assertEqual(search[1], {'config_entry_id': 'entry', 'name': 'тест',
                                    'media_type': ['track'], 'limit': 25, 'library_only': False})
        self.assertEqual(self.server.calls[3][1], {'entity_id': 'media_player.station_lite_ma',
                         'media_id': 'ytmusic://track/test', 'media_type': 'track',
                         'enqueue': 'replace', 'radio_mode': False})
        self.assertTrue(all(c[2] == 'Bearer test-secret' for c in self.server.calls))

    def test_preview_does_not_play(self):
        self.assertEqual(run(self.source, self.ma, self.ma)['status'], 'preview')
        self.assertEqual(len(self.server.calls), 1)

    def test_case_sensitive_provider_instance(self):
        provider = 'ytmusic--AbC123xy'
        self.server.tracks = [
            {'uri': provider.lower() + '://track/wrong', 'name': 'wrong instance'},
            {'uri': provider + '://track/example', 'name': 'right instance'},
        ]
        adapter = MusicAssistant(self.ha, 'entry', 'media_player.station_lite_ma', provider)
        result = run(self.source, adapter, adapter, True)
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(self.server.calls[-1][1]['media_id'], provider + '://track/example')

    def test_native_queue_is_paused_before_ma_play(self):
        adapter = MusicAssistant(self.ha, 'entry', 'media_player.station_lite_ma',
                                 native_entity='media_player.yandex_station_lite')
        run(self.source, adapter, adapter, True)
        self.assertEqual(self.server.calls[-2][0], '/api/services/media_player/media_pause')
        self.assertEqual(self.server.calls[-2][1],
                         {'entity_id': 'media_player.yandex_station_lite'})
        self.assertEqual(self.server.calls[-1][0], '/api/services/music_assistant/play_media')
        self.assertFalse(self.server.calls[-1][1]['radio_mode'])

    def test_no_fallback_to_another_provider_or_library(self):
        for uri in ['spotify://track/x', 'library://track/1', 'https://example.org/song',
                    'ytmusic://album/x', 'ytmusic://track/']:
            with self.subTest(uri=uri):
                self.server.tracks = [{'uri': uri, 'name': 'wrong'}]
                with self.assertRaises(BridgeError):
                    run(self.source, self.ma, self.ma, True)
        self.assertTrue(all('search?' in c[0] for c in self.server.calls))

    def test_non_music_and_oversized_text_never_network(self):
        for text in ['', 'Алиса, погода', 'включи музыку', 'включи свет',
                     'включи телевизор в гостиной', 'включи чайник',
                     'включи на ютубе ', 'x' * 513]:
            with self.assertRaises(BridgeError):
                run(ManualText(text), self.ma, self.ma, True)
        self.assertEqual(self.server.calls, [])

    def test_normalization(self):
        self.assertEqual(query_from_text('АЛИСА, включи на ютубе  Queen  live'), 'Queen live')
        self.assertEqual(query_from_text('Включи через ютуб Queen live'), 'Queen live')
        self.assertEqual(
            query_from_text('Попроси музыкальный мост включить Queen live'),
            'Queen live',
        )
        self.assertEqual(
            query_from_text('Попроси музыкальный мозг включить Queen live'),
            'Queen live',
        )
        self.assertEqual(query_from_text('Включи песню Bohemian Rhapsody'),
                         'Bohemian Rhapsody')
        self.assertEqual(query_from_text('Включи группу Queen'), 'Queen')
        self.assertEqual(query_from_text('Включи noize mc страна дождей'),
                         'noize mc страна дождей')

    def test_quasar_final_phrase_emitted_only_after_idle(self):
        events = QuasarLogEvents()
        self.assertIsNone(events.feed(
            "onRequestStateChanged: LISTENING, recognizedPhrase='Включи через ютуб Queen'"
        ))
        self.assertIsNone(events.feed(
            "onAliceStateChanged: SPEAKING, recognizedPhrase='Включи через ютуб Queen'"
        ))
        self.assertEqual(events.feed("onAliceStateChanged: IDLE"),
                         'Включи через ютуб Queen')
        self.assertIsNone(events.feed("onAliceStateChanged: IDLE"))

    def test_quasar_watch_filters_prefix_and_duplicates(self):
        class FakeAdapter:
            def __init__(self):
                self.played = []

            def search(self, query):
                return [Track('ytmusic://track/test', query)]

            def play(self, track):
                self.played.append(track)

        lines = [
            "onRequestStateChanged: LISTENING, recognizedPhrase='Какая погода'\n",
            "onAliceStateChanged: IDLE\n",
            "onRequestStateChanged: LISTENING, recognizedPhrase='Попроси музыкальный мост включить Queen'\n",
            "onAliceStateChanged: BUSY, recognizedPhrase='Попроси музыкальный мост включить Queen'\n",
            "onAliceStateChanged: IDLE\n",
            "onRequestStateChanged: LISTENING, recognizedPhrase='Попроси музыкальный мост включить Queen'\n",
            "onAliceStateChanged: IDLE\n",
        ]
        adapter = FakeAdapter()
        with contextlib.redirect_stdout(io.StringIO()):
            watch(lines, adapter, cooldown=60)
        self.assertEqual([track.name for track in adapter.played], ['Queen'])

    def test_quasar_watch_discards_pending_phrase_after_disconnect(self):
        class FakeAdapter:
            def __init__(self):
                self.played = []

            def search(self, query):
                return [Track('ytmusic://track/test', query)]

            def play(self, track):
                self.played.append(track)

        lines = [
            "onRequestStateChanged: LISTENING, recognizedPhrase='Включи Queen'\n",
            None,
            "onAliceStateChanged: IDLE\n",
            "onRequestStateChanged: LISTENING, recognizedPhrase='Включи Muse'\n",
            "onAliceStateChanged: IDLE\n",
        ]
        adapter = FakeAdapter()
        with contextlib.redirect_stdout(io.StringIO()):
            watch(lines, adapter)
        self.assertEqual([track.name for track in adapter.played], ['Muse'])

    def test_quasar_is_disabled(self):
        with self.assertRaises(BridgeError):
            QuasarSource().read()

    def test_unavailable_player(self):
        self.server.player_state = 'unavailable'
        with self.assertRaises(BridgeError):
            self.ma.preflight()
        self.assertTrue(all(c[1] is None for c in self.server.calls))

    def test_http_error_redacted_and_not_retried(self):
        self.server.status = 401
        with self.assertRaisesRegex(BridgeError, 'HTTP 401') as caught:
            self.ma.search('test')
        self.assertNotIn('test-secret', str(caught.exception))
        self.assertEqual(len(self.server.calls), 1)

    def test_redirect_refused(self):
        self.server.status = 302
        with self.assertRaisesRegex(BridgeError, 'redirect refused'):
            self.ma.search('test')
        self.assertEqual(len(self.server.calls), 1)

    def test_invalid_response_fails_closed(self):
        self.server.tracks = None
        with self.assertRaisesRegex(BridgeError, 'schema'):
            run(self.source, self.ma, self.ma, True)
        self.assertEqual(len(self.server.calls), 1)

    def test_play_validates_uri(self):
        with self.assertRaises(BridgeError):
            self.ma.play(Track('https://example.org', 'bad'))
        self.assertEqual(self.server.calls, [])

    def test_transport_configuration(self):
        for url in ['http://ha.local', 'https://user:secret@ha.local', 'https://ha.local/path', '']:
            with self.assertRaises(BridgeError):
                HomeAssistant(url, 'token')

    def test_demo_cli(self):
        with patch('sys.argv', ['station-music', self.source.text, '--demo']), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(), 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'preview')
        self.assertEqual(self.server.calls, [])

    def test_demo_execute_rejected(self):
        with patch('sys.argv', ['station-music', self.source.text, '--demo', '--execute']), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 2)


if __name__ == '__main__':
    unittest.main()
