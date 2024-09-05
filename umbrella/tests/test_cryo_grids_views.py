from datetime import datetime
from cryo_grids.views import filter_by_sample_name, add_msi_session, format_grid, get_base_url, format_queryset_results, apply_filters, get_cryo_grids_details, available_filters
import pytest
from cryo_grids.utils import CryoGridsQueryParams, QueryParams
from django.db.models import Q
from unittest.mock import patch, Mock
from cryo_grids.views import get_freezing_plan_list
from django.test import RequestFactory
from django.core.exceptions import ObjectDoesNotExist
import json
from django.core.exceptions import ValidationError
@pytest.fixture
def mock_get_base_url():
    with patch('cryo_grids.views.get_base_url') as mock:
        mock.return_value = 'http://umbrella.czbiohub.org'
        yield mock


@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def mock_query_params():
    return Mock(spec=QueryParams)

@pytest.mark.django_db
def test_available_filters_success(request_factory, mock_query_params):
    request = request_factory.get('/cryo_grids/filters', {'q': '[]'})
    request.META['HTTP_ORIGIN'] = '*'
    
    mock_query_params.q = []

    mock_queryset = Mock()
    mock_filtered_queryset = Mock()
    mock_filtered_queryset.filter.return_value.count.return_value = 10

    with patch('cryo_grids.views.CryoGrid.objects.select_related', return_value=mock_queryset), \
         patch('cryo_grids.views.QueryParams', return_value=mock_query_params), \
         patch('cryo_grids.views.PlungeFreezingPlan.objects.filter', return_value=Mock()), \
         patch('cryo_grids.views.now', return_value=datetime(2023, 10, 1)):

        response = available_filters(request)
        assert response.status_code == 200
        response_data = json.loads(response.content)
        assert 'filters' in response_data

@pytest.mark.django_db
def test_available_filters_invalid_query_params(request_factory):
    request = request_factory.get('/cryo_grids/filters', {'invalid_param': 'value'})
    request.META['HTTP_ORIGIN'] = '*'

    response = available_filters(request)
    assert response.status_code == 422
    response_data = json.loads(response.content)
    assert response_data == {'error': 'Invalid query parameters. Only "q" is allowed.'}

@pytest.mark.django_db
def test_available_filters_validation_error(request_factory):
    request = request_factory.get('/cryo_grids/filters', {'q': 'invalid_json'})
    request.META['HTTP_ORIGIN'] = '*'

    with patch('cryo_grids.views.QueryParams', side_effect=ValidationError([])):
        response = available_filters(request)
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert 'error' in response_data
        assert 'Invalid input' in response_data['error']

@pytest.mark.django_db
def test_available_filters_exception(request_factory, mock_query_params):
    request = request_factory.get('/cryo_grids/filters', {'q': '[]'})
    request.META['HTTP_ORIGIN'] = '*'
    
    mock_query_params.q = []

    with patch('cryo_grids.views.CryoGrid.objects.select_related', side_effect=Exception('Test Exception')), \
         patch('cryo_grids.views.QueryParams', return_value=mock_query_params):

        response = available_filters(request)
        assert response.status_code == 500
        response_data = json.loads(response.content)
        assert response_data == {'error': 'An unexpected error occurred: Test Exception'}


@pytest.fixture
def request_factory():
    return RequestFactory()

@pytest.fixture
def mock_query_params():
    return Mock(spec=CryoGridsQueryParams)

@pytest.mark.django_db
def test_get_cryo_grids_details_success(request_factory, mock_query_params):
    request = request_factory.get('/cryo_grids/details', {'filter_type': 'AND'})
    request.META['HTTP_ORIGIN'] = '*'
    
    mock_query_params.filter_type = 'AND'
    mock_query_params.sample_name = None

    mock_queryset = Mock()
    mock_filtered_queryset = Mock()
    mock_formatted_result = {
        1: {
            'grid': {'id': 1, 'name': 'Test Grid'},
            'cassette': {'name': 'Cassette 1'},
            'project': {'id': 1, 'name': 'Test Project'},
            'puck': {'name': 'Puck 1'},
            'user': {'id': 1, 'name': 'user1'},
            'freezingPlan': {'id': 1, 'sample': [{'id': 1, 'name': 'Sample A'}]},
            'freezingSession': {'id': 1, 'createdAt': '2023-10-01 12:00'},
            'screeningSession': 'Screening Session 1',
            'msiSession': []
        }
    }

    with patch('cryo_grids.views.CryoGrid.objects.select_related', return_value=mock_queryset), \
         patch('cryo_grids.views.apply_filters', return_value=mock_filtered_queryset), \
         patch('cryo_grids.views.format_queryset_results', return_value=mock_formatted_result), \
         patch('cryo_grids.views.filter_by_sample_name', return_value=mock_formatted_result), \
         patch('cryo_grids.views.CryoGridsQueryParams', return_value=mock_query_params):

        response = get_cryo_grids_details(request)
        assert response.status_code == 200
        assert json.loads(response.content) == {'result': list(mock_formatted_result.values())}

