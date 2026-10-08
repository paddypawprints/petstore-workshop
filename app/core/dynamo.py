from typing import Any

import boto3

from app.core.config import get_settings

_dynamodb: Any = None


def table(name: str) -> Any:
    # Created on first use so importing the app (in tests) never touches AWS.
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=get_settings().aws_default_region)
    return _dynamodb.Table(name)
