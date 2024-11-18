import pytest

from RosettaPy.utils.tools import convert_crlf_to_lf


@pytest.fixture
def create_temp_file(tmp_path):
    """
    Fixture to create a temporary file with given content.

    Parameters:
    - tmp_path: pytest fixture providing a temporary directory.

    Returns:
    - A function to create a file with specific content.
    """

    def _create_temp_file(content: str, filename: str = "input.txt") -> str:
        file_path = tmp_path / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    return _create_temp_file


@pytest.mark.parametrize(
    "input_content, expected_content, expect_warning",
    [
        # Positive Cases
        ("Line 1\nLine 2\n", "Line 1\nLine 2\n", False),  # No CRLF
        ("Line 1\r\nLine 2\n", "Line 1\nLine 2\n", True),  # Mixed line endings
        ("Line 1\r\nLine 2\r\n", "Line 1\nLine 2\n", True),  # Only CRLF
        ("", "", False),  # Empty file
    ],
)
def test_convert_crlf_to_lf(create_temp_file, input_content, expected_content, expect_warning):
    """
    Test the convert_crlf_to_lf function for various input scenarios.

    Parameters:
    - create_temp_file: Fixture to create a temporary file.
    - input_content: The content to be written to the input file.
    - expected_content: The expected content of the converted file.
    - contains_crlf: Boolean indicating if the input contains CRLF line endings.
    - expect_warning: Boolean indicating if a warning is expected for conversion.
    """
    # Arrange
    input_file = create_temp_file(input_content)

    # Act & Assert
    if expect_warning:
        with pytest.warns(UserWarning, match="Converting CRLF line endings to LF"), convert_crlf_to_lf(
            input_file
        ) as output_file:
            assert output_file != input_file
            with open(output_file, encoding="utf-8") as f:
                output_content = f.read()
            assert output_content == expected_content
            assert "\r\n" not in output_content

    else:
        with convert_crlf_to_lf(input_file) as output_file:
            assert output_file == input_file


@pytest.mark.parametrize(
    "invalid_input, error_type, error_match",
    [
        ("tests/data/not_exists/flag.txt", OSError, "Failed to read input file"),  # Invalid input: File does not exist
        (None, TypeError, "expected str, bytes or os.PathLike object, not NoneType"),  # Invalid input: None
        (123, OSError, "Bad file descriptor"),  # Invalid input: Non-string
        ({}, TypeError, "expected str, bytes or os.PathLike object, not"),  # Invalid input: Unsupported type
    ],
)
def test_convert_crlf_to_lf_invalid_inputs(invalid_input, error_type, error_match):
    """
    Test the convert_crlf_to_lf function with invalid inputs.
    """
    with pytest.raises(error_type, match=error_match):
        with convert_crlf_to_lf(invalid_input) as _:
            pass
