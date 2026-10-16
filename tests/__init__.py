"""Test package.

Makes the whole suite independent of a developer's real .env: tests never see a
real API key or GEMMA_* settings. (gemma.py calls load_dotenv(), which does not
override variables that are already set, even to an empty string.)
"""

import os

os.environ["GOOGLE_API_KEY"] = "test-key"
os.environ["GEMMA_MODEL"] = ""
os.environ["GEMMA_THINKING"] = ""
