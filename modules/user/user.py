import uuid
from dataclasses import field, dataclass
from typing import Dict
from json import loads, dumps
from smdb_api import Privilege


@dataclass
class User:
    """
    Representation a user as the core handles it

    privilege: Privilege - The privilege the user holds
    connector_ids: Dict[str, str] - The different IDs across different connectors.
    UUID: str - A UUID for identification within the core
    """
    privilege: Privilege = field(compare=False)
    connector_ids: Dict[str, str] = field(compare=False)
    UUID: str = field(default_factory=lambda: str(uuid.uuid1()))

    def get_connector_id_for_connector(self, connector: str) -> str | None:
        return self.connector_ids.get(connector)

    def to_json(self) -> str:
        data = {'privilege': self.privilege, 'connector_ids': self.connector_ids, 'UUID': self.UUID}
        return dumps(data)

    @staticmethod
    def from_json(json: str) -> 'User':
        _dict = loads(json)
        for key in ['privilege', 'connector_ids', 'UUID']:
            if key not in _dict.keys():
                raise KeyError(f'Json missing key {key}. All keys need to be present when loading from Json')

        return User(_dict['privilege'], _dict['connector_ids'], _dict['UUID'])