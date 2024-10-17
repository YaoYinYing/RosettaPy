from unittest.mock import patch

import pytest

from RosettaPy.utils.escape import Colors, render

# Sample ANSI color codes for testing
RESET_CODE = "\033[0m"
BLUE_CODE = "\033[0;34m"
BOLD_CODE = "\033[1m"
ITALIC_CODE = "\033[3m"
RED_CODE = "\033[0;31m"


def test_colors_blue_method_no_isatty():
    """Test if the dynamically created method for blue color works correctly."""
    result = Colors.blue("test")
    expected = "test"
    assert result == expected, f"Expected {expected}, got {result}"


@patch("sys.stdout.isatty", return_value=True)
def test_colors_blue_method(mock_isatty):
    """Test if the dynamically created method for blue color works correctly."""
    result = Colors.blue("test")
    expected = f"{Colors.BLUE}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


@patch("sys.stdout.isatty", return_value=True)
def test_colors_bold_method(mock_isatty):
    result = Colors.bold("test")
    expected = f"{Colors.BOLD}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


@patch("sys.stdout.isatty", return_value=True)
def test_colors_italic_method(mock_isatty):
    result = Colors.italic("test")
    expected = f"{Colors.ITALIC}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


@patch("sys.stdout.isatty", return_value=True)
def test_render_single_style(mock_isatty):
    result = render("test", "blue")
    expected = f"{Colors.BLUE}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


@patch("sys.stdout.isatty", return_value=True)
def test_render_multiple_styles(mock_isatty):
    result = render("test", "blue-bold")
    expected = f"{Colors.BLUE}{Colors.BOLD}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


@patch("sys.stdout.isatty", return_value=True)
def test_create_class_methods(mock_isatty):
    """Test that _create_class_methods dynamically creates methods for all color/format options."""
    # Ensure that the method has been run and created the methods
    Colors._create_class_methods()

    # Check that all dynamically generated methods exist and work correctly
    for color_name in Colors.all_colors:
        color_method = getattr(Colors, color_name, None)
        assert color_method is not None, f"Method {color_name} should be dynamically created."

        # Test that the method works and returns text wrapped in the corresponding ANSI code
        color_code = getattr(Colors, color_name.upper())
        result = color_method("test")
        expected = f"{color_code}test{Colors.RESET}"
        assert result == expected, f"Expected {expected}, got {result} for {color_name}"


def test_create_class_methods_method_count():
    """Test that the correct number of class methods were created by _create_class_methods."""
    Colors._create_class_methods()

    # The number of dynamically created methods should match the number of all_colors
    created_methods = [
        method_name
        for method_name in dir(Colors)
        if callable(getattr(Colors, method_name)) and method_name in Colors.all_colors
    ]
    assert len(created_methods) == len(
        Colors.all_colors
    ), f"Expected {len(Colors.all_colors)} methods, but found {len(created_methods)}"


@patch("sys.stdout.isatty", return_value=True)
def test_create_class_methods_content(mock_isatty):
    """Test that methods created by _create_class_methods return correct content."""
    # Ensure that _create_class_methods has run
    Colors._create_class_methods()

    # Test a specific color/format for correct wrapping
    result = Colors.red("example")
    expected = f"{Colors.RED}example{Colors.RESET}"
    assert result == expected, f"Expected {expected}, but got {result}"

    # Test a different formatting option
    result = Colors.bold("important")
    expected = f"{Colors.BOLD}important{Colors.RESET}"
    assert result == expected, f"Expected {expected}, but got {result}"
