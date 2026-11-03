"""groq_transcribe.py 동작 고정용 unittest (네트워크 미사용).

실행: python3 -m unittest discover -s tests -v
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import groq_transcribe as gt  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self._buf = io.BytesIO(payload)

    def read(self):
        return self._buf.getvalue()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TranscribeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.audio = os.path.join(self.tmp.name, "sample.mp3")
        with open(self.audio, "wb") as f:
            f.write(b"ID3" + b"\x00" * 64)
        self.out = os.path.join(self.tmp.name, "out.txt")
        self.env = mock.patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_dummy"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def _patch_response(self, payload):
        return mock.patch("urllib.request.urlopen",
                          return_value=FakeResponse(json.dumps(payload).encode()))

    def test_writes_transcript_and_returns_text(self):
        with self._patch_response({"text": "안녕하세요 회의록입니다."}) as m:
            text = gt.transcribe(self.audio, self.out)
        self.assertEqual(text, "안녕하세요 회의록입니다.")
        self.assertTrue(os.path.exists(self.out))
        with open(self.out, encoding="utf-8") as f:
            self.assertEqual(f.read(), "안녕하세요 회의록입니다.")
        self.assertTrue(m.called)

    def test_empty_text_returns_none_and_writes_nothing(self):
        with self._patch_response({"text": "   "}):
            text = gt.transcribe(self.audio, self.out)
        self.assertIsNone(text)
        self.assertFalse(os.path.exists(self.out))

    def test_oversize_file_fails_before_upload(self):
        with mock.patch("urllib.request.urlopen") as m:
            with mock.patch("os.path.getsize", return_value=30 * 1024 * 1024):
                text = gt.transcribe(self.audio, self.out)
        self.assertIsNone(text)
        m.assert_not_called()

    def _sent_body(self, filename, **kwargs):
        path = os.path.join(self.tmp.name, filename)
        with open(path, "wb") as f:
            f.write(b"ID3data")
        with self._patch_response({"text": "ok"}) as m:
            gt.transcribe(path, self.out, **kwargs)
        return m.call_args[0][0].data

    def test_content_type_follows_extension(self):
        self.assertIn(b"Content-Type: audio/wav", self._sent_body("a.wav"))
        self.assertIn(b"Content-Type: audio/mpeg", self._sent_body("b.mp3"))

    def test_language_override_reaches_request(self):
        body = self._sent_body("c.mp3", language="en")
        self.assertIn(b'name="language"', body)
        self.assertIn(b"\r\n\r\nen\r\n", body)

    def test_cli_exits_one_when_audio_missing(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "groq_transcribe.py"),
             os.path.join(self.tmp.name, "nope.mp3")],
            capture_output=True, text=True, env={**os.environ, "GROQ_API_KEY": "gsk_test_dummy"})
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