@pytest.mark.django_db
def test_get_cryo_grids_details_no_results(request_factory, mock_query_params):
    request = request_factory.get('/cryo_grids/details', {'filter_type': 'AND'})
    request.META['HTTP_ORIGIN'] = '*'
    
    mock_query_params.filter_type = 'AND'
    mock_query_params.sample_name = None

    mock_queryset = Mock()
    mock_filtered_queryset = Mock()
    mock_filtered_queryset.exists.return_value = False

    with patch('cryo_grids.views.CryoGrid.objects.select_related', return_value=mock_queryset), \
         patch('cryo_grids.views.apply_filters', return_value=mock_filtered_queryset), \
         patch('cryo_grids.views.CryoGridsQueryParams', return_value=mock_query_params):

        response = get_cryo_grids_details(request)
        assert response.status_code == 200
        assert json.loads(response.content) == {'result': []}

@pytest.mark.django_db
def test_get_cryo_grids_details_exception(request_factory, mock_query_params):
    request = request_factory.get('/cryo_grids/details', {'filter_type': 'AND'})
    request.META['HTTP_ORIGIN'] = '*'
    
    mock_query_params.filter_type = 'AND'
    mock_query_params.sample_name = None

    with patch('cryo_grids.views.CryoGrid.objects.select_related', side_effect=Exception('Test Exception')), \
         patch('cryo_grids.views.CryoGridsQueryParams', return_value=mock_query_params):

        response = get_cryo_grids_details(request)
        assert response.status_code == 500
        assert json.loads(response.content) == {'error': 'An unexpected error occurred: Test Exception'}

@pytest.fixture
def mock_functions():
    with patch('cryo_grids.views.get_freezing_plan_list') as mock_get_freezing_plan_list, \
         patch('cryo_grids.views.format_grid') as mock_format_grid, \
         patch('cryo_grids.views.format_project') as mock_format_project, \
         patch('cryo_grids.views.add_msi_session') as mock_add_msi_session:
        
        mock_get_freezing_plan_list.return_value = [{'id': 1, 'name': 'Sample A', 'url': 'http://umbrella.czbiohub.org/admin/samples/1'}]
        mock_format_grid.return_value = {'id': 1, 'name': 'Test Grid', 'trashed': False, 'url': 'http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/1', 'createdAt': datetime(2023, 10, 1, 12, 0, 0)}
        mock_format_project.return_value = {'id': 1, 'name': 'Test Project', 'url': 'http://umbrella.czbiohub.org/admin/projects/project/1'}
        
        yield mock_get_freezing_plan_list, mock_format_grid, mock_format_project, mock_add_msi_session

@pytest.mark.django_db
def test_format_queryset_results(mock_get_base_url, mock_functions):
    mock_get_freezing_plan_list, mock_format_grid, mock_format_project, mock_add_msi_session = mock_functions

    queryset = [
        {
            'id': 1,
            'fz_plan_id': 1,
            'fz_session_id': 1,
            'fz_session_datetime': datetime(2023, 10, 1, 12, 0, 0),
            'cassette_name': 'Cassette 1',
            'project_id': 1,
            'project_name': 'Project 1',
            'puck': 'Puck 1',
            'userID': 1,
            'username': 'user1',
            'screening_session_name': 'Screening Session 1',
            'msisession_id': 1,
            'msisession_name': 'MSI Session 1'
        }
    ]

    expected_result = {
        1: {
            'grid': {
                'id': 1,
                'name': 'Test Grid',
                'trashed': False,
                'url': 'http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/1',
                'createdAt': datetime(2023, 10, 1, 12, 0, 0)
            },
            'cassette': {'name': 'Cassette 1'},
            'project': {
                'id': 1,
                'name': 'Test Project',
                'url': 'http://umbrella.czbiohub.org/admin/projects/project/1'
            },
            'puck': {'name': 'Puck 1'},
            'user': {'id': 1, 'name': 'user1'},
            'freezingPlan': {
                'id': 1,
                'sample': [{'id': 1, 'name': 'Sample A', 'url': 'http://umbrella.czbiohub.org/admin/samples/1'}]
            },
            'freezingSession': {'id': 1, 'createdAt': '2023-10-01 12:00'},
            'screeningSession': 'Screening Session 1',
            'msiSession': []
        }
    }

    result = format_queryset_results(queryset)
    assert result == expected_result
    mock_add_msi_session.assert_called_once_with(expected_result[1]['msiSession'], queryset[0])

