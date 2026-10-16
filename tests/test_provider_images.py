"""Image handling: resize, PNG-or-JPEG choice, and all three input modes end to end."""

import base64
import io
import json
import unittest

from PIL import Image, ImageChops

import app
import gemma
import prompts
from tests.helpers import (
    FakeApi,
    ProviderTestCase,
    decode_part,
    patch_api,
    photo_like,
    screenshot_like,
    tiny_image,
)

LIMIT = gemma.MAX_IMAGE_DIMENSION


def jpeg_bytes(image, quality):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def png_size(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return len(buffer.getvalue())


class ResizeTests(unittest.TestCase):
    def test_limit_is_1536(self):
        self.assertEqual(LIMIT, 1536)

    def test_oversized_landscape_photo_is_scaled_down_proportionally(self):
        sent = decode_part(gemma._to_image_part(photo_like(1800, 1200)))
        self.assertEqual(sent.size, (1536, 1024))

    def test_oversized_portrait_photo_is_scaled_down_proportionally(self):
        sent = decode_part(gemma._to_image_part(photo_like(900, 1800)))
        self.assertEqual(sent.size, (768, 1536))

    def test_aspect_ratio_is_kept_for_awkward_sizes(self):
        width, height = 1803, 1201
        sent = decode_part(gemma._to_image_part(photo_like(width, height)))
        self.assertEqual(max(sent.size), LIMIT)
        self.assertAlmostEqual(sent.width / sent.height, width / height, delta=0.01)

    def test_images_within_the_limit_are_not_resized(self):
        for size in ((1536, 100), (100, 1536), (800, 600), (1, 1), (10, 1500)):
            sent = decode_part(gemma._to_image_part(photo_like(*size)))
            self.assertEqual(sent.size, size)

    def test_one_pixel_over_the_limit_is_resized(self):
        sent = decode_part(gemma._to_image_part(photo_like(1537, 100)))
        self.assertEqual(sent.width, 1536)

    def test_small_images_are_never_enlarged(self):
        self.assertEqual(decode_part(gemma._to_image_part(tiny_image())).size, (8, 8))

    def test_callers_image_is_not_modified(self):
        original = photo_like(1700, 1100).copy()
        before = original.tobytes()
        gemma._to_image_part(original)
        self.assertEqual(original.size, (1700, 1100))
        self.assertEqual(original.tobytes(), before)

    def test_oversized_upload_is_small(self):
        payload = gemma._to_image_part(photo_like(1800, 1200)).inline_data.data
        self.assertLess(len(payload), 1_000_000)


class EncodingTests(unittest.TestCase):
    def test_photos_are_sent_as_jpeg(self):
        part = gemma._to_image_part(photo_like(1800, 1200))
        self.assertEqual(part.inline_data.mime_type, "image/jpeg")
        self.assertEqual(decode_part(part).format, "JPEG")

    def test_jpeg_quality_is_90(self):
        self.assertEqual(gemma.JPEG_QUALITY, 90)
        photo = photo_like(800, 600)  # within the size limit, so it is encoded as is
        part = gemma._to_image_part(photo)
        self.assertEqual(part.inline_data.mime_type, "image/jpeg")
        self.assertEqual(part.inline_data.data, jpeg_bytes(photo, 90))
        self.assertNotEqual(part.inline_data.data, jpeg_bytes(photo, 60))

    def test_screenshots_stay_lossless_png(self):
        screenshot = screenshot_like(1200, 800)
        part = gemma._to_image_part(screenshot)
        self.assertEqual(part.inline_data.mime_type, "image/png")
        self.assertIsNone(ImageChops.difference(decode_part(part), screenshot).getbbox())

    def test_oversized_screenshots_are_scaled_but_not_made_lossy(self):
        part = gemma._to_image_part(screenshot_like(3000, 1800))
        self.assertEqual(part.inline_data.mime_type, "image/png")
        self.assertEqual(decode_part(part).size, (1536, 922))

    def test_jpeg_is_used_only_when_it_is_much_smaller(self):
        # On a photo JPEG is far below the ratio; on a screenshot it is above it.
        for image, jpeg_wins in ((photo_like(800, 600), True), (screenshot_like(800, 600), False)):
            ratio = len(jpeg_bytes(image, 90)) / png_size(image)
            self.assertEqual(ratio < gemma.JPEG_MAX_SIZE_RATIO, jpeg_wins, ratio)

    def test_other_image_modes_are_accepted(self):
        for mode in ("RGBA", "LA", "L", "P", "1", "CMYK"):
            part = gemma._to_image_part(Image.new(mode, (40, 30)))
            self.assertEqual(decode_part(part).size, (40, 30), mode)


class InputModesEndToEndTests(ProviderTestCase):
    """text, image, and text+image through app -> prompts -> gemma -> real SDK -> fake HTTP."""

    REPLY = json.dumps({"summary": "s", "steps": [], "confidence": 0.5})

    def run_app(self, text, image):
        api = FakeApi(200, reply=self.REPLY)
        with patch_api(api):
            states = list(app.analyze(text, image))
        status, result, _raw, _button = states[-1]
        self.assertEqual(status, "Done.")
        self.assertEqual(result["confidence"], 0.5)
        (body,) = api.bodies
        return api, body["contents"][0]["parts"]

    @staticmethod
    def image_in(part):
        """(mime type, PIL image) of an inline image as it appears in the request body."""
        inline = part["inlineData"]
        raw = base64.urlsafe_b64decode(inline["data"])  # the SDK sends URL-safe base64
        return inline["mime_type"], Image.open(io.BytesIO(raw))

    def test_text_only(self):
        api, parts = self.run_app("My laptop is hot", None)
        self.assertEqual(parts, [{"text": "My laptop is hot"}])
        self.assertEqual(api.thinking_level(), "MINIMAL")

    def test_image_only_large_photo(self):
        api, parts = self.run_app("", photo_like(1800, 1200))
        mime, image = self.image_in(parts[0])
        self.assertEqual((mime, image.size), ("image/jpeg", (1536, 1024)))
        self.assertEqual(parts[1], {"text": prompts.IMAGE_ONLY})
        self.assertEqual(api.thinking_level(), "MINIMAL")

    def test_text_and_image(self):
        api, parts = self.run_app("Is this safe?", photo_like(1700, 1100))
        _mime, image = self.image_in(parts[0])
        self.assertEqual(max(image.size), 1536)
        self.assertIn("Is this safe?", parts[1]["text"])
        self.assertEqual(api.thinking_level(), "MINIMAL")

    def test_small_screenshot_is_unchanged(self):
        screenshot = screenshot_like(900, 500)
        _api, parts = self.run_app("what does it say?", screenshot)
        mime, image = self.image_in(parts[0])
        self.assertEqual((mime, image.size), ("image/png", (900, 500)))
        self.assertIsNone(ImageChops.difference(image, screenshot).getbbox())

    def test_empty_input_never_reaches_the_provider(self):
        api = FakeApi(200)
        with patch_api(api):
            states = list(app.analyze("   ", None))
        self.assertTrue(states[-1][0].startswith("Error"))
        self.assertEqual(api.requests, [])


if __name__ == "__main__":
    unittest.main()
