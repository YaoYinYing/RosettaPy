import os

import pytest

from RosettaPy import RosettaEnergyUnitAnalyser

sample_score_file = "tests/data/score.sc"
best_decoy = {"score": -388.465, "decoy": "3fap_hf3_A_0003"}
best_decoy_cat = {"score": -788.235, "decoy": "3fap_hf3_A_0006"}

top3_total_score = (
    {"score": -788.235, "decoy": "3fap_hf3_A_0006"},
    {"score": -455.465, "decoy": "3fap_hf3_A_0005"},
    {"score": -388.465, "decoy": "3fap_hf3_A_0003"},
)
top3_fa_atr = (
    {"score": -675.517, "decoy": "3fap_hf3_A_0001"},
    {"score": -607.507, "decoy": "3fap_hf3_A_0006"},
    {"score": -595.527, "decoy": "3fap_hf3_A_0002"},
)
# Test a non-existing score file


# Test cases
class TestRosettaEnergyUnitAnalyser:
    def test_single_score_file(self):
        analyser = RosettaEnergyUnitAnalyser(score_file=sample_score_file)
        assert analyser.best_decoy == best_decoy

    def test_multiple_score_files(self):
        analyser = RosettaEnergyUnitAnalyser(score_file=os.path.dirname(sample_score_file))
        assert analyser.best_decoy == best_decoy_cat

    def test_top3_total_score(self):
        analyser = RosettaEnergyUnitAnalyser(score_file=os.path.dirname(sample_score_file))
        assert analyser.top(3) == top3_total_score

    def test_top3_fa_atr(self):
        analyser = RosettaEnergyUnitAnalyser(score_file=os.path.dirname(sample_score_file))
        assert analyser.top(3, "fa_atr") == top3_fa_atr

    def test_non_existing_file(self):
        with pytest.raises(FileNotFoundError):
            RosettaEnergyUnitAnalyser(score_file=os.path.join(sample_score_file, "non_existing_file.sc"))

    def test_missing_score_term(self):
        with pytest.raises(ValueError):
            RosettaEnergyUnitAnalyser(score_file=sample_score_file, score_term="missing_score_term")


# Run pytest to execute tests
if __name__ == "__main__":
    pytest.main()
