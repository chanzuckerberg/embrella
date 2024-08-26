from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union


class CryoGridsQueryParams(BaseModel):
    project_name: Optional[Union[List[str], str]] = None
    cassette_name: Optional[Union[List[str], str]] = None
    grid_name: Optional[Union[List[str], str]] = None
    puck_name: Optional[Union[List[str], str]] = None
    user_name: Optional[Union[List[str], str]] = None
    sample_name: Optional[Union[List[str], str]] = None
    msi_session_name: Optional[Union[List[str], str]] = None
    screen_session_name: Optional[Union[List[str], str]] = None
    filter_type: Optional[str] = None
    trashed: Optional[str] = None

    @validator('filter_type')
    def validate_filter_type(cls, value):
        if not isinstance(value, str):
            raise ValueError("filter_type must be a string")
        value = value.upper().strip()
        if value not in {"AND", "OR"}:
            raise ValueError("filter_type must be either 'AND' or 'OR'")
        return value
    @validator('filter_type')
    def validate_filter_type(cls, value):
        if not isinstance(value, str):
            raise ValueError("filter_type must be a string")
        value = value.upper().strip()
        if value not in {"AND", "OR"}:
            raise ValueError("filter_type must be either 'AND' or 'OR'")
        return value

    @validator('*', pre=True)
    def split_comma_separated_values(cls, value):
        if isinstance(value, str) and ',' in value:
            return [v.strip() for v in value.strip('[]').split(',')]
        return value

    @validator('trashed')
    def validate_trashed(cls, value):
        if value not in {"true", "false"}:
            raise ValueError("trashed must be either 'true' or 'false'")
        return value

