"""Persistence primitives with DynamoDB and explicit local-mode behavior."""
import json
from typing import Any, Optional, TypeVar

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from backend.config import settings

ModelT = TypeVar("ModelT", bound=BaseModel)


class DynamoRepository:
    """Persist Pydantic records in DynamoDB when local mode is disabled."""

    def __init__(self, table_name: str, key_name: str, sort_key: Optional[str] = None):
        self.table_name = table_name
        self.key_name = key_name
        self.sort_key = sort_key
        self._table = None
        if not settings.use_local_mode:
            self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
                table_name
            )

    def put(self, record: BaseModel, key: str, condition: Optional[str] = None) -> None:
        if self._table is None:
            return
        item = json.loads(record.model_dump_json())
        item = {key: value for key, value in item.items() if value is not None}
        item[self.key_name] = key
        key_values = {self.key_name: key}
        if self.sort_key:
            sort_value = item.get(self.sort_key)
            if sort_value is None:
                raise ValueError(f"Record is missing DynamoDB sort key {self.sort_key}")
            key_values[self.sort_key] = sort_value
        kwargs: dict[str, Any] = {"Item": item}
        if condition:
            kwargs["ConditionExpression"] = condition
        try:
            self._table.put_item(**kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Unable to persist {self.table_name} record") from exc

    def get(self, key: str, model_type: type[ModelT]) -> Optional[ModelT]:
        if self._table is None:
            return None
        try:
            key_values = {self.key_name: key}
            if self.sort_key:
                raise ValueError("get requires a sort key for composite-key tables")
            response = self._table.get_item(Key=key_values)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Unable to read {self.table_name} record") from exc
        item = response.get("Item")
        return model_type.model_validate(item) if item else None

    def update_fields(self, key: str, fields: dict[str, Any], condition: Optional[str] = None) -> None:
        if self._table is None:
            return
        names = {f"#field{index}": name for index, name in enumerate(fields)}
        values = {f":value{index}": value for index, value in enumerate(fields.values())}
        expression = ", ".join(
            f"{name} = :value{index}" for index, name in enumerate(names)
        )
        kwargs: dict[str, Any] = {
            "Key": {self.key_name: key},
            "UpdateExpression": f"SET {expression}",
            "ExpressionAttributeNames": names,
            "ExpressionAttributeValues": values,
        }
        if condition:
            kwargs["ConditionExpression"] = condition
            values[":unused"] = False
        try:
            self._table.update_item(**kwargs)
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Unable to update {self.table_name} record") from exc
