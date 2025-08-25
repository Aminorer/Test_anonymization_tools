import pytest

from src.group_ui_utils import filter_groups, mark_groups_for_management, delete_groups


def test_filter_groups():
    groups = {
        1: {"id": 1, "token": "Alpha"},
        2: {"id": 2, "token": "Beta"},
        3: {"id": 3, "token": "Gamma"},
    }
    assert list(filter_groups(groups, "alp").keys()) == [1]
    assert set(filter_groups(groups, "a").keys()) == {1, 2, 3}
    assert list(filter_groups(groups, "z").keys()) == []


def test_mark_groups_for_management():
    session_state = {}
    mark_groups_for_management(session_state, [1, 2])
    assert session_state["show_details_1"] is True
    assert session_state["show_details_2"] is True
    assert session_state["manage_1"] is False
    assert session_state["delete_2"] is False


def test_delete_groups():
    groups_list = [
        {"id": 1, "token": "Alpha"},
        {"id": 2, "token": "Beta"},
    ]

    class DummyManager:
        def __init__(self, groups):
            self.groups = {g["id"]: g for g in groups}

    manager = DummyManager(groups_list.copy())
    session_state = {
        "manage_1": True,
        "delete_1": True,
        "show_details_1": True,
    }
    delete_groups(manager, groups_list, session_state, [1])
    assert 1 not in manager.groups
    assert groups_list == [{"id": 2, "token": "Beta"}]
    assert "manage_1" not in session_state
    assert "show_details_1" not in session_state
