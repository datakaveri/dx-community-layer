import uuid
import json
from typing import Annotated, Optional
from datetime import datetime, timezone

import httpx
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError, JWSError
from fastapi import Depends, Header, status
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database.discussion.models import User
from ..middlewares.logging import logger
from ..configs.env_config import env_config
from ..configs.db_config import get_discussion_db_session 
from ..configs.redis_config import redis_client
from ..schemas.custom_responses import CustomHttpException
from ..schemas.default_schemas import AuthorizationData, UserRole


class HttpBearerHeader(HTTPBearer):
    JWKS_CACHE_KEY = "jwks:public_keys"
    JWKS_CACHE_TTL = 900  # 15 minutes

    def __init__(
        self,
        *,
        bearerFormat: str = "JWT",
        scheme_name: str = "Bearer",
        description: str = "Bearer token authentication using JWT.",
        auto_error: bool = True,
        public: bool = False,
    ):
        super().__init__(
            bearerFormat=bearerFormat,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )
        self.public = public
        self.redis_client = redis_client
        self.jwks_url = (
            f"{env_config.KEYCLOAK_URL}/auth/realms/"
            f"{env_config.KEYCLOAK_REALM}/protocol/openid-connect/certs"
        )

    ...
    # (all your existing methods stay the same)
    ...

    async def __call__(
        self,
        Authorization: Annotated[
            Optional[str], Header(description="Bearer token")
        ] = None,
        session: AsyncSession = Depends(get_discussion_db_session),  # ✅ UPDATED
    ) -> AuthorizationData:
        if (not Authorization) and self.public:
            return AuthorizationData(
                user_id=None,
                username="public",
                email="Public",
                user_role=UserRole.CONSUMER,
            )

        if not Authorization:
            raise CustomHttpException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error_code="UNAUTHORIZED",
                error_details="Missing Authorization header.",
            )

        scheme, access_token = get_authorization_scheme_param(Authorization)
        if scheme.lower() != "bearer" or not access_token:
            if self.public:
                return AuthorizationData(
                    user_id=None,
                    username="public",
                    email="Public",
                    user_role=UserRole.CONSUMER,
                )

            raise CustomHttpException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error_code="UNAUTHORIZED",
                error_details="Invalid Authorization header. Provide Bearer token.",
            )

        payload = await self.verify_token(access_token)

        user_id = payload.get("sub")
        user_name = payload.get("name")
        user_email = payload.get("email")
        user_roles = payload.get("realm_access", {}).get("roles", [])

        if not all([user_id, user_name, user_email, user_roles]):
            if self.public:
                return AuthorizationData(
                    user_id=None,
                    username="public",
                    email="Public",
                    user_role=UserRole.CONSUMER,
                )

            raise CustomHttpException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error_code="UNAUTHORIZED",
                error_details="Token missing required user info.",
            )

        effective_user_id = await self.update_user_info(
            user_id, user_name, user_email, session
        )

        return AuthorizationData(
            user_id=effective_user_id,
            username=user_name,
            email=user_email,
            user_role=self.get_highest_role(user_roles),
        )


http_bearer_header = HttpBearerHeader()
http_bearer_header_public = HttpBearerHeader(public=True)
