from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    """Base for response schemas populated from ORM objects."""

    model_config = ConfigDict(from_attributes=True)
