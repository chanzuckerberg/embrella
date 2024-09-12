from pydantic import BaseModel,validator, constr
from typing import  Union, Optional, List
import re

class CryoGridsQueryParams(BaseModel):
    q: Optional[List[dict[str, Union[List[str], str, bool]]]] = None  # q parameter now expects a list of dictionaries
    # page_size: Optional[int] = None
    # sort: Optional[str] = None
    # asc: Optional[bool] = False

    @validator('q')
    def validate_q(cls, value):
        # Ensure that 'q' is a list of dictionaries with 'category' and 'value'
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("q must be a list of filter objects")
        for item in value:
            if 'category' not in item or 'value' not in item:
                raise ValueError("Each item in 'q' must have 'category' and 'value'")
        return value

    # @validator('page_size')
    # def validate_page_size(cls, value):
    #     if value is not None and value <= 0:
    #         raise ValueError("page_size must be a positive integer")
    #     return value
    
    # @validator('sort')
    # def validate_sort(cls, value):
    #     if value is not None and not isinstance(value, str):
    #         raise ValueError("sort must be a valid string")
    #     # Only allow 'updatedAt' as the valid sort field
    #     if value and value != 'updatedAt':
    #         raise ValueError(f"Invalid sort field '{value}', must be 'updatedAt'")
    #     return 'updated_on' if value == 'updatedAt' else value

    # @validator('asc')
    # def validate_asc(cls, value):
    #     if value is None:
    #         return False
    #     if not isinstance(value, bool):
    #         raise ValueError("asc must be a boolean value")
    #     return value
## API Result
# Pagination metadata model
class PaginationMetadataModel(BaseModel):
    page: int
    page_size: int
    total_pages: int
    total_results: int

class SortMetadataModel(BaseModel):
    sort: Optional[str] 
    asc: bool

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
    updatedAt: Optional[str] = None

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
    pagination: PaginationMetadataModel
    sort: Optional[SortMetadataModel] = None 
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



# filterlist endpoint
class FilterItem(BaseModel):
    category: constr(strip_whitespace=True, to_lower=True)
    value: List[constr(strip_whitespace=True)]

    @validator('value', each_item=True)
    def validate_value(cls, v):
        if not re.match(r'^[\w\s.-]+$', v):
            raise ValueError('Invalid characters in value')
        return v

class QueryParams(BaseModel):
    q: Optional[List[FilterItem]] = []
