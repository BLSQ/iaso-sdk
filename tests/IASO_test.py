import responses
import requests
from pprint import pprint
from responses import matchers

from IASO import IASOContext, ProjectModel, OrgUnitTypeModel, OrgUnitModel
from IASO_mock_data import (
    mock_count_response,
    mock_projects_responses,
    mock_orgunittype_responses,
    mock_orgunittype_84_responses,
    mock_orgunittype_78_responses,
    mock_orgunit_1278118_responses,
)

@responses.activate
def IASO_Login():
        responses.add(
            method = responses.POST,
            url = "https://iaso-dev.bluesquare.org/api/token/",
            json = {'access': "whatanicetoken"},
            status = 200,
            match = [ matchers.json_params_matcher({ "username": 'jstilmant', "password": 'goodpasswd' }) ]
        )
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/",
            status = 200,
            match = [ matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}) ]
        )
        try:
            iasocontext = IASOContext(url="https://iaso-staging.bluesquare.org", username="jstilmant", password="badpasswd")
        except requests.exceptions.ConnectionError as err:
            pass

        iasocontext = IASOContext(url="https://iaso-dev.bluesquare.org", username="jstilmant", password="goodpasswd")
        assert(iasocontext.get_token() == "whatanicetoken")

        return iasocontext

@responses.activate
def CountOrgUnitType10(iasocontext: IASOContext):
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/orgunits",
            status = 200,
            json = mock_count_response,
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                    matchers.query_param_matcher({'orgUnitTypeId': 10, 'limit': 1, 'page': 1}),
                ],
        )

        result = iasocontext.count(endpoint="orgunits", filter={'orgUnitTypeId': 10})
        assert(result == 9042)


@responses.activate
def GetAllProjects(iasocontext: IASOContext):
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/projects",
            status = 200,
            json = {'count': 11, 'has_next': True, 'has_previous': False, 'page': 1, 'pages': 11, 'limit': 1},
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                    matchers.query_param_matcher({'limit': 1, 'page': 1}),
                ],
        )
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/projects",
            status = 200,
            json = mock_projects_responses,
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                ],
        )
        result = iasocontext.get_projects()
        assert(len(result) == 11)
        assert(isinstance(result[0], ProjectModel))


@responses.activate
def GetOrgUnitTypeLimit3(iasocontext: IASOContext):
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/orgunittypes",
            status = 200,
            json = {'count': 38, 'has_next': True, 'has_previous': False, 'page': 1, 'pages': 38, 'limit': 1},
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                    matchers.query_param_matcher({'limit': 1, 'page': 1}),
                ],
        )
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/orgunittypes",
            status = 200,
            json = mock_orgunittype_responses,
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                    matchers.query_param_matcher({'limit': 3, 'page': 1}),
                ],
        )
        result = iasocontext.get_orgunittypes(limit=3)
        assert(len(result) == 3)
        assert(isinstance(result[0], OrgUnitTypeModel))


@responses.activate
def GetOrgUnitType_84(iasocontext: IASOContext):
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/orgunittypes/84",
            status = 200,
            json = mock_orgunittype_84_responses,
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                ],
        )
        result = iasocontext.get_orgunittype(id=84)
        assert(isinstance(result, OrgUnitTypeModel))
        assert(result.name == "Aire de santé")


@responses.activate
def getOrgUnit_1278118(iasocontext: IASOContext):
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/orgunittypes/78",
            status = 200,
            json = mock_orgunittype_78_responses,
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                ],
        )
        responses.add(
            method = responses.GET,
            url = "https://iaso-dev.bluesquare.org/api/orgunits/1278118",
            status = 200,
            json = mock_orgunit_1278118_responses,
            match = [
                    matchers.header_matcher({"Authorization": "Bearer whatanicetoken"}),
                ],
        )
        result = iasocontext.get_orgunit(id=1278118)
        assert(isinstance(result, OrgUnitModel))
        assert(result.parent_id == 1295396)


iaso = IASO_Login()
CountOrgUnitType10(iaso)
GetAllProjects(iaso)
GetOrgUnitTypeLimit3(iaso)
GetOrgUnitType_84(iaso)
getOrgUnit_1278118(iaso)
