from pydantic import BaseModel


class SettingsResponse(BaseModel):
    settings: dict


class SettingsUpdateRequest(BaseModel):
    settings: dict