@pytest.mark.django_db
def test_format_queryset_results_no_msi_session(mock_get_base_url, mock_functions):
    mock_get_freezing_plan_list, mock_format_grid, mock_format_project, mock_add_msi_session = mock_functions

    queryset = [
        {
            'id': 1,
            'fz_plan_id': 1,
            'fz_session_id': 1,
            'fz_session_datetime': datetime(2023, 10, 1, 12, 0, 0),
            'cassette_name': 'Cassette 1',
            'project_id': 1,
            'project_name': 'Project 1',
            'puck': 'Puck 1',
            'userID': 1,
            'username': 'user1',
            'screening_session_name': 'Screening Session 1',
            'msisession_id': None,
            'msisession_name': None
        }
    ]

    expected_result = {
        1: {
            'grid': {
                'id': 1,
                'name': 'Test Grid',
                'trashed': False,
                'url': 'http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/1',
                'createdAt': datetime(2023, 10, 1, 12, 0, 0)
            },
            'cassette': {'name': 'Cassette 1'},
            'project': {
                'id': 1,
                'name': 'Test Project',
                'url': 'http://umbrella.czbiohub.org/admin/projects/project/1'
            },
            'puck': {'name': 'Puck 1'},
            'user': {'id': 1, 'name': 'user1'},
            'freezingPlan': {
                'id': 1,
                'sample': [{'id': 1, 'name': 'Sample A', 'url': 'http://umbrella.czbiohub.org/admin/samples/1'}]
            },
            'freezingSession': {'id': 1, 'createdAt': '2023-10-01 12:00'},
            'screeningSession': 'Screening Session 1',
            'msiSession': []
        }
    }

    result = format_queryset_results(queryset)
    assert result == expected_result
    mock_add_msi_session.assert_not_called()


@pytest.mark.django_db
def test_get_freezing_plan_list(mock_get_base_url):
    # Mock the PlungeFreezingPlan object and its related objects
    sample1 = Mock(id=1)
    sample1.name = 'Sample A'
    sample2 = Mock(id=2)
    sample2.name = 'Sample B'
    tag1 = 'tag1'
    tag2 = 'tag2'

    freezing_plan = Mock()
    freezing_plan.sample.all.return_value = [sample1, sample2]
    freezing_plan.tags.values_list.return_value = [tag1, tag2]

    with patch('cryo_grids.views.PlungeFreezingPlan.objects.get', return_value=freezing_plan):
        result = get_freezing_plan_list(1)
        expected_result = [
            {
                'id': 1,
                'name': 'Sample A with tag1, tag2',
                'url': 'http://umbrella.czbiohub.org/admin/samples/1'
            },
            {
                'id': 2,
                'name': 'Sample B with tag1, tag2',
                'url': 'http://umbrella.czbiohub.org/admin/samples/2'
            }
        ]
        assert result == expected_result

@pytest.mark.django_db
def test_get_freezing_plan_list_no_tags(mock_get_base_url):
    # Mock the PlungeFreezingPlan object and its related objects
    sample1 = Mock(id=1)
    sample1.name = 'Sample A'
    sample2 = Mock(id=2)
    sample2.name = 'Sample B'

    freezing_plan = Mock()
    freezing_plan.sample.all.return_value = [sample1, sample2]
    freezing_plan.tags.values_list.return_value = []

    with patch('cryo_grids.views.PlungeFreezingPlan.objects.get', return_value=freezing_plan):
        result = get_freezing_plan_list(1)
        expected_result = [
            {
                'id': 1,
                'name': 'Sample A without tag',
                'url': 'http://umbrella.czbiohub.org/admin/samples/1'
            },
            {
                'id': 2,
                'name': 'Sample B without tag',
                'url': 'http://umbrella.czbiohub.org/admin/samples/2'
            }
        ]
        assert result == expected_result

