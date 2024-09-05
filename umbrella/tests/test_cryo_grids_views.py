from django.test import TestCase
from datetime import datetime
from cryo_grids.views import filter_by_sample_name, add_msi_session, format_grid
import pytest

def test_format_grid():
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

def test_add_msi_session_new_entry():
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

def test_add_msi_session_existing_entry():
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

def test_add_msi_session_different_entry():
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