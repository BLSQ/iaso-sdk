from datetime import datetime
import requests
import operator
import os
from dataclasses import dataclass, field, asdict
from typing import List, Literal, Union, Optional


@dataclass
class ProjectModel:
    id: int
    name: str
    app_id: str
    needs_authentication: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class OrgUnitTypeModel:
    id: int
    name: str
    short_name: str
    depth: int
    units_count: int
    created_at: datetime
    updated_at: datetime
    projects: List[ProjectModel] = field(default_factory=list)


@dataclass
class GroupModel:
    id: int
    name: str
    org_unit_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class SimpleOrgUnitModel:
    id: int
    name: str
    parent_id: int
    org_unit_type_id: int
    org_unit_type_name: str
    created_at: datetime
    updated_at: datetime
    validation_status: Literal["NEW", "VALID", "REJECTED"] = "NEW"


@dataclass
class OrgUnitModel:
    id: int
    name: str
    short_name: str
    parent_id: int
    org_unit_type_id: int
    org_unit_type: OrgUnitTypeModel
    source: str
    source_id: int
    source_url: str
    source_ref: str
    sub_source: Optional[str]
    sub_source_id: Optional[int]
    version: int
    geo_json: Optional[dict]
    created_at: datetime
    updated_at: datetime
    reference_instance: Union[str, None]
    reference_instance_id: Union[int, None]
    catchment: Optional[str]
    altitude: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    has_geo_json: bool
    aliases: Optional[List[str]]
    groups: List[int] = field(default_factory=list)
    validation_status: Literal["NEW", "VALID", "REJECTED"] = "NEW"

    def save(self, iaso: "IASOContext") -> bool:
        if self.validation_status not in ["NEW", "VALID", "REJECTED"]:
            raise
        payload = asdict(self)
        payload["created_at"] = self.created_at.timestamp()
        payload["updated_at"] = self.updated_at.timestamp()
        del payload["org_unit_type"]
        return iaso.patch(endpoint="orgunits", id=self.id, payload=payload)


class JsonField:
    # TODO: complete this list
    orgunits = "orgUnits"
    orgunittypes = "orgUnitTypes"
    projects = "projects"
    groups = "groups"
    instances = "instances"
    forms = "forms"
    formversions = "form_versions"