@pytest.fixture
def mock_get_base_url():
    with patch('cryo_grids.views.get_base_url') as mock:
        mock.return_value = 'http://umbrella.czbiohub.org'
        yield mock

def test_format_grid(mock_get_base_url):
    item = {
        'id': 1,
        'grid_name': 'Test Grid',
        'status': False,
        'created_on': datetime(2023, 10, 1, 12, 0, 0)
    }
    expected_result = {
        'id': 1,
        'name': 'Test Grid (id=1)',
        'trashed': False,
        'url': 'http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/1',
        'createdAt': datetime(2023, 10, 1, 12, 0, 0),
    }
    result = format_grid(item)
    assert result == expected_result

def test_add_msi_session_new_entry(mock_get_base_url):
    msi_session_list = []
    item = {
        'msisession_id': 1,
        'msisession_name': 'Session 1'
    }
    add_msi_session(msi_session_list, item)
    expected_entry = {
        'id': 1,
        'name': 'Session 1',
        'url': 'http://umbrella.czbiohub.org/tem/1'
    }
    assert expected_entry in msi_session_list

def test_add_msi_session_existing_entry(mock_get_base_url):
    msi_session_list = [{
        'id': 1,
        'name': 'Session 1',
        'url': 'http://umbrella.czbiohub.org/tem/1'
    }]
    item = {
        'msisession_id': 1,
        'msisession_name': 'Session 1'
    }
    add_msi_session(msi_session_list, item)
    assert len(msi_session_list) == 1

def test_add_msi_session_different_entry(mock_get_base_url):
    msi_session_list = [{
        'id': 1,
        'name': 'Session 1',
        'url': 'http://umbrella.czbiohub.org/tem/1'
    }]
    item = {
        'msisession_id': 2,
        'msisession_name': 'Session 2'
    }
    add_msi_session(msi_session_list, item)
    expected_entry = {
        'id': 2,
        'name': 'Session 2',
        'url': 'http://umbrella.czbiohub.org/tem/2'
    }
    assert expected_entry in msi_session_list
    assert len(msi_session_list) == 2

@pytest.fixture
def formatted_result():
    return {
        1: {
            'freezingPlan': {
                'sample': [
                    {'name': 'Sample A with tag1', 'id': 1, 'url': 'http://example.com/sample/1'},
                    {'name': 'Sample B without tag', 'id': 2, 'url': 'http://example.com/sample/2'}
                ]
            }
        },
        2: {
            'freezingPlan': {
                'sample': [
                    {'name': 'Sample C with tag2', 'id': 3, 'url': 'http://example.com/sample/3'},
                    {'name': 'Sample D without tag', 'id': 4, 'url': 'http://example.com/sample/4'}
                ]
            }
        }
    }

def test_filter_by_sample_name(formatted_result):
    sample_name_input = ['Sample A with tag1', 'Sample D without tag']
    expected_result = {
        1: {
            'freezingPlan': {
                'sample': [
                    {'name': 'Sample A with tag1', 'id': 1, 'url': 'http://example.com/sample/1'}
                ]
            }
        },
        2: {
            'freezingPlan': {
                'sample': [
                    {'name': 'Sample D without tag', 'id': 4, 'url': 'http://example.com/sample/4'}
                ]
            }
        }
    }

    result = filter_by_sample_name(formatted_result, sample_name_input)
    assert result == expected_result

def test_filter_by_sample_name_no_match(formatted_result):
    sample_name_input = ['Sample X with tag3']
    expected_result = {}

    result = filter_by_sample_name(formatted_result, sample_name_input)
    assert result == expected_result

def test_filter_by_sample_name_partial_match(formatted_result):
    sample_name_input = ['Sample A with tag1', 'Sample X with tag3']
    expected_result = {
        1: {
            'freezingPlan': {
                'sample': [
                    {'name': 'Sample A with tag1', 'id': 1, 'url': 'http://example.com/sample/1'}
                ]
            }
        }
    }

    result = filter_by_sample_name(formatted_result, sample_name_input)
    assert result == expected_result