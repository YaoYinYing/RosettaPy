import pandas as pd
import pytest

from RosettaPy.analyser.ddg import RosettaCartesianddGAnalyser, main


@pytest.fixture
def sample_ddg_json():
    return [
        {
            "mutations": [{"mut": "A", "pos": "10", "wt": "A"}],
            "scores": {"total": -3.0, "fa_atr": -1.0, "fa_rep": 1.0},
        },
        {
            "mutations": [{"mut": "V", "pos": "10", "wt": "A"}],
            "scores": {"total": -1.0, "fa_atr": -0.5, "fa_rep": 0.5},
        },
    ]


@pytest.fixture
def sample_ddg_ddg():
    return """COMPLEX Round Baseline total fa_atr_label fa_atr fa_rep_label fa_rep
WT_: Round0 WT_: -3.0 fa_atr -1.0 fa_rep 1.0
MUT_10A: Round0 MUT_10A: -1.0 fa_atr -0.5 fa_rep 0.5
"""


@pytest.fixture
def sample_ddg_ddg_file():
    return "tests/data/ddg_runtimes/task-cart_ddg_run_3fap_hf3_A_short-no-0/W4T_E5R_G7N_Q10K_M11K.ddg"


@pytest.fixture
def sample_ddg_ddg_file_json():
    return "tests/data/ddg_runtimes/task-cart_ddg_run_3fap_hf3_A_short-no-0/W4T_E5R_G7N_Q10K_M11K.json"


@pytest.fixture
def sample_ddg_ddg_dir():
    return "tests/data/ddg_runtimes/task-cart_ddg_run_3fap_hf3_A_short-no-0"


@pytest.fixture
def sample_ddg_df(sample_ddg_ddg_dir):
    analyser = RosettaCartesianddGAnalyser(sample_ddg_ddg_dir, recursive=True)
    return analyser.parse_ddg_files()


def test_gather_files_recursive(mocker):
    mocker.patch("os.walk", return_value=[("some/dir", [], ["file1.json", "file2.json"])])
    analyser = RosettaCartesianddGAnalyser("some", recursive=True)
    files = analyser.gather_files()
    assert len(files) == 2
    assert "some/dir/file1.json" in files


def test_gather_files_non_recursive(mocker):
    mocker.patch("os.listdir", return_value=["file1.json", "file2.json"])
    analyser = RosettaCartesianddGAnalyser("some/dir", recursive=False)
    files = analyser.gather_files()
    assert len(files) == 2
    assert "some/dir/file1.json" in files


def test_read_json(sample_ddg_ddg_file_json, mocker):

    df = RosettaCartesianddGAnalyser.read_json(sample_ddg_ddg_file_json)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 6  # Two records in the json
    assert "total" in df.columns


def test_read_ddg(sample_ddg_ddg_file, mocker):

    df = RosettaCartesianddGAnalyser.read_ddg(sample_ddg_ddg_file)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 6  # Two records in the ddg file
    assert "total" in df.columns


def test_is_wild_type():
    mutations = [{"mut": "A", "pos": "10", "wt": "A"}]
    assert RosettaCartesianddGAnalyser.is_wild_type(mutations) is True

    mutations = [{"mut": "V", "pos": "10", "wt": "A"}]
    assert RosettaCartesianddGAnalyser.is_wild_type(mutations) is False


def test_mutinfo2id():
    mutations = [{"mut": "V", "pos": "10", "wt": "A"}]
    mutant_id = RosettaCartesianddGAnalyser.mutinfo2id(mutations)
    assert mutant_id == "MUT_10VAL"


def test_raw_to_ddg(sample_ddg_ddg_file, mocker):

    df_raw = RosettaCartesianddGAnalyser.read_ddg(sample_ddg_ddg_file)
    ddg_summary = RosettaCartesianddGAnalyser.raw_to_ddg(df_raw)
    assert isinstance(ddg_summary, pd.DataFrame)
    assert "ddG_cart" in ddg_summary.columns


def test_parse_ddg_files(mocker, sample_ddg_ddg_dir):

    analyser = RosettaCartesianddGAnalyser(sample_ddg_ddg_dir, recursive=True)
    df = analyser.parse_ddg_files()
    assert isinstance(df, pd.DataFrame)
    assert "ddG_cart" in df.columns


def test_ddg_analyser_main():
    main()