class IASOContext:
    _server_url = None
    _username = None
    _password = None
    _token = None
    _http_headers = None

    def __init__(
        self, username="", password="", token="", url="https://iaso.bluesquare.org"
    ):
        self._server_url = url

        if username == "" and password == "":
            username = os.environ.get("IASO_USERNAME", "")
            password = os.environ.get("IASO_PASSWORD", "")

        if token == "":
            token = os.environ.get("IASO_TOKEN", "")

        if username == "" and token == "":
            raise ValueError("You must pass a token or a username & password")

        if token != "":
            self._token = token
        else:
            self._username = username
            if password != "":
                self._password = password
            else:
                raise ValueError("Password cannot be blank")

            self.refresh_token()

        self._http_headers = {"Authorization": "Bearer %s" % self._token}
        r = requests.get(self._server_url + "/api/", headers=self._http_headers)
        r.raise_for_status()

    def get_token(self):
        return self._token

    def refresh_token(self):
        if self._username != "":
            creds = {"username": self._username, "password": self._password}
            r = requests.post(self._server_url + "/api/token/", json=creds)
            r.raise_for_status()
            self._token = r.json().get("access")
        else:
            raise ValueError("Cannot obtain a new token without credentials")

    def count(self, endpoint: str, filter={}):
        url = self._server_url + "/api/" + endpoint
        params = filter.copy()
        params.update({"limit": 1, "page": 1})
        r = requests.get(url, headers=self._http_headers, params=params)
        r.raise_for_status()
        j = r.json()
        return int(j["count"])

    def patch(self, endpoint: str, id: int, payload: dict):
        url = self._server_url + "/api/" + endpoint + "/" + str(id) + "/"
        r = None
        try:
            r = requests.patch(url, json=payload, headers=self._http_headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if r.status_code <= 500:
                time.sleep(3)
                r = requests.patch(url, json=payload, headers=self._http_headers)
                r.raise_for_status()
            else:
                return False
        except:
            if r is not None:
                print(r.text)
            return False

        return True

    def _get_iaso_list(self, endpoint: str, limit: int = 0, page: int = 1, filter={}):
        url = self._server_url + "/api/" + endpoint
        jsonfield = getattr(JsonField, endpoint)
        results = []
        c = self.count(endpoint=endpoint, filter=filter)

        if limit == 0 and c > 1000:
            continueloop = True
            page = 1
            while continueloop:
                filter.update({"limit": 500, "page": page})
                r = requests.get(url, headers=self._http_headers, params=filter)
                r.raise_for_status()
                j = r.json()
                if not jsonfield in j:  # IASO sux
                    jsonfield = jsonfield.lower()
                results += j[jsonfield]
                page += 1
                if j["has_next"] == False:
                    continueloop = False

                # FIXME: Exponential backoff

        else:
            if limit != 0:
                filter.update({"limit": limit, "page": page})
            r = requests.get(url, headers=self._http_headers, params=filter)
            r.raise_for_status()
            j = r.json()
            if not jsonfield in j:  # IASO sux
                jsonfield = jsonfield.lower()

            results = j[jsonfield]

        return results

    def _create_ProjectModel(self, json):
        return ProjectModel(
            id=json["id"],
            name=json["name"],
            app_id=json["app_id"],
            needs_authentication=json["needs_authentication"],
            created_at=datetime.fromtimestamp(json["created_at"]),
            updated_at=datetime.fromtimestamp(json["updated_at"]),
        )

    def get_projects(
        self, limit: int = 0, page: int = 1, filter={}
    ) -> List[ProjectModel]:
        data = self._get_iaso_list(
            endpoint="projects", limit=limit, page=page, filter=filter
        )
        results = []
        for d in data:
            results.append(self._create_ProjectModel(d))
        results.sort(key=operator.attrgetter("id"))
        return results

    def get_project(self, id: int) -> ProjectModel:
        url = self._server_url + "/api/projects/" + str(id)
        r = requests.get(url, headers=self._http_headers)
        r.raise_for_status()
        return self._create_ProjectModel(r.json())

    def _create_GroupModel(self, json):
        return GroupModel(
            id=json["id"],
            name=json["name"],
            org_unit_count=json["org_unit_count"],
            created_at=datetime.fromtimestamp(json["created_at"]),
            updated_at=datetime.fromtimestamp(json["updated_at"]),
        )

    def get_groups(self, limit: int = 0, page: int = 1, filter={}) -> List[GroupModel]:
        data = self._get_iaso_list(
            endpoint="groups", limit=limit, page=page, filter=filter
        )
        results = []
        for d in data:
            results.append(self._create_GroupModel(d))
        results.sort(key=operator.attrgetter("id"))
        return results

    def get_group(self, id: int) -> GroupModel:
        url = self._server_url + "/api/groups/" + str(id)
        r = requests.get(url, headers=self._http_headers)
        r.raise_for_status()
        return self._create_GroupModel(r.json())

    def _create_OrgUnitTypeModel(self, json):
        projects = []
        for p in json["projects"]:
            projects.append(self._create_ProjectModel(p))
        return OrgUnitTypeModel(
            id=json["id"],
            name=json["name"],
            short_name=json["short_name"],
            depth=json["depth"],
            units_count=json["units_count"],
            projects=projects,
            created_at=datetime.fromtimestamp(json["created_at"]),
            updated_at=datetime.fromtimestamp(json["updated_at"]),
        )

    def get_orgunittypes(
        self, limit: int = 0, page: int = 1, filter={}
    ) -> List[OrgUnitTypeModel]:
        data = self._get_iaso_list(
            endpoint="orgunittypes", limit=limit, page=page, filter=filter
        )
        results = []
        for d in data:
            results.append(self._create_OrgUnitTypeModel(d))
        results.sort(key=operator.attrgetter("id"))
        return results

    def get_orgunittype(self, id: int) -> OrgUnitTypeModel:
        url = self._server_url + "/api/orgunittypes/" + str(id)
        r = requests.get(url, headers=self._http_headers)
        r.raise_for_status()
        return self._create_OrgUnitTypeModel(r.json())

    def get_orgunits(
        self, limit: int = 0, page: int = 1, filter={}
    ) -> List[SimpleOrgUnitModel]:
        data = self._get_iaso_list(
            endpoint="orgunits", limit=limit, page=page, filter=filter
        )
        results = []
        for d in data:
            results.append(
                SimpleOrgUnitModel(
                    id=d["id"],
                    name=d["name"],
                    parent_id=d["parent_id"],
                    org_unit_type_id=d["org_unit_type_id"],
                    org_unit_type_name=d["org_unit_type_name"],
                    created_at=datetime.fromtimestamp(d["created_at"]),
                    updated_at=datetime.fromtimestamp(d["updated_at"]),
                    validation_status=d["validation_status"],
                )
            )
        results.sort(key=operator.attrgetter("id"))
        return results

    def _create_OrgUnitModel(self, json):
        groups = []
        for g in json["groups"]:
            groups.append(g["id"])
        return OrgUnitModel(
            id=json["id"],
            name=json["name"],
            short_name=json["short_name"],
            parent_id=json["parent_id"],
            org_unit_type_id=json["org_unit_type_id"],
            org_unit_type=self.get_orgunittype(json["org_unit_type_id"]),
            source=json["source"],
            source_id=json["source_id"],
            version=json["version"],
            geo_json=json["geo_json"],
            created_at=datetime.fromtimestamp(json["created_at"]),
            updated_at=datetime.fromtimestamp(json["updated_at"]),
            validation_status=json["validation_status"],
            aliases=json["aliases"],
            groups=groups,
            source_url=json["source_url"],
            source_ref=json["source_ref"],
            sub_source=json["sub_source"],
            sub_source_id=json["sub_source_id"],
            reference_instance=json["reference_instance"],
            reference_instance_id=json["reference_instance_id"],
            catchment=json["catchment"],
            altitude=json["altitude"],
            latitude=json["latitude"],
            longitude=json["longitude"],
            has_geo_json=json["has_geo_json"],
        )

    def get_orgunit(self, id: int) -> OrgUnitModel:
        url = self._server_url + "/api/orgunits/" + str(id)
        r = requests.get(url, headers=self._http_headers)
        r.raise_for_status()
        return self._create_OrgUnitModel(r.json())
