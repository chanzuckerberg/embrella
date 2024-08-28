from pydantic import BaseModel,validator
from typing import  Union, Optional, List

class CryoGridsQueryParams(BaseModel):
    project_name: Optional[Union[List[str], str]] = None
    cassette_name: Optional[Union[List[str], str]] = None
    puck_name: Optional[Union[List[str], str]] = None
    user_name: Optional[Union[List[str], str]] = None
    sample_name: Optional[Union[List[str], str]] = None
    msi_session_name: Optional[Union[List[str], str]] = None
    screen_session_name: Optional[Union[List[str], str]] = None
    filter_type: Optional[str] = None
    trashed: Optional[str] = None
    month: Optional[int] = None
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
        if value not in {"True", "False", "true", "false"}:
            raise ValueError("trashed must be either 'true' or 'false'")
        return value

    @validator('month')
    def validate_month(cls, value):
        if value not in [1, 3, 6, None]:
            raise ValueError('Month must be 1, 3, 6, or None')
        return value

## API Result

class SampleModel(BaseModel):
    id: int
    name: str
    url: str  # Changed from HttpUrl to str

class FreezingPlanModel(BaseModel):
    id: int
    sample: List[SampleModel]

class FreezingSessionModel(BaseModel):
    id: int
    createdAt: Optional[str] = None

class MSISessionModel(BaseModel):
    id: int
    name: str
    url: str  # Changed from HttpUrl to str

class GridModel(BaseModel):
    id: int
    name: str
    trashed: bool
    url: str  # Changed from HttpUrl to str
    createdAt: Optional[str] = None

class CassetteModel(BaseModel):
    name: Optional[str] = None

class ProjectModel(BaseModel):
    id: int
    name: str
    url: str  # Changed from HttpUrl to str

class PuckModel(BaseModel):
    name: str

class UserModel(BaseModel):
    id: int
    name: str

class CryoGridResultModel(BaseModel):
    grid: GridModel
    cassette: CassetteModel
    project: ProjectModel
    puck: PuckModel
    user: UserModel
    freezingPlan: FreezingPlanModel
    freezingSession: FreezingSessionModel
    screeningSession: Optional[str] = None
    msiSession: List[MSISessionModel]

class CryoGridResponseModel(BaseModel):
    result: List[CryoGridResultModel]


## available set API
class DateRangeModel(BaseModel):
    range: str
    count: int

class FilterModel(BaseModel):
    name: str
    count: int

class FiltersModel(BaseModel):
    project: List[FilterModel]
    puck: List[FilterModel]
    sample: List[FilterModel]
    user: List[FilterModel]
    cassette: List[FilterModel]
    screenSession: List[FilterModel]
    msiSession: List[FilterModel]
    status: List[FilterModel]
    date: List[DateRangeModel]

class ApiResponseModel(BaseModel):
    filters: FiltersModel
