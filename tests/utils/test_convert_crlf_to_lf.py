import pytest

# Import the function to be tested
from RosettaPy.utils.tools import (
    convert_crlf_to_lf,  # Replace with the actual module name
)


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
    "input_content, expected_content, contains_crlf, expect_warning",
    [
        # Positive Cases
        ("Line 1\nLine 2\n", "Line 1\nLine 2\n", False, False),  # No CRLF
        ("Line 1\r\nLine 2\n", "Line 1\nLine 2\n", True, True),  # Mixed line endings
        ("Line 1\r\nLine 2\r\n", "Line 1\nLine 2\n", True, True),  # Only CRLF
        ("", "", False, False),  # Empty file
    ],
)
def test_convert_crlf_to_lf(create_temp_file, input_content, expected_content, contains_crlf, expect_warning):
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
    else:
        with convert_crlf_to_lf(input_file) as output_file:
            assert output_file == input_file
