import re
from typing import ClassVar, List, Optional, Union

from pydantic import BaseModel, constr, validator
from rest_framework.exceptions import APIException


class FilterItem(BaseModel):
    category: constr(strip_whitespace=True)
    value: List[Union[constr(strip_whitespace=True), bool, None]]  # Accept strings, booleans, and None

    @validator('value', each_item=True)
    def validate_value(cls, v):
        # Skip validation if value is None
        if v is None:
            return v
        # Check if the value is a string, if not, skip string validation
        if isinstance(v, str):
            # Only validate strings
            if not re.match(r'^[\w\s.-]+$', v):
                raise ValueError('Invalid characters in value')
        return v
class QueryParams(BaseModel):
    q: Optional[List[FilterItem]] = []

class UnprocessableEntity(APIException):
    status_code = 422  # Define the 422 status code here
    default_detail = 'Unprocessable entity.'

    def __init__(self, detail=None):
        if detail is None:
            detail = self.default_detail
        self.detail = detail

class tomoQueryParams(BaseModel):
    q: Optional[List[dict[str, Union[List[Union[str, bool, None, int]], str, bool, None, int]]]] = None  # Allow int as well in value


    # Define the allowed category names in camelCase
    ALLOWED_CATEGORIES: ClassVar[set[str]] = {"filterType", "updatedAt", "tomogram", "user","userName", "procPlan", "msiSession", "project", "sort", "asc", "page", "pageSize", "status", "sample","date", "json", 'grid', 'tomograms','screeningSession'}

    @validator('q')
    def validate_q(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("q must be a list of filter objects")

        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Each item in 'q' must be a dictionary with 'category' and 'value'")

            category = item.get('category')
            item_value = item.get('value')

            # Ensure 'category' and 'value' keys exist
            if category is None or item_value is None:
                raise ValueError("Each item in 'q' must have 'category' and 'value' keys")

            # Check if the category is in the allowed camelCase category names
            if category not in cls.ALLOWED_CATEGORIES:
                raise ValueError(f"Invalid category: '{category}'. Allowed categories are: {', '.join(cls.ALLOWED_CATEGORIES)}")

            # Ensure the value is a string, list of strings/booleans/None/ints, boolean, or int
            if isinstance(item_value, list):
                for val in item_value:
                    if not isinstance(val, (str, bool, type(None), int)):
                        raise ValueError(f"Invalid value in list for category '{category}': expected string, boolean, int, or None.")
            elif not isinstance(item_value, (str, bool, type(None), int)):
                raise ValueError(f"Invalid value for category '{category}': expected string, boolean, int, or None.")

        return value
    

class annotationQueryParams(BaseModel):
    q: Optional[List[dict[str, Union[List[Union[str, bool, None, int]], str, bool, None, int]]]] = None  # Allow int as well in value


    # Define the allowed category names in camelCase
    ALLOWED_CATEGORIES: ClassVar[set[str]] = {"filterType", "tomogram", "user","userName", "procPlan", "msiSession", "project", "sort", "asc", "page", "pageSize", "status", "sample","date", "json", 'grid', 'tomograms','screeningSession'}

    @validator('q')
    def validate_q(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("q must be a list of filter objects")

        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Each item in 'q' must be a dictionary with 'category' and 'value'")

            category = item.get('category')
            item_value = item.get('value')

            # Ensure 'category' and 'value' keys exist
            if category is None or item_value is None:
                raise ValueError("Each item in 'q' must have 'category' and 'value' keys")

            # Check if the category is in the allowed camelCase category names
            if category not in cls.ALLOWED_CATEGORIES:
                raise ValueError(f"Invalid category: '{category}'. Allowed categories are: {', '.join(cls.ALLOWED_CATEGORIES)}")

            # Ensure the value is a string, list of strings/booleans/None/ints, boolean, or int
            if isinstance(item_value, list):
                for val in item_value:
                    if not isinstance(val, (str, bool, type(None), int)):
                        raise ValueError(f"Invalid value in list for category '{category}': expected string, boolean, int, or None.")
            elif not isinstance(item_value, (str, bool, type(None), int)):
                raise ValueError(f"Invalid value for category '{category}': expected string, boolean, int, or None.")

        return value

## API Result
# Pagination metadata model
class PaginationMetadataModel(BaseModel):
    page: Optional[int] = None
    pageSize: Optional[int] = None
    totalPages: Optional[int] = None
    totalResults: Optional[int] = None

class SortMetadataModel(BaseModel):
    sort: Optional[str] = None
    asc: Optional[bool] = None

class TomogramModel(BaseModel):
    id: Optional[int]
    name: Optional[str]
    url: Optional[str]

class AnnotationModel(BaseModel):
    id: Optional[int]
    name: Optional[str]
    url: Optional[str]
    updatedAt: Optional[str] = None
    notes: Optional[str] = None

class ProcPlanModel(BaseModel):
    id: Optional[int]
    name: Optional[str]
    url: Optional[str]

class JsonModel(BaseModel):
    id: Optional[int]
    name: Optional[str]

class GridModel(BaseModel):
    id: Optional[int]
    name: Optional[str]
    trashed: Optional[bool]
    url: Optional[str]
    createdAt: Optional[str] = None

class ProjectModel(BaseModel):
    id: Optional[int]
    name: Optional[str]
    url: Optional[str]

class UserModel(BaseModel):
    id: Optional[int]
    name: Optional[str]

class MSISessionModel(BaseModel):
    id: Optional[int]  # id is now optional
    name: Optional[str]  # name is now optional
    url: Optional[str]  # url is optional

class ProcRunModel(BaseModel):
    id: Optional[int]
    notes: Optional[str]
    updatedAt: Optional[str] = None

class InputTomogramModel(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    url: Optional[str] = None

class ResponseModel(BaseModel):
    tomograms: Optional[TomogramModel] = None
    procPlan: Optional[ProcPlanModel] = None
    procRun: Optional[ProcRunModel] = None
    json: Optional[JsonModel] = None
    grid: Optional[GridModel] = None
    project: Optional[ProjectModel] = None
    user: Optional[UserModel] = None
    msiSession: Optional[MSISessionModel] = None

class AnnotationResponseModel(BaseModel):
    annotations: Optional[AnnotationModel] = None
    procPlan: Optional[ProcPlanModel] = None
    inputTomogram: Optional[InputTomogramModel] = None
    json: Optional[JsonModel] = None
    grid: Optional[GridModel] = None
    project: Optional[ProjectModel] = None
    user: Optional[UserModel] = None
    msiSession: Optional[MSISessionModel] = None


# Processing Data Management Models
class ProcessingDataQueryParams(BaseModel):
    q: Optional[List[dict[str, Union[List[Union[str, bool, None, int]], str, bool, None, int]]]] = None

    # Define the allowed category names in camelCase
    ALLOWED_CATEGORIES: ClassVar[set[str]] = {
        "filterType", "user", "userName", "msiSession", "dataType",
        "preserveStatus", "sort", "asc", "page", "pageSize",
        "createdAt", "source",
    }

    @validator('q')
    def validate_q(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("q must be a list of filter objects")

        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Each item in 'q' must be a dictionary with 'category' and 'value'")

            category = item.get('category')
            item_value = item.get('value')

            # Ensure 'category' and 'value' keys exist
            if category is None or item_value is None:
                raise ValueError("Each item in 'q' must have 'category' and 'value' keys")

            # Check if the category is in the allowed camelCase category names
            if category not in cls.ALLOWED_CATEGORIES:
                raise ValueError(f"Invalid category: '{category}'. Allowed categories are: {', '.join(cls.ALLOWED_CATEGORIES)}")

            # Ensure the value is a string, list of strings/booleans/None/ints, boolean, or int
            if isinstance(item_value, list):
                for val in item_value:
                    if not isinstance(val, (str, bool, type(None), int)):
                        raise ValueError(f"Invalid value in list for category '{category}': expected string, boolean, int, or None.")
            elif not isinstance(item_value, (str, bool, type(None), int)):
                raise ValueError(f"Invalid value for category '{category}': expected string, boolean, int, or None.")

        return value


class ProcessingDataModel(BaseModel):
    id: Optional[int]
    name: Optional[str]
    path: Optional[str]
    dataType: Optional[str]
    sizeBytes: Optional[int]
    sizeDisplay: Optional[str]
    createdAt: Optional[str]
    modifiedAt: Optional[str]
    fileCreatedAt: Optional[str]
    user: Optional[UserModel]
    msiSession: Optional[MSISessionModel]
    source: Optional[str]
    preserveStatus: Optional[str]
    statusUpdatedAt: Optional[str]
    statusUpdatedBy: Optional[UserModel]
    notes: Optional[str]
    contentType: Optional[str]
    objectId: Optional[int]


class ProcessingDataResponseModel(BaseModel):
    data: Optional[ProcessingDataModel] = None
    user: Optional[UserModel] = None
    msiSession: Optional[MSISessionModel] = None


class StorageStatsModel(BaseModel):
    totalSizeBytes: Optional[int]
    totalSizeDisplay: Optional[str]
    countByType: Optional[dict]
    sizeByType: Optional[dict]
    countByStatus: Optional[dict]
    sizeByStatus: Optional[dict]
    countByUser: Optional[dict]
    sizeByUser: Optional[dict]


class BulkActionRequest(BaseModel):
    ids: List[int]
    status: constr(strip_whitespace=True)

    @validator('status')
    def validate_status(cls, v):
        if v not in ['preserve', 'delete', 'unset']:
            raise ValueError('Status must be one of: preserve, delete, unset')
        return v
