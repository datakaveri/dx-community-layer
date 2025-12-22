from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .middlewares.logging import logger
from .configs.env_config import env_config
from .docs import (
    docs_summary,
    docs_description,
    docs_tags_metadata,
    generate_code_samples,
)
from .routes.utility import router as utility_router
from .routes.discussion.root import router as discussion_router
from .routes.challenge.root import router as challenge_router
from .schemas.custom_responses import CustomHttpException, CustomJSONResponse


app = FastAPI()


# Set up CORS (Cross-Origin Resource Sharing)
origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5003",
    "http://localhost:5003",
    "http://localhost:4007",
    "http://127.0.0.1:4007",
    "http://localhost:4200",
    "https://staging.catalogue.tgdex.iudx.io",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Encoding",
        "Accept-Language",
        "Authorization",
        "Connection",
        "Connection-Length",
        "Connection-Type",
        "Keep-Alive",
        "Content-Length",
        "Content-Type",
        "Cookie",
        "Date",
        "Host",
        "Origin",
        "Referer",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "User-Agent",
        "Sec-Ch-Ua-Mobile",
        "Sec-Ch-Ua-Platform",
    ],
)

# Routes
SERVICES = {
    "DISCUSSION": discussion_router,
    "CHALLENGE": challenge_router,
}
app.include_router(router=utility_router)

for service, router in SERVICES.items():
    if service in env_config.ACTIVATED_SERVICES:
        app.include_router(router=router)


# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = [
        {"field": ".".join(e["loc"]), "error": e["msg"]} for e in exc.errors()
    ]
    response = {
        "success": False,
        "status_code": 422,
        "message": "Validation Error(s)",
        "data": None,
        "error": {"code": "VALIDATION_ERROR", "details": error_details},
        "meta": None,
    }
    return JSONResponse(status_code=422, content=response)


# Custom handler for internal server errors
@app.exception_handler(Exception)
async def internal_server_error_handler(request: Request, exc: Exception):
    # Log the error for debugging (optional)
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    # Standardized response for 500 errors
    response = {
        "success": False,
        "status_code": 500,
        "message": "Internal Server Error",
        "data": None,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "details": "Something went wrong. Please contact developers if the issue persists.",
        },
        "meta": None,
    }
    return JSONResponse(status_code=500, content=response)


# Custom handler for custom HTTP exceptions
@app.exception_handler(CustomHttpException)
async def custom_http_exception_handler(request: Request, exc: CustomHttpException):
    return CustomJSONResponse(**exc.detail, status_code=exc.status_code)


# Custom OpenAPI schema generator
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=env_config.PROJECT_NAME,
        version=env_config.INSTANCE.upper(),
        summary=docs_summary,
        description=docs_description,
        tags=docs_tags_metadata,
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png",
    }
    openapi_schema["x-tagGroups"] = [
        {
            "name": "Utility",
            "tags": [
                "Utility APIs",
            ],
        },
        {
            "name": "Discussion",
            "tags": [
                "Discussion APIs",
                "Discussion - Admin APIs",
                "Discussion - Search APIs",
                "Discussion - Attachment APIs",
                "Discussion - Comment APIs",
            ],
        },
        {
            "name": "Challenge",
            "tags": [
                "Challenge APIs",
                "Challenge - Admin APIs",
                "Challenge - Attachment APIs",
                "Challenge - Submission APIs",
            ],
        },
    ]

    components = openapi_schema.get("components", {})
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if operation["summary"] in ["Create Discussion"]:
                operation["responses"].pop("200", None)
            if method in {"get", "post", "put", "delete", "patch"}:
                generate_code_samples(path, method, operation, components)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Seting the custom OpenAPI function
app.openapi = custom_openapi
