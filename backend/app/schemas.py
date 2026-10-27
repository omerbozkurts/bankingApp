from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    # Same rules as the app and the legacy desktop version: 9-digit customer no, 6-digit password.
    customer_no: str = Field(pattern=r"^\d{9}$", examples=["123456789"])
    password: str = Field(pattern=r"^\d{6}$", examples=["123456"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_no: str
    full_name: str


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iban: str
    balance_kurus: int
    goal_kurus: int | None
