import os
from unittest.mock import Mock, patch

import pytest

from RosettaPy.app.abc import RosettaAppBase
from RosettaPy.node import MpiNode, Native, NodeClassType, NodeHintT, RosettaContainer


class TestRosettaAppBase:
    """Test suite for RosettaAppBase class"""

    @pytest.fixture(scope="function")
    def mock_node_picker(self):
        """Mock the node_picker function"""
        with patch("RosettaPy.app.abc.node_picker") as mock:
            mock.return_value = Mock(spec=NodeClassType)
            yield mock

    @pytest.fixture
    def mock_makedirs(self):
        """Mock os.makedirs"""
        with patch("RosettaPy.app.abc.os.makedirs") as mock:
            yield mock

    @pytest.fixture
    def mock_abspath(self):
        """Mock os.path.abspath"""
        with patch("RosettaPy.app.abc.os.path.abspath") as mock:
            mock.return_value = "/absolute/path"
            yield mock

    @pytest.mark.parametrize(
        "job_id,save_dir,user_opts,node_hint,node_config,kwargs",
        [
            ("test_job", "/home/user", None, "native", None, {}),
            ("job2", "/home/user", ["-opt1", "-opt2"], "docker", {"image": "test"}, {"extra": "value"}),
            ("minimal_job", ".", [], "local", {}, {}),
        ],
    )
    def test_init(
        self, mock_node_picker, mock_makedirs, mock_abspath, job_id, save_dir, user_opts, node_hint, node_config, kwargs
    ):
        """Test RosettaAppBase initialization with various parameters"""
        # Act
        app = TestableRosettaAppBase(
            job_id=job_id,
            save_dir=save_dir,
            user_opts=user_opts,
            node_hint=node_hint,
            node_config=node_config,
            **kwargs,
        )

        # Assert initialization
        assert app.job_id == job_id
        assert app.save_dir == "/absolute/path"  # Should be absolute path
        assert app.user_opts == (user_opts or [])
        assert app._node_hint == node_hint
        assert app._node_config == node_config
        assert app.kwargs == kwargs

        # Check that node was created
        mock_node_picker.assert_called_once_with(node_type=node_hint, **(node_config or {}))

        # Check directory creation
        mock_makedirs.assert_called_once_with(os.path.join(save_dir, job_id), exist_ok=True)
        # mock_abspath.assert_called_once_with(save_dir)

    @pytest.mark.parametrize(
        "initial_hint,expected_hint",
        [
            ("native", "native"),
            ("docker", "docker"),
            ("local", "local"),
            (None, None),
        ],
    )
    def test_node_hint_getter(self, mock_node_picker, mock_makedirs, mock_abspath, initial_hint, expected_hint):
        """Test node_hint property getter"""
        # Arrange
        app = TestableRosettaAppBase(job_id="test", save_dir="/tmp", node_hint=initial_hint)

        # Act & Assert
        assert app.node_hint == expected_hint

    @pytest.mark.parametrize(
        "initial_config,expected_config",
        [
            ({"key": "value"}, {"key": "value"}),
            ({}, {}),
            (None, {}),
            ({"a": 1, "b": "test"}, {"a": 1, "b": "test"}),
        ],
    )
    def test_node_config_getter(self, mock_node_picker, mock_makedirs, mock_abspath, initial_config, expected_config):
        """Test node_config property getter"""
        # Arrange
        app = TestableRosettaAppBase(job_id="test", save_dir="/tmp", node_config=initial_config)

        # Act & Assert
        assert app.node_config == expected_config

    @pytest.mark.parametrize(
        "new_hint, new_config, expected_node_type",
        [
            ("docker", {}, RosettaContainer),
            ("docker_mpi", {}, RosettaContainer),
            ("native", {}, Native),
            ("mpi", {}, MpiNode),
            ("docker", {"image": "rosettacommons/rosetta:latest", "prohibit_mpi": True}, RosettaContainer),
            ("docker_mpi", {"image": "rosettacommons/rosetta:mpi", "prohibit_mpi": False}, RosettaContainer),
            ("native", {"nproc": 4}, Native),
            ("mpi", {"nproc": 4}, MpiNode),
        ],
    )
    def test_node_setter(self, mock_makedirs, mock_abspath, new_hint, new_config, expected_node_type):
        """Test node_hint setter updates node correctly"""
        # Arrange
        app = TestableRosettaAppBase(
            job_id="test",
            save_dir="/tmp",
            node_hint="native",
            node_config={},
        )
        initial_node = app.node  # Store initial node

        with patch("RosettaPy.app.abc.node_picker") as patch_node_picker:

            # Act
            app.node = (new_hint, new_config)
            patch_node_picker.assert_called_once_with(node_type=new_hint, **new_config)

            # Assert

            assert app._node_hint == new_hint
            # assert isinstance(app.node, expected_node_type)
            # Verify node was updated (not the same as initial)
            assert app.node != initial_node


# Concrete implementation for testing since RosettaAppBase is abstract
class TestableRosettaAppBase(RosettaAppBase):
    """Concrete implementation of RosettaAppBase for testing purposes"""
