import pytest

from ..conftest import GITHUB_CONTAINER_ROSETTA_TEST, NO_NATIVE_ROSETTA


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
def test_app_pross(use_docker):
    from RosettaPy.app.pross import main

    main(use_docker)
