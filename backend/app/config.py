import os

from dotenv import load_dotenv

load_dotenv()

# Root directory the storage abstraction writes to. In docker-compose this
# should be a mounted volume shared between the API container and (if you
# ever add one) a static file server. Locally it defaults to a `storage`
# folder at the repo root so it's easy to poke at while developing.
STORAGE_ROOT = os.getenv(
    "STORAGE_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "storage"),
)

# Key (path, relative to STORAGE_ROOT) the published catalogue is written to.
CATALOG_KEY = os.getenv("CATALOG_KEY", "catalog/catalog.json")
