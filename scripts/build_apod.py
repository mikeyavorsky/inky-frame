"""Build baseline JPEGs from the APOD article, never site navigation images."""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from PIL import Image, ImageOps

PAGE = "https://science.nasa.gov/apod/"
OUT = Path(__file__).resolve().parents[1] / "assets" / "apod"


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "InkyFrame-APOD/1.0"}), timeout=60) as response:
        return response.read()


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.smd-embed-post__article")
    if article is None:
        raise ValueError("APOD article missing; keeping the previous feed")
    title = article.find("h2")
    # Restrict selection to APOD assets inside the featured article.
    picture = next((img for img in article.find_all("img")
                    if "/apod/" in img.get("src", "")
                    and "logo" not in img["src"].lower()), None)
    if title is None or picture is None:
        raise ValueError("No APOD still image; keeping the previous feed")
    return title.get_text(strip=True), picture["src"]


def main():
    title, source = parse_page(fetch(PAGE))
    with Image.open(io.BytesIO(fetch(source))) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    if min(image.size) < 200:
        raise ValueError("APOD image suspiciously small; keeping previous feed")
    OUT.mkdir(parents=True, exist_ok=True)
    images = {}
    for width, height in ((600, 448), (640, 400), (800, 480)):
        # Leave the bottom 25 pixels for the device's caption.
        fitted = ImageOps.contain(image, (width, height - 25), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), "black")
        canvas.paste(fitted, ((width - fitted.width) // 2,
                              (height - 25 - fitted.height) // 2))
        buffer = io.BytesIO()
        canvas.save(buffer, "JPEG", quality=90, progressive=False)
        data = buffer.getvalue()
        name = hashlib.sha256(data).hexdigest()[:20] + ".jpg"
        (OUT / name).write_bytes(data)
        images[str(height)] = name
    (OUT / "feed.json").write_text(json.dumps({"title": title, "source": source,
                                                "images": images}, indent=2) + "\n")
    print(title)


if __name__ == "__main__":
    main()
