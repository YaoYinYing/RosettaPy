import os
import pytest
from ..conftest import no_rosetta, is_github_actions


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize(
    "num_mut, use_docker",
    [
        pytest.param(
            1,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (1, False),
        pytest.param(
            2,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (2, False),
    ],
)
def test_app_mutate_relax(num_mut, use_docker):
    from RosettaPy.app.mutate_relax import main

    main(num_mut, use_docker)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize(
    "start_from, use_docker",
    [
        pytest.param(
            None,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (None, False),
        pytest.param(
            (-13.218, 6.939, 6.592),
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        ((-13.218, 6.939, 6.592), False),
    ],
)
def test_app_rosettaligand(start_from, use_docker):
    from RosettaPy.app.rosettaligand import main

    main(start_from, use_docker)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize(
    "use_docker",
    [
        pytest.param(
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        False,
    ],
)
def test_app_supercharge(use_docker):
    """
    Test the supercharge function with real parameters from Rosetta.
    """
    from RosettaPy.app.supercharge import main

    main(use_docker)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize(
    "dualspace, use_docker",
    [
        pytest.param(
            True,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (True, False),
        pytest.param(
            False,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (False, False),
    ],
)
def test_app_fastrelax(dualspace, use_docker):
    from RosettaPy.app.fastrelax import main

    main(dualspace, use_docker)


@pytest.mark.integration
@pytest.mark.skipif(no_rosetta(), reason="No Rosetta Installed.")
@pytest.mark.parametrize(
    "legacy, use_docker",
    [
        pytest.param(
            True,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (True, False),
        pytest.param(
            False,
            True,
            marks=pytest.mark.skipif(is_github_actions, reason="Skipping docker tests in GitHub Actions"),
        ),
        (False, False),
    ],
)
def test_app_cart_ddg(legacy, use_docker):
    from RosettaPy.app.cart_ddg import main

    main(legacy, use_docker)
