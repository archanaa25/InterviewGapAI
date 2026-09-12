"""Static contrast regressions for Streamlit's state-dependent widgets."""

from ui.styles import APP_STYLES


def test_uploaded_file_chip_has_explicit_light_theme_colors() -> None:
    """A selected file must not inherit a black chip from a dark preference."""

    assert '[data-testid="stFileChip"]' in APP_STYLES
    assert '[data-testid="stFileChipName"]' in APP_STYLES
    assert "background: #ffffff !important" in APP_STYLES
    assert '[data-testid="stFileChipDeleteBtn"] button' in APP_STYLES


def test_form_submit_buttons_receive_the_app_button_treatment() -> None:
    """Streamlit names a form's submit button "primaryFormSubmit".

    An exact `button[kind="primary"]` selector therefore skips every button
    inside a form - including the interview's only call to action, which then
    renders in Streamlit's default red instead of the app's palette.
    """

    assert 'button[kind^="primary"]' in APP_STYLES
    assert 'button[kind^="secondary"]' in APP_STYLES
    assert 'button[kind="primary"]' not in APP_STYLES
    assert 'button[kind="secondary"]' not in APP_STYLES
