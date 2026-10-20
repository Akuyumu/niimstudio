from .lifecycle import mark

mark("python_started")
from .app import main  # noqa: E402

raise SystemExit(main())
