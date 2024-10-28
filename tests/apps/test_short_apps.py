import pytest


@pytest.mark.integration
@pytest.mark.parametrize(
    "num_mut",
    (1, 2),
)
def test_app_mutate_relax(num_mut, test_node_hint):
    from RosettaPy.app.mutate_relax import main

    main(num_mut, test_node_hint)


@pytest.mark.integration
@pytest.mark.parametrize(
    "start_from",
    [None, (-13.218, 6.939, 6.592)],
)
def test_app_rosettaligand(start_from, test_node_hint):
    from RosettaPy.app.rosettaligand import main

    main(start_from, test_node_hint)


@pytest.mark.integration
def test_app_supercharge(test_node_hint):
    """
    Test the supercharge function with real parameters from Rosetta.
    """
    from RosettaPy.app.supercharge import main

    main(test_node_hint)


@pytest.mark.integration
@pytest.mark.parametrize(
    "dualspace",
    [
        (
            True,
            False,
        )
    ],
)
def test_app_fastrelax(dualspace, test_node_hint):
    from RosettaPy.app.fastrelax import main

    main(dualspace, test_node_hint)


@pytest.mark.integration
@pytest.mark.parametrize(
    "legacy",
    [
        (
            False,
            True,
        )
    ],
)
def test_app_cart_ddg(legacy, test_node_hint):
    from RosettaPy.app.cart_ddg import main

    main(legacy, test_node_hint)
