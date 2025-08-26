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


class SimpleDataFrame:
    def __init__(self, records):
        self.records = records

    def iterrows(self):
        for i, row in enumerate(self.records):
            yield i, row


fake_pandas = types.ModuleType("pandas")
fake_pandas.DataFrame = SimpleDataFrame
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
    def __init__(
        self,
        text_value="",
        multiselect_return=None,
        columns_sets=None,
        data_editor_updates=None,
    ):
        self.text_value = text_value
        self.multiselect_return = multiselect_return
        self.columns_sets = columns_sets or []
        self.columns_index = 0
        self.session_state = {}
        self.data_editor_updates = data_editor_updates or {}
        def text_column(label=None, *, help=None, width=None, max_chars=None, validate=None):
            return None

        self.column_config = types.SimpleNamespace(
            CheckboxColumn=lambda *a, **k: None,
            TextColumn=text_column,
        )

    def header(self, *a, **k):
        pass

    def markdown(self, *a, **k):
        pass

    def write(self, *a, **k):
        pass

    def text_input(self, *a, **k):
        return self.text_value

    def multiselect(self, label, options, default=None):
        self.multiselect_last_default = default
        return self.multiselect_return if self.multiselect_return is not None else default

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

    def data_editor(self, df, **kwargs):
        for idx, updates in self.data_editor_updates.items():
            df.records[idx].update(updates)
        return df

# load module
streamlit_legal_ui = types.ModuleType("streamlit_legal_ui")
with open(root_dir / "src" / "streamlit_legal_ui.py", "r", encoding="utf-8") as f:
    exec(f.read(), streamlit_legal_ui.__dict__)
def test_delete_action_removes_group(monkeypatch):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn()],  # pagination
        [FakeColumn(button=True), FakeColumn(button=False)],  # delete modal confirm
    ]
    st = FakeStreamlit(columns_sets=cols, data_editor_updates={0: {"Delete": True}})
    monkeypatch.setattr(streamlit_legal_ui, "st", st)
    groups = [{"id": 1, "token": "Alpha", "type": "PERSON", "total_occurrences": 1, "variants": {}}]
    streamlit_legal_ui.display_legal_entity_manager(groups, language="en")
    assert groups == []


def test_filters_types_defaults_to_all(monkeypatch):
    cols = [[FakeColumn(), FakeColumn(), FakeColumn()]]
    st = FakeStreamlit(columns_sets=cols)
    monkeypatch.setattr(streamlit_legal_ui, "st", st)
    groups = [
        {"id": 1, "token": "Alpha", "type": "PERSON", "total_occurrences": 1, "variants": {}}
    ]
    streamlit_legal_ui.display_legal_entity_manager(groups, language="en")
    assert st.multiselect_last_default == ["PERSON"]
    assert st.session_state["group_filters"]["types"] == ["PERSON"]


def test_display_legal_entity_manager_rejects_extra_kwargs():
    with pytest.raises(TypeError):
        streamlit_legal_ui.display_legal_entity_manager([], language="en", unexpected=True)
