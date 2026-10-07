import pytest

from src.quality_gate import check_quality


@pytest.mark.parametrize("f1", [0.65, 0.8, 1.0])
def test_quality_gate_accepts_threshold_and_above(f1):
    check_quality(f1)


@pytest.mark.parametrize("f1", [0.0, 0.649999])
def test_quality_gate_blocks_low_f1(f1):
    with pytest.raises(ValueError, match="Release blocked"):
        check_quality(f1)


@pytest.mark.parametrize("f1", [float("nan"), float("inf"), -0.1, 1.1])
def test_quality_gate_blocks_invalid_f1(f1):
    with pytest.raises(ValueError, match="Invalid"):
        check_quality(f1)
