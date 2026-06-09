from __future__ import annotations

from digest.config import load_local_env, setup_logging
from digest.observability import init_observability
from digest.scheduled import deliver_scheduled_digest


def main() -> None:
    load_local_env()
    init_observability()
    setup_logging()
    deliver_scheduled_digest()


if __name__ == "__main__":
    main()
