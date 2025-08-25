import types
import pytest
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# stub external dependencies
sys.modules.setdefault("chardet", types.ModuleType("chardet"))
sys.modules.setdefault("requests", types.ModuleType("requests"))
sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))
fake_pandas = types.ModuleType("pandas")
fake_pandas.DataFrame = lambda *a, **k: None
sys.modules.setdefault("pandas", fake_pandas)

# minimal stubs
class FakeColumn:
    def __init__(self, checkbox=False, button=False, columns_sets=None):
        self._checkbox = checkbox
        self._button = button
        self._columns_sets = columns_sets or []
        self._columns_index = 0

    def markdown(self, *a, **k):
        pass

    def write(self, *a, **k):
        pass

    def checkbox(self, *a, **k):
        return self._checkbox

    def button(self, *a, **k):
        return self._button

    def columns(self, spec):
        result = self._columns_sets[self._columns_index]
        self._columns_index += 1
        return result

class FakeStreamlit:
    def __init__(self, text_value="", multiselect_return=None, columns_sets=None):
        self.text_value = text_value
        self.multiselect_return = multiselect_return or []
        self.columns_sets = columns_sets or []
        self.columns_index = 0
        self.session_state = {}

    def header(self, *a, **k):
        pass

    def markdown(self, *a, **k):
        pass

    def write(self, *a, **k):
        pass

    def text_input(self, *a, **k):
        return self.text_value

    def multiselect(self, *a, **k):
        return self.multiselect_return

    def selectbox(self, label, options, format_func=None, index=0):
        return options[index]

    def radio(self, *a, **k):
        return "asc"

    def columns(self, spec):
        result = self.columns_sets[self.columns_index]
        self.columns_index += 1
        return result

    def modal(self, *a, **k):
        class _M:
            def __enter__(self_inner):
                return self
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return _M()

    def rerun(self):
        pass

# load module
streamlit_legal_ui = types.ModuleType("streamlit_legal_ui")
with open(root_dir / "src" / "streamlit_legal_ui.py", "r", encoding="utf-8") as f:
    exec(f.read(), streamlit_legal_ui.__dict__)


def test_selection_updates_state(monkeypatch):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn()],  # pagination
        [FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn()],  # header
        [
            FakeColumn(checkbox=True), FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(),
            FakeColumn(columns_sets=[[FakeColumn(), FakeColumn(), FakeColumn()]])
        ],  # row
        [FakeColumn(), FakeColumn(), FakeColumn()],  # bulk actions
    ]
    st = FakeStreamlit(columns_sets=cols)
    monkeypatch.setattr(streamlit_legal_ui, "st", st)
    groups = [{"id": 1, "token": "Alpha", "type": "PERSON", "total_occurrences": 1, "variants": {}}]
    streamlit_legal_ui.display_legal_entity_manager(groups, language="en")
    assert st.session_state["selected_groups"] == [1]


def test_delete_action_removes_group(monkeypatch):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn()],  # pagination
        [FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn()],  # header
        [
            FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn(),
            FakeColumn(columns_sets=[[FakeColumn(), FakeColumn(), FakeColumn(button=True)]])
        ],  # row with delete button
        [FakeColumn(button=True), FakeColumn(button=False)],  # delete modal confirm
    ]
    st = FakeStreamlit(columns_sets=cols)
    monkeypatch.setattr(streamlit_legal_ui, "st", st)
    groups = [{"id": 1, "token": "Alpha", "type": "PERSON", "total_occurrences": 1, "variants": {}}]
    streamlit_legal_ui.display_legal_entity_manager(groups, language="en")
    assert groups == []
