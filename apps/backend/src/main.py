import importlib

from core.observability import configure_observability


# Configure OpenTelemetry/Azure Monitor before importing FastAPI/Starlette.
configure_observability()

if __package__:
    app = importlib.import_module(f"{__package__}.app").app
else:  # pragma: no cover - supports PYTHONPATH=./src execution
    app = importlib.import_module("app").app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
