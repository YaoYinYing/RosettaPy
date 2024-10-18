from unittest.mock import patch

import pytest

from RosettaPy.utils.escape import Colors, print_diff, render, zip_render

# Sample ANSI color codes for testing
RESET_CODE = "\033[0m"
BLUE_CODE = "\033[0;34m"
BOLD_CODE = "\033[1m"
ITALIC_CODE = "\033[3m"
RED_CODE = "\033[0;31m"


@pytest.fixture
def mock_isatty():
    return patch("sys.stdout.isatty", return_value=True)


def test_colors_blue_method_no_isatty():
    """Test if the dynamically created method for blue color works correctly."""
    result = Colors.blue("test")
    expected = "test"
    assert result == expected, f"Expected {expected}, got {result}"


@pytest.mark.parametrize(
    "color",
    [
        "blue",
        "bold",
        "red",
        "italic",
    ],
)
def test_colors_method(color, mock_isatty):
    """Test if the dynamically created method for blue color works correctly."""
    color_code = getattr(Colors, color.upper())
    color_func = getattr(Colors, color.lower())
    result = color_func("test")
    expected = f"{color_code}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


def test_render_single_style(mock_isatty):
    result = render("test", "blue")
    expected = f"{Colors.BLUE}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


def test_render_multiple_styles(mock_isatty):
    result = render("test", "blue-bold")
    expected = f"{Colors.BLUE}{Colors.BOLD}test{Colors.RESET}"
    assert result == expected, f"Expected {expected}, got {result}"


# Test cases for the render function
@pytest.mark.parametrize(
    "text, styles, expected",
    [
        ("Hello, World!", "blue-bold", f"{Colors.BLUE}{Colors.BOLD}Hello, World!{Colors.RESET}"),
        ("Test", "red-italic", f"{Colors.RED}{Colors.ITALIC}Test{Colors.RESET}"),
        ("Styled Text", ["green", "bold"], f"{Colors.GREEN}{Colors.BOLD}Styled Text{Colors.RESET}"),
        ("No Style", "", f"No Style{Colors.RESET}"),
        (
            "Invalid Mixed Style",
            "blue-invalid-italic",
            f"{Colors.RED}{Colors.ITALIC}Invalid Mixed Style{Colors.RESET}",
        ),
    ],
)
def test_render(mock_isatty, text, styles, expected):

    # Test render function with different styles
    assert render(text, styles) == expected


# Test cases for the print_diff function
def test_print_diff():

    title = "Test Diff"
    labels = {"Label1": "Value1", "Label2": "Value2"}
    label_colors = ["red", "green"]
    title_color = "light_purple"

    # Mock print to capture the output
    with patch("builtins.print") as mock_print:
        print_diff(title, labels, label_colors, title_color)

    # Verify the print calls
    assert mock_print.call_count == 3
    mock_print.assert_any_call(f"{Colors.LIGHT_PURPLE}{Colors.BOLD}{Colors.NEGATIVE}Test Diff{Colors.RESET}")
    mock_print.assert_any_call(
        f"{Colors.RED}{Colors.BOLD}{Colors.ITALIC}Label1{Colors.RESET} "
        f"{Colors.RED}{Colors.BOLD}{Colors.NEGATIVE} - {Colors.RESET} "
        f"{Colors.RED}{Colors.BOLD}Value1{Colors.RESET}"
    )
    mock_print.assert_any_call(
        f"{Colors.GREEN}{Colors.BOLD}{Colors.ITALIC}Label2{Colors.RESET} "
        f"{Colors.GREEN}{Colors.BOLD}{Colors.NEGATIVE} + {Colors.RESET} "
        f"{Colors.GREEN}{Colors.BOLD}Value2{Colors.RESET}"
    )


# Test cases for the zip_render function
def test_zip_render():

    labels = {"Label1": "Value1", "Label2": "Value2"}
    label_colors = ["red", "green"]
    diff_labels = ["-", "+"]

    # Mock print to capture the output
    with patch("builtins.print") as mock_print:
        zip_render(labels, label_colors, diff_labels)

    # Verify the print calls
    assert mock_print.call_count == 2
    mock_print.assert_any_call(
        f"{Colors.RED}{Colors.BOLD}{Colors.ITALIC}Label1{Colors.RESET} "
        f"{Colors.RED}{Colors.BOLD}{Colors.NEGATIVE} - {Colors.RESET} "
        f"{Colors.RED}{Colors.BOLD}Value1{Colors.RESET}"
    )
    mock_print.assert_any_call(
        f"{Colors.GREEN}{Colors.BOLD}{Colors.ITALIC}Label2{Colors.RESET} "
        f"{Colors.GREEN}{Colors.BOLD}{Colors.NEGATIVE} + {Colors.RESET} "
        f"{Colors.GREEN}{Colors.BOLD}Value2{Colors.RESET}"
    )


# Test cases for edge cases in the render function
def test_render_with_invalid_style():

    text = "Hello, World!"
    styles = "unknown-style"

    # If the style is not found, it should not apply any style formatting
    assert render(text, styles) == f"Hello, World!{Colors.RESET}"
