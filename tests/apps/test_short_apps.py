import os
import pytest
from ..conftest import no_rosetta


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize("num_mut", [1, 2])
def test_app_mutate_relax(num_mut):
    from RosettaPy.app.mutate_relax import main

    main(num_mut)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize(
    "start_from",
    [
        None,
        (
            -13.218,
            6.939,
            6.592,
        ),
    ],
)
def test_app_rosettaligand(start_from):
    from RosettaPy.app.rosettaligand import main

    main(start_from)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
def test_app_supercharge():
    """
    Test the supercharge function with real parameters from Rosetta.
    """
    from RosettaPy.app import supercharge

    pdb = "tests/data/3fap_hf3_A.pdb"
    supercharge(pdb, nproc=os.cpu_count())


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize("dualspace", [True, False])
def test_app_fastrelax(dualspace):
    from RosettaPy.app.fastrelax import main

    main(dualspace)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize("legacy", [True, False])
def test_app_cart_ddg(legacy):
    from RosettaPy.app.cart_ddg import main

    main(legacy)
