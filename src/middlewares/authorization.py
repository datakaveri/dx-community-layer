import uuid
import json
import httpx
from jose import jwt
from sqlalchemy.future import select
from typing import Annotated, Literal, Optional
from datetime import datetime, timezone
from fastapi.security import HTTPBearer
from fastapi import Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security.utils import get_authorization_scheme_param
from jose.exceptions import JWTError, ExpiredSignatureError, JWTClaimsError, JWSError

from ..middlewares.logging import logger
from ..configs.env_config import env_config
from ..database.discussion.models import User as DiscussionUser
from ..database.challenge.models import User as ChallengeUser
from ..configs.redis_config import redis_client
from ..configs.db_config import get_challenge_db_session, get_discussion_db_session
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
        self.jwks_url = f"{env_config.KEYCLOAK_URL}/auth/realms/{env_config.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    async def fetch_jwks(self) -> dict:
        """Fetch JWKS from Keycloak asynchronously and cache in Redis"""
        # Check Redis cache first
        cached_jwks = await self.redis_client.get(self.JWKS_CACHE_KEY)
        if cached_jwks:
            return json.loads(cached_jwks)

        # Fetch JWKS from Keycloak
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                jwks = response.json()

            # Cache in Redis
            await self.redis_client.set(
                self.JWKS_CACHE_KEY, json.dumps(jwks), ex=self.JWKS_CACHE_TTL
            )
            return jwks

        except Exception as e:
            logger.error(f"Failed to fetch JWKS from Keycloak: {e}")
            raise CustomHttpException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="User authorization failed",
                error_code="INTERNAL_SERVER_ERROR",
                error_details="Failed to authorize user. Please contact developers.",
            )

    async def verify_token(self, token: str) -> dict:
        """Verify JWT, check expiry, and cache payload in Redis"""

        try:
            token_signature = token.split(".")[2]
        except Exception as e:
            logger.error(f"Failed to verify token: {e}")
            raise CustomHttpException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error_code="UNAUTHORIZED",
                error_details="Invalid token format",
            )

        # Check Redis token cache
        cached_payload = await self.redis_client.get(f"token:{token_signature}")
        if cached_payload:
            payload = json.loads(cached_payload)
            if (
                payload.get("exp")
                and datetime.now(timezone.utc).timestamp() > payload["exp"]
            ):
                await self.redis_client.delete(f"token:{token_signature}")
                raise CustomHttpException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message="Unauthorized access",
                    error_code="UNAUTHORIZED",
                    error_details="Token expired. Please login again.",
                )
            return payload

        # Decode token using JWKS
        jwks = await self.fetch_jwks()
        try:
            unverified_header = jwt.get_unverified_header(token)
            key = next(
                (k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None
            )
            if not key:
                raise CustomHttpException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message="Unauthorized access",
                    error_code="UNAUTHORIZED",
                    error_details="Invalid token key.",
                )

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=env_config.KEYCLOAK_AUDIENCE,
                issuer=env_config.KEYCLOAK_ISSUER,
            )

            # Cache payload in Redis until token expiry
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                ttl = int(exp_timestamp - datetime.now(timezone.utc).timestamp())
                await self.redis_client.set(
                    f"token:{token_signature}", json.dumps(payload), ex=ttl
                )

            return payload

        except ExpiredSignatureError:
            raise CustomHttpException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error_code="UNAUTHORIZED",
                error_details="Token expired. Please login again.",
            )
        except (JWTError, JWTClaimsError, JWSError):
            raise CustomHttpException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Unauthorized access",
                error_code="UNAUTHORIZED",
                error_details="Invalid token. Please provide a valid Bearer token.",
            )

    def get_highest_role(self, roles: list[str]) -> str:
        """
        Returns the highest role in the list of roles.
        """
        return (
            UserRole.COS_ADMIN
            if UserRole.COS_ADMIN.value in roles
            else UserRole.CONSUMER
        )

    async def update_user_info(
        self,
        user_id: str,
        name: str,
        email: str,
        service: Literal["discussion", "challenge"],
        db_session: AsyncSession,
    ) -> uuid.UUID:
        """Ensure a User row exists and is up to date.

        Resolves collisions by email: if no row by id, but a row exists by email,
        reuse that user and return its id instead of inserting a duplicate user.
        """
        # Prefer a stable mapping cache from external id -> effective internal id
        idmap_key = f"user:idmap:{user_id}"
        cached_map = await self.redis_client.get(idmap_key)
        User = ChallengeUser if service == "challenge" else DiscussionUser

        if cached_map:
            try:
                mapped_id = uuid.UUID(json.loads(cached_map))
                # best-effort: ensure user exists; if not, fall through to DB resolution
                res = await db_session.execute(select(User).where(User.id == mapped_id))
                if res.scalars().first():
                    # Optionally refresh profile if changed
                    user_row = res.scalars().first()
                    if user_row:
                        changed = False
                        if user_row.name != name:
                            user_row.name = name
                            changed = True
                        if user_row.email != email:
                            user_row.email = email
                            changed = True
                        if changed:
                            await db_session.commit()
                    return mapped_id
            except Exception:
                pass

        # Lookup by id
        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        effective_user_id: uuid.UUID
        try:
            if user:
                # Update fields if changed
                user.name = name
                user.email = email
                effective_user_id = user.id
            else:
                # Fallback: lookup by email to avoid unique email violation
                by_email_res = await db_session.execute(
                    select(User).where(User.email == email)
                )
                by_email = by_email_res.scalars().first()
                if by_email:
                    # Reuse existing user by email; update name only
                    by_email.name = name
                    effective_user_id = by_email.id
                else:
                    # Create new user with provided id
                    new_user = User(id=user_id, name=name, email=email)
                    db_session.add(new_user)
                    effective_user_id = uuid.UUID(str(user_id))

            await db_session.commit()

            # Cache under both keys (provided id and effective id) for 1 hour
            payload = json.dumps({"name": name, "email": email})
            await self.redis_client.set(f"user:{effective_user_id}", payload, ex=3600)
            await self.redis_client.set(
                idmap_key, json.dumps(str(effective_user_id)), ex=3600
            )

            return uuid.UUID(str(effective_user_id))
        except Exception as e:
            logger.error(f"Failed to update user info: {e}")
            # Do not block request on cache/ensure issues; fallback to provided id
            return uuid.UUID(str(user_id))

    async def __call__(
        self,
        request: Request,
        Authorization: Annotated[
            Optional[str], Header(description="Bearer token")
        ] = None,
        discussion_db_session: AsyncSession = Depends(get_discussion_db_session),
        challenge_db_session: AsyncSession = Depends(get_challenge_db_session),
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

        if request.url.path.startswith("/challenge"):
            db_session = challenge_db_session
            service = "challenge"
        else:
            db_session = discussion_db_session
            service = "discussion"

        effective_user_id = await self.update_user_info(
            user_id=user_id,
            name=user_name,
            email=user_email,
            service=service,
            db_session=db_session,
        )

        return AuthorizationData(
            user_id=effective_user_id,
            username=user_name,
            email=user_email,
            user_role=self.get_highest_role(user_roles),
        )


http_bearer_header = HttpBearerHeader()
http_bearer_header_public = HttpBearerHeader(public=True)
