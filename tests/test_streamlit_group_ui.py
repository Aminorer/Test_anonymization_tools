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


class SimpleSeries(list):
    @property
    def empty(self):
        return len(self) == 0

    class _ILoc:
        def __init__(self, data):
            self.data = data

        def __getitem__(self, idx):
            return self.data[idx]

    @property
    def iloc(self):
        return SimpleSeries._ILoc(self)

    def tolist(self):
        return list(self)


class SimpleDataFrame:
    def __init__(self, records):
        self.records = records

    def iterrows(self):
        for i, row in enumerate(self.records):
            yield i, row

    def __getitem__(self, key):
        return SimpleSeries([row.get(key) for row in self.records])

    @property
    def loc(self):
        class _Loc:
            def __init__(self, df):
                self.df = df

            def __getitem__(self, key):
                mask, column = key
                filtered = [row for row, flag in zip(self.df.records, mask) if flag]
                return SimpleSeries([row.get(column) for row in filtered])

        return _Loc(self)


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
        form_submit=False,
        input_values=None,
        button_presses=None,
    ):
        self.default_text_value = text_value
        self.multiselect_return = multiselect_return
        self.columns_sets = columns_sets or []
        self.columns_index = 0
        self.session_state = {}
        self.data_editor_updates = data_editor_updates or {}
        self.form_submit = form_submit
        self.input_values = input_values or {}
        self.button_presses = button_presses or {}

        def text_column(label=None, *, help=None, width=None, max_chars=None, validate=None):
            return None

        self.column_config = types.SimpleNamespace(
            CheckboxColumn=lambda *a, **k: None,
            TextColumn=text_column,
        )

    def _initial_widget_value(self, widget_key, fallback):
        if widget_key in self.input_values:
            return self.input_values[widget_key]
        if self.default_text_value != "":
            return self.default_text_value
        return fallback

    def header(self, *a, **k):
        pass

    def markdown(self, *a, **k):
        pass

    def write(self, *a, **k):
        pass

    def text_input(self, label, value="", key=None):
        widget_key = key or label
        if widget_key not in self.session_state:
            self.session_state[widget_key] = self._initial_widget_value(
                widget_key, value
            )
        return self.session_state[widget_key]

    def text_area(self, label, value="", key=None):
        widget_key = key or label
        if widget_key not in self.session_state:
            self.session_state[widget_key] = self._initial_widget_value(
                widget_key, value
            )
        return self.session_state[widget_key]

    def multiselect(self, label, options, default=None):
        self.multiselect_last_default = default
        return self.multiselect_return if self.multiselect_return is not None else default

    def selectbox(self, label, options, format_func=None, index=0):
        return options[index]

    def radio(self, *a, **k):
        return "asc"

    def button(self, label, key=None, **k):
        button_key = key or label
        return self.button_presses.get(button_key, False)

    def columns(self, spec):
        result = self.columns_sets[self.columns_index]
        self.columns_index += 1
        return result

    def form(self, *a, **k):
        class _F:
            def __enter__(self_inner):
                return self
            def __exit__(self_inner, exc_type, exc, tb):
                return False
        return _F()

    def form_submit_button(self, label, disabled=False):
        return self.form_submit and not disabled

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
    ]
    st = FakeStreamlit(
        columns_sets=cols,
        data_editor_updates={0: {"Delete": True}},
        form_submit=True,
    )
    monkeypatch.setattr(streamlit_legal_ui, "st", st)
    groups = [{"id": 1, "token": "Alpha", "type": "PERSON", "total_occurrences": 1, "variants": {}}]
    streamlit_legal_ui.display_legal_entity_manager(groups, language="en")
    assert groups == []


def test_delete_action_uses_entity_manager(monkeypatch):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn()],
    ]
    st = FakeStreamlit(
        columns_sets=cols,
        data_editor_updates={0: {"Delete": True}},
        form_submit=True,
    )
    monkeypatch.setattr(streamlit_legal_ui, "st", st)
    em = streamlit_legal_ui.EntityManager()
    em.add_entity({"type": "PERSON", "value": "Alice", "start": 0, "end": 5, "replacement": "[Alpha]"})
    em.add_entity({"type": "PERSON", "value": "Bob", "start": 6, "end": 9, "replacement": "[Beta]"})
    groups = list(em.get_grouped_entities().values())
    streamlit_legal_ui.display_legal_entity_manager(groups, entity_manager=em, language="en")
    assert len(em.entities) == 1
    assert em.entities[0]["replacement"] == "[Beta]"
    assert groups == list(em.get_grouped_entities().values())


def test_filters_types_defaults_to_all(monkeypatch):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn()],
    ]
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


def test_edit_action_updates_type_and_variants(monkeypatch):
    cols = [[FakeColumn(), FakeColumn(), FakeColumn()]]
    em = streamlit_legal_ui.EntityManager()
    em.add_entity(
        {
            "type": "PERSON",
            "value": "Alice",
            "start": 0,
            "end": 5,
            "replacement": "[Alpha]",
        }
    )
    groups = [
        {"id": gid, **data}
        for gid, data in em.get_grouped_entities().items()
    ]
    st = FakeStreamlit(
        columns_sets=cols,
        data_editor_updates={0: {"Edit": True}},
        button_presses={"save_edit": True},
    )
    monkeypatch.setattr(streamlit_legal_ui, "st", st)

    st.session_state["edit_token_Alpha"] = "[Alpha]"
    st.session_state["edit_type_Alpha"] = "ORG"
    st.session_state["edit_variants_Alpha"] = "[Alice], [Charlie]"

    streamlit_legal_ui.display_legal_entity_manager(groups, entity_manager=em, language="en")

    assert groups[0]["type"] == "ORG"
    assert set(groups[0]["variants"].keys()) == {"Alice", "Charlie"}
    assert em.entities[0]["type"] == "ORG"
    assert set(em.entities[0]["variants"]) == {"Alice", "Charlie"}
    assert "edit_type_Alpha" not in st.session_state
