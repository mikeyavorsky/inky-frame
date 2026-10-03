import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_apod import parse_page
from PIL import Image


class APODTests(unittest.TestCase):
    def test_selects_article_image_not_logo(self):
        html = '<img src="logo.png"><article class="smd-embed-post__article"><h2>Nebulas</h2><img src="https://assets.science.nasa.gov/apod/stars.png"></article>'
        self.assertEqual(parse_page(html), ('Nebulas', 'https://assets.science.nasa.gov/apod/stars.png'))

    def test_rejects_logo_and_video_only_pages(self):
        for body in ('<img src="/apod/nasa-logo.png">', '<iframe src="video"></iframe>'):
            with self.assertRaises(ValueError):
                parse_page('<article class="smd-embed-post__article"><h2>APOD</h2>' + body + '</article>')

    def test_download_exact_bytes_and_preserve_cache(self):
        request = Mock()
        decoder = Mock()
        modules = {'urllib.urequest': request, 'jpegdec': decoder,
                   'inky_frame': types.SimpleNamespace(BLACK=0, RED=1, WHITE=2), 'ujson': json}
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location('apod_device', ROOT / 'nasa_apod.py')
            app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app)
        jpeg = b'\xff\xd8' + b'x' * 1030 + b'\xff\xd9'
        metadata = json.dumps({'title': 'Test stars', 'images': {'448': 'stars.jpg'}}).encode()
        old_dir = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                request.urlopen.side_effect = [io.BytesIO(metadata), io.BytesIO(jpeg)]
                app.update()
                self.assertEqual(Path(app.FILENAME).read_bytes(), jpeg)
                for bad in (b'<html>Error</html>', jpeg[:-3]):
                    request.urlopen.side_effect = [io.BytesIO(metadata), io.BytesIO(bad)]
                    app.update()
                    self.assertEqual(Path(app.FILENAME).read_bytes(), jpeg)
                    self.assertEqual(app.apod_title, 'Test stars')
                request.urlopen.side_effect = OSError('offline')
                app.update()
                self.assertEqual(Path(app.FILENAME).read_bytes(), jpeg)
                self.assertFalse(Path(app.FILENAME + '.new').exists())
            finally:
                os.chdir(old_dir)

    def test_generated_feed_dimensions_and_baseline_jpeg(self):
        feed = json.loads((ROOT / 'assets/apod/feed.json').read_text())
        for height, width in ((448, 600), (400, 640), (480, 800)):
            with Image.open(ROOT / 'assets/apod' / feed['images'][str(height)]) as image:
                self.assertEqual(image.size, (width, height))
                self.assertEqual(image.format, 'JPEG')
                self.assertFalse(image.info.get('progressive', False))


if __name__ == '__main__':
    unittest.main()
