from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from agent.api.v1_routes import router as v1_router
from agent.core.capabilities import capability_manager
from agent.utils.logging_config import logger


def create_agent_app() -> FastAPI:
    # Ensure default features and actions are registered in ActionRegistry
    capability_manager.register_default_features()

    app = FastAPI(
        title="LAN Office Control Agent",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
    )

    # Include versioned router
    app.include_router(v1_router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Agent Exception on {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error_code": "EXECUTION_FAILED",
                "message": "An internal agent error occurred.",
            },
        )

    return app
