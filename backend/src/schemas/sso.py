from typing import List, Optional
from pydantic import BaseModel, Field


class LdapLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class OidcAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str
    provider: str = "oidc"


class OidcCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1)
    state: Optional[str] = None


class AuthProviderStatusResponse(BaseModel):
    local_enabled: bool = True
    ldap_enabled: bool
    oidc_enabled: bool
    providers: List[str]
