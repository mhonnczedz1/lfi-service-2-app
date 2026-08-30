import httpx
import pytest

# Importing from src.main is what fails right now, and that is the point:
# the test file is written before the module exists.
from src.main import app, transform


# ---------------------------------------------------------------------------
# Pure-function tests. No app, no client, no I/O. These run in microseconds
# and are the reason `transform` was kept separate from the route handler.
# ---------------------------------------------------------------------------
def test_transform_doubles_its_input():
    assert transform(21) == 42


def test_transform_handles_zero():
    assert transform(0) == 0


def test_transform_handles_negatives():
    assert transform(-7) == -14


# ---------------------------------------------------------------------------
# HTTP-level tests. ASGITransport calls the app directly in-process: no
# socket, no port, no uvicorn. It also does NOT run lifespan events, which
# matters enormously for service-1 and not at all here.
#
# No @pytest.mark.asyncio decorator is needed because pyproject.toml sets
# asyncio_mode = "auto".
# ---------------------------------------------------------------------------
@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # yield, not return: everything after this runs as teardown, which is
        # what closes the client even if the test fails.
        yield c


async def test_healthz_returns_ok(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_process_returns_the_doubled_value(client):
    response = await client.post("/process", json={"value": 21})
    assert response.status_code == 200
    # Asserting the whole body, not just one field. That pins the response
    # shape, which the Kubernetes probes and service-1 both depend on.
    assert response.json() == {
        "service": "service-2",
        "input": 21,
        "result": 42,
    }


async def test_process_rejects_a_non_integer_value(client):
    response = await client.post("/process", json={"value": "not-a-number"})
    # 422, not 400 or 500. FastAPI validates against the Pydantic model before
    # the handler is ever called, so this is free rather than hand-written.
    assert response.status_code == 422
