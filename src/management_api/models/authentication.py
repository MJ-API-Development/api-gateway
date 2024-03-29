from pydantic import BaseModel, validator, root_validator


class LoginData(BaseModel):
    """
    Model for user login data
    Attributes:
        email (str): User's email address
        password (str): User's password
    """

    email: str
    password: str

    @classmethod
    @validator('email')
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError('Not a Valid Email Address')
        return v

    class Config:
        title = "Login Model"
        extra = "forbid"


class AuthorizationRequest(BaseModel):
    """
    Model for authorization request

    Attributes:
        uuid (str): Client's UUID
        path (str): Path login or authorization Request
        method (str): Method of request which will be used to access the path (default: 'GET')
    """
    uuid: str
    path: str
    method: str

    @root_validator
    def validate_not_empty(cls, values):
        for key, value in values.items():
            if not value:
                raise ValueError(f"{key} must not be empty")
        return values

    class Config:
        title = "User Authorization Model"
        extra = "allow"
