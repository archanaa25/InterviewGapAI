"""Static contrast regressions for Streamlit's state-dependent widgets."""

from ui.styles import APP_STYLES


def test_uploaded_file_chip_has_explicit_light_theme_colors() -> None:
    """A selected file must not inherit a black chip from a dark preference."""

    assert '[data-testid="stFileChip"]' in APP_STYLES
    assert '[data-testid="stFileChipName"]' in APP_STYLES
    assert "background: #ffffff !important" in APP_STYLES
    assert '[data-testid="stFileChipDeleteBtn"] button' in APP_STYLES
