import pytest

from ..conftest import GITHUB_CONTAINER_ROSETTA_TEST, NO_NATIVE_ROSETTA


@pytest.mark.integration
@pytest.mark.parametrize(
    "num_mut, use_docker",
    [
        pytest.param(
            1,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(
            1,
            False,
            marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed."),
        ),
        pytest.param(
            2,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(2, False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
    ],
)
def test_app_mutate_relax(num_mut, use_docker):
    from RosettaPy.app.mutate_relax import main

    main(num_mut, use_docker)


@pytest.mark.integration
@pytest.mark.parametrize(
    "start_from, use_docker",
    [
        pytest.param(
            None,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(None, False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
        pytest.param(
            (-13.218, 6.939, 6.592),
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(
            (-13.218, 6.939, 6.592), False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")
        ),
    ],
)
def test_app_rosettaligand(start_from, use_docker):
    from RosettaPy.app.rosettaligand import main

    main(start_from, use_docker)


@pytest.mark.integration
@pytest.mark.parametrize(
    "use_docker",
    [
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
    ],
)
def test_app_supercharge(use_docker):
    """
    Test the supercharge function with real parameters from Rosetta.
    """
    from RosettaPy.app.supercharge import main

    main(use_docker)


@pytest.mark.integration
@pytest.mark.parametrize(
    "dualspace, use_docker",
    [
        pytest.param(
            True,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(True, False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
        pytest.param(
            False,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(False, False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
    ],
)
def test_app_fastrelax(dualspace, use_docker):
    from RosettaPy.app.fastrelax import main

    main(dualspace, use_docker)


@pytest.mark.integration
@pytest.mark.parametrize(
    "legacy, use_docker",
    [
        pytest.param(
            True,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(True, False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
        pytest.param(
            False,
            True,
            marks=pytest.mark.skipif(
                not GITHUB_CONTAINER_ROSETTA_TEST, reason="Skipping docker tests in GitHub Actions"
            ),
        ),
        pytest.param(False, False, marks=pytest.mark.skipif(NO_NATIVE_ROSETTA, reason="No Rosetta Installed.")),
    ],
)
def test_app_cart_ddg(legacy, use_docker):
    from RosettaPy.app.cart_ddg import main

    main(legacy, use_docker)
