import sys
import types
import pytest
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))
sys.modules.setdefault("chardet", types.ModuleType("chardet"))

# ---------------------------------------------------------------------------
# Minimal pandas and streamlit stubs so modules can be imported without deps
# ---------------------------------------------------------------------------


class FakeDataFrame:
    def __init__(self, rows):
        self.rows = rows

    def __getitem__(self, cols):
        return FakeDataFrame([{c: row[c] for c in cols} for row in self.rows])


fake_pandas = types.ModuleType("pandas")
fake_pandas.DataFrame = lambda rows: FakeDataFrame(rows)
sys.modules.setdefault("pandas", fake_pandas)

fake_streamlit_module = types.ModuleType("streamlit")
fake_streamlit_module.header = lambda *a, **k: None
fake_streamlit_module.columns = lambda *a, **k: []
fake_streamlit_module.text_input = lambda *a, **k: ""
fake_streamlit_module.dataframe = lambda *a, **k: None
fake_streamlit_module.button = lambda *a, **k: False
fake_streamlit_module.checkbox = lambda *a, **k: False
fake_streamlit_module.write = lambda *a, **k: None
fake_streamlit_module.session_state = {}
fake_streamlit_module.rerun = lambda: None
sys.modules.setdefault("streamlit", fake_streamlit_module)

# Create a minimal "src" package and load needed modules without executing src/__init__
src_pkg = types.ModuleType("src")
sys.modules["src"] = src_pkg

import importlib.util

def _load(name):
    path = root_dir / "src" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"src.{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[f"src.{name}"] = module
    return module

_load("variant_manager_ui")
_load("group_ui_utils")
_load("entity_manager")
streamlit_legal_ui = _load("streamlit_legal_ui")


class FakeColumn:
    def __init__(self, checkbox: bool = False, button: bool = False) -> None:
        self._checkbox = checkbox
        self._button = button

    def markdown(self, *args, **kwargs) -> None:
        pass

    def write(self, *args, **kwargs) -> None:
        pass

    def checkbox(self, *args, **kwargs) -> bool:
        return self._checkbox

    def button(self, *args, **kwargs) -> bool:
        return self._button


class FakeStreamlit:
    def __init__(self, text_input_value: str, columns_sets, button_returns=None) -> None:
        self.text_input_value = text_input_value
        self.columns_sets = columns_sets
        self.columns_index = 0
        self.button_returns = button_returns or []
        self.button_index = 0
        self.session_state = {}
        self.captured_df = None

    def header(self, *args, **kwargs) -> None:
        pass

    def text_input(self, *args, **kwargs) -> str:
        return self.text_input_value

    def columns(self, spec):
        result = self.columns_sets[self.columns_index]
        self.columns_index += 1
        return result

    def dataframe(self, df, **kwargs) -> None:
        self.captured_df = df

    def rerun(self) -> None:
        pass

    def write(self, *args, **kwargs) -> None:
        pass

    def button(self, *args, **kwargs) -> bool:
        if self.button_index < len(self.button_returns):
            res = self.button_returns[self.button_index]
            self.button_index += 1
            return res
        return False


@pytest.fixture
def sample_groups():
    return [
        {"id": 1, "token": "Alpha", "total_occurrences": 2},
        {"id": 2, "token": "Beta", "total_occurrences": 5},
    ]


def test_search_filters_groups(monkeypatch, sample_groups):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn()],  # header
        [FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn()],  # row for Beta
        [FakeColumn(), FakeColumn()],  # bulk action row
    ]
    st_mock = FakeStreamlit(text_input_value="beta", columns_sets=cols)
    monkeypatch.setattr(streamlit_legal_ui, "st", st_mock)
    monkeypatch.setattr(streamlit_legal_ui, "display_variant_management", lambda *a, **k: None)
    streamlit_legal_ui.display_legal_entity_manager(sample_groups)
    assert [row["Token"] for row in st_mock.captured_df.rows] == ["Beta"]


def test_manage_and_delete_updates_state(monkeypatch, sample_groups):
    cols = [
        [FakeColumn(), FakeColumn(), FakeColumn(), FakeColumn()],  # header
        [FakeColumn(), FakeColumn(), FakeColumn(checkbox=True), FakeColumn(checkbox=False)],
        [FakeColumn(), FakeColumn(), FakeColumn(checkbox=False), FakeColumn(checkbox=True)],
        [FakeColumn(button=True), FakeColumn(button=True)],  # bulk buttons pressed
    ]
    st_mock = FakeStreamlit(text_input_value="", columns_sets=cols, button_returns=[False])
    monkeypatch.setattr(streamlit_legal_ui, "st", st_mock)
    monkeypatch.setattr(streamlit_legal_ui, "display_variant_management", lambda *a, **k: None)
    streamlit_legal_ui.display_legal_entity_manager(sample_groups)
    assert st_mock.session_state["show_details_1"] is True
    assert sample_groups == [{"id": 1, "token": "Alpha", "total_occurrences": 2}]
