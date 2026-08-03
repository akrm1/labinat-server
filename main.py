# بسم الله الرحمن الرحيم

import os

from app import server

if __name__ == "__main__":
    config = server.start()
    options = config.get("server") or {}

    host = os.getenv("LABINAT_HOST", options.get("host", "0.0.0.0"))
    port = int(os.getenv("LABINAT_PORT", options.get("port", 8000)))
    reload = os.getenv("LABINAT_RELOAD", str(options.get("reload", False))).lower() in {"1", "true", "yes"}

    try:
        server.run(host=host, port=port, reload=reload)
    finally:
        server.shutdown()

# الحمد لله رب العالمين
