from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # TODO: initialise DB pool, Redis connection, arq worker pool
    yield
    # TODO: tear down resources


def create_app() -> FastAPI:
    application = FastAPI(
        title="DailyLoadout API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
