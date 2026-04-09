from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str = Field(alias="displayName")
    role: str

    model_config = {"populate_by_name": True, "from_attributes": True}


class SessionOut(BaseModel):
    user: UserOut

    model_config = {"populate_by_name": True, "from_attributes": True}
