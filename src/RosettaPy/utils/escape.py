"""
Color escape code class
"""

# pylint: disable=too-few-public-methods
# pylint: disable=protected-access

from typing import Any, Dict, List, Optional, Union


class UninitializedClassError(RuntimeError):
    """Raised when a class is used before it is initialized."""


class Colors:
    """Class for ANSI color codes, used to output colored and formatted text on supported terminals.

    source: https://gist.github.com/rene-d/9e584a7dd2935d0f461904b9f2950007

    This class provides various ANSI escape codes for colors and text formatting,
    enabling the addition of color or visual changes to text on compatible terminals.
    It checks `sys.stdout.isatty()` to determine whether to enable these escape codes
    when not outputting to a terminal.
    On Windows systems, if running in a terminal is detected, the `SetConsoleMode`
    function is used to enable VT mode for supporting ANSI escape codes.

    Attributes:
        BLACK, RED, GREEN, BROWN, BLUE, PURPLE, CYAN, LIGHT_GRAY,
        DARK_GRAY, LIGHT_RED, LIGHT_GREEN, YELLOW, LIGHT_BLUE,
        LIGHT_PURPLE, LIGHT_CYAN, LIGHT_WHITE, BOLD, FAINT, ITALIC,
        UNDERLINE, BLINK, NEGATIVE, CROSSED, RESET
    """

    BLACK = "\033[0;30m"

    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"

    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    RESET = "\033[0m"

    CYAN = "\033[0;36m"
    CYAN_BG = "\033[0;44m"

    RED = "\033[0;31m"
    RED_BG = "\033[0;41m"

    MAGENTA = "\033[0;35m"
    MAGENTA_BG = "\033[0;45m"

    # a placeholder class property
    all_colors: List[str] = []

    @classmethod
    def _create_class_methods(cls):
        """Dynamically create class methods for each color and formatting option."""
        if cls.all_colors:
            return

        cls.all_colors = [
            attr_name.lower()
            for attr_name in dir(Colors)
            if attr_name.isupper() and not attr_name.startswith("_") and attr_name != "RESET"
        ]

        for attr_name in cls.all_colors:
            # Get the color code
            color_code = getattr(cls, attr_name.upper())

            # Define a class method that wraps text with the color code
            def color_method(cls, text, color_code=color_code):
                return f"{color_code}{text}{cls.RESET}"

            color_method.__doc__ = f"""Print input text colored as {attr_name}\n
                                    :param text: Text to be colored and printed
                                    :return: Text with color code wrapped
                                    """

            # Attach the method to the class with a lowercase name
            setattr(cls, attr_name, classmethod(color_method))

    # Cancel SGR codes if not writing to a terminal
    if not __import__("sys").stdout.isatty():
        for _ in dir():
            if isinstance(_, str) and _[0] != "_":
                locals()[_] = ""
    else:
        # Set Windows console in VT mode
        if __import__("platform").system() == "Windows":
            kernel32 = __import__("ctypes").windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


Colors._create_class_methods()


def render(text: Union[str, Any], styles: Union[str, List[str]] = "blue-bold") -> str:
    """
    Render the given text with the specified style.

    This method converts the style parameter (which consists of color and format names separated by hyphens)
    into uppercase format suitable for console output, then wraps the text with this format.

    :param text: The text content to be rendered.
    :param styles: The display style of the text, default is 'blue-bold-italic'.
                It can include color and format names, separated by hyphens.
    :return: The formatted text string.
    """

    text = str(text)

    # split all style into a list if it's a string, otherwise assume it's already a list
    # if not isinstance(styles, (str, list)):
    #     raise ValueError("style must be a string or list of strings")

    if isinstance(styles, str):
        styles = styles.split("-")

    # Split the style parameter by hyphens, convert each part to uppercase,
    # but only process the parts that are in the list of all available colors
    # Join them together, wrap the text, and return
    style_strings = [getattr(Colors, _s.upper()) for _s in styles if _s.lower() in Colors.all_colors]
    return f'{"".join(style_strings)}{text}{Colors.RESET}'


def print_diff(
    title: str, labels: Dict[str, Any], label_colors: Optional[List[str]] = None, title_color: Optional[str] = None
):
    """
    Render a diff table with the given title, labels, and colors.
    """
    if not label_colors:
        label_colors = ["red", "green"]

    if not title_color:
        title_color = "light_purple"

    diff_labels = ["-", "+"]

    print(render(f"{title}", f"{title_color}-bold-negative"))
    zip_render(labels=labels, label_colors=label_colors, diff_labels=diff_labels)


def zip_render(labels: Dict[str, Any], label_colors: List[str], diff_labels: Optional[List[str]] = None):
    """
    Zip render labels, colors, and diff labels.
    """

    if not diff_labels:
        diff_labels = [":=" for _ in labels]

    label_widths = max(len(label) for label in labels)

    for (label, text), color, diff_label in zip(labels.items(), label_colors, diff_labels):
        print(
            f'{render(f"{label:{label_widths}}", f"{color}-bold-italic")} '
            f'{render(f" {diff_label} ", f"{color}-bold-negative")} '
            f'{render(str(text), f"{color}-bold")}'
        )


if __name__ == "__main__":
    for i in dir(Colors):
        if i[0:1] != "_" and i != "RESET" and i.isupper():
            print(f"{i:>16} {getattr(Colors, i) + i + Colors.RESET}")

    SAMPLE_TEXT = """Welcome to The World of Color Escape Code."""
    print(f"{Colors.BOLD}{Colors.PURPLE}{Colors.NEGATIVE}{SAMPLE_TEXT}{Colors.RESET}")
