from pydantic import BaseModel, validator, ValidationError, constr
from typing import Union, Optional, List, ClassVar
from rest_framework import status
from rest_framework.exceptions import APIException
from django.http import JsonResponse
import re

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