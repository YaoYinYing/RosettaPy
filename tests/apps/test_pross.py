import pytest
from ..conftest import no_rosetta, is_github_actions


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
def test_app_pross(use_docker):
    from RosettaPy.app.pross import main

    main(use_docker)
