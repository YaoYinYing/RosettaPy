import pytest


@pytest.mark.order(-2)
@pytest.mark.integration
def test_app_pross(test_node_hint):
    from RosettaPy.app.pross import main

    main(test_node_hint)
