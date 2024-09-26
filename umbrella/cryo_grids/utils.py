from pydantic import BaseModel, validator, ValidationError, constr
from typing import Union, Optional, List, ClassVar
from rest_framework import status
from rest_framework.exceptions import APIException
from django.http import JsonResponse
import re

class UnprocessableEntity(APIException):
    status_code = 422  # Define the 422 status code here
    default_detail = 'Unprocessable entity.'

    def __init__(self, detail=None):
        if detail is None:
            detail = self.default_detail
        self.detail = detail

class CryoGridsQueryParams(BaseModel):
    q: Optional[List[dict[str, Union[List[Union[str, bool]], str, bool]]]] = None  # q parameter now expects a list of dictionaries
    
    # Define the allowed category names in camelCase
    ALLOWED_CATEGORIES: ClassVar[set[str]] = {"filterType", "puck", "user", "screeningSession", "msiSession", "project", "sort", "asc", "page", "pageSize", "status", "cassette", "sample", "date", "freezingPlan", "freezingSession", "date"}

    @validator('q')
    def validate_q(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise UnprocessableEntity(
                detail={"error": "q must be a list of filter objects"}
            )
        
        for item in value:
            if not isinstance(item, dict):
                raise UnprocessableEntity(
                    detail={"error": "Each item in 'q' must be a dictionary with 'category' and 'value'"}
                )
            
            category = item.get('category')
            item_value = item.get('value')

            # Ensure 'category' and 'value' keys exist
            if category is None or item_value is None:
                raise UnprocessableEntity(
                    detail={"error": "Each item in 'q' must have 'category' and 'value' keys"}
                )
            
            # Check if the category is in the allowed camelCase category names
            if category not in cls.ALLOWED_CATEGORIES:
                raise UnprocessableEntity(
                    detail={
                        "error": f"Invalid category: '{category}'.",
                        "message": f"Allowed categories are: {', '.join(cls.ALLOWED_CATEGORIES)}"
                    }
                )
            
            # Ensure the value is a string, list of strings, or boolean
            if isinstance(item_value, list):
                for val in item_value:
                    if not isinstance(val, (str, bool)):
                        raise UnprocessableEntity(
                            detail={"error": f"Invalid value in list for category '{category}': expected string or boolean."}
                        )
            elif not isinstance(item_value, (str, bool)):
                raise UnprocessableEntity(
                    detail={"error": f"Invalid value for category '{category}': expected string, boolean, or list of these."}
                )
        
        return value


## API Result
# Pagination metadata model
class PaginationMetadataModel(BaseModel):
    page: int
    pageSize: int
    totalPages: int
    totalResults: int

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
    category: constr(strip_whitespace=True)
    value: List[Union[constr(strip_whitespace=True), bool]]  # Accept both strings and booleans

    @validator('value', each_item=True)
    def validate_value(cls, v):
        # Check if the value is a string, if not, skip validation
        if isinstance(v, str):
            # Only validate strings
            if not re.match(r'^[\w\s.-]+$', v):
                raise ValueError('Invalid characters in value')
        return v

class QueryParams(BaseModel):
    q: Optional[List[FilterItem]] = []