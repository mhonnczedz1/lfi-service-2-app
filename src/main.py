from fastapi import FastAPI
from pydantic import BaseModel

# No lifespan handler, unlike service-1. This service opens no connections to
# anything, so there is nothing to set up or tear down.
app = FastAPI(title="service-2-worker", version="1.0.0")


# ---------------------------------------------------------------------------
# Request and response schemas. Declaring these buys three things at once:
# input validation, the 422 on bad input, and the OpenAPI docs at /docs.
# ---------------------------------------------------------------------------
class ProcessRequest(BaseModel):
    # `int`, not `str`. This single annotation is what rejects "not-a-number".
    value: int


class ProcessResponse(BaseModel):
    service: str
    input: int
    result: int


def transform(value: int) -> int:
    """The stub's entire business logic: deliberately trivial and pure.

    Pure so it is testable without any I/O, which is what lets service-2
    stay free of a database connection.
    """
    return value * 2


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness. Has no dependencies, so it must never fail while the
    process is alive."""
    # No readiness endpoint here, deliberately. Readiness answers "can I reach
    # my dependencies", and this service has none, so it would duplicate
    # liveness. service-1 does need both.
    return {"status": "ok"}


# `def`, not `async def`. There is no await in the body, so FastAPI runs this
# in a threadpool and nothing blocks the event loop either way.
@app.post("/process", response_model=ProcessResponse)
def process(request: ProcessRequest) -> ProcessResponse:
    return ProcessResponse(
        # Echoing the service name is what lets service-1's response prove the
        # internal DNS hop actually happened rather than being faked locally.
        service="service-2",
        input=request.value,
        result=transform(request.value),
    )
