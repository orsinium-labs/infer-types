try:
    from yapf.yapflib.style import CreateGoogleStyle
    from yapf.yapflib.yapf_api import FormatCode
except ImportError:
    FormatCode = None
try:
    from autopep8 import fix_code
except ImportError:
    fix_code = None
try:
    from black import format_str
    from black.mode import Mode
except ImportError:
    format_str = None  # type: ignore


def format_code(source: str) -> str:
    """Run autoformatter on the given code (if installed).

    Currently supported:
        + black
        + yapf
        + autopep8
    """
    # try formatting code using black
    if format_str is not None:
        return format_str(source, mode=Mode())

    # if black is not available, try yapf and autopep8
    if FormatCode is not None:
        source, _changed = FormatCode(
            source,
            style_config=CreateGoogleStyle(),
        )
    if fix_code is not None:
        source = fix_code(source)
    return source
