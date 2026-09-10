"""Visual treatment for the candidate-facing Streamlit application."""


APP_STYLES = """
<style>
  :root {
    color-scheme: light;
    --ig-ink: #172033;
    --ig-muted: #607087;
    --ig-blue: #0d80b4;
    --ig-teal: #55c6c8;
    --ig-lime: #c5f21f;
    --ig-line: #d9e3ec;
    --ig-soft: #f4f8fb;
  }

  [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(circle at 82% 8%, rgba(85, 198, 200, .22), transparent 28rem),
      linear-gradient(135deg, #eef4f7 0%, #f8fafc 52%, #edf5f6 100%);
  }

  [data-testid="stHeader"] { background: transparent; }

  [data-testid="stMainBlockContainer"] {
    max-width: 960px;
    margin-top: 2rem;
    margin-bottom: 2rem;
    padding: 2.1rem 2.5rem 2.7rem;
    background: rgba(255, 255, 255, .98);
    border: 1px solid rgba(205, 219, 230, .95);
    border-radius: 24px;
    box-shadow: 0 22px 50px rgba(44, 62, 80, .14), 0 2px 6px rgba(44, 62, 80, .08);
    color: var(--ig-ink);
  }

  .ig-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 2.15rem;
  }

  .ig-brand {
    display: flex;
    align-items: center;
    gap: .7rem;
    color: var(--ig-ink);
    font-size: .78rem;
    font-weight: 850;
    line-height: 1.05;
    letter-spacing: .055em;
  }

  .ig-mark {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    color: white;
    border-radius: 11px 11px 11px 3px;
    background: linear-gradient(135deg, var(--ig-blue), var(--ig-teal) 65%, var(--ig-lime));
    box-shadow: 0 6px 14px rgba(13, 128, 180, .24);
  }

  .ig-steps {
    display: flex;
    align-items: center;
    gap: .65rem;
    color: #8793a2;
    font-size: .7rem;
    font-weight: 800;
    letter-spacing: .045em;
  }

  .ig-step.active {
    color: var(--ig-ink);
    border-bottom: 2px solid var(--ig-blue);
    padding-bottom: .28rem;
  }

  .ig-kicker {
    color: var(--ig-blue);
    font-size: .73rem;
    font-weight: 850;
    letter-spacing: .09em;
    margin-bottom: .25rem;
  }

  .ig-subtitle {
    color: #435169;
    margin-top: -.45rem;
    margin-bottom: 1.3rem;
  }

  .ig-upload-note {
    min-height: 176px;
    padding: 1.35rem 1.45rem;
    border: 1px solid var(--ig-line);
    border-radius: 14px;
    background: linear-gradient(160deg, #f8fbfd, #f1f8f9);
  }

  .ig-upload-note h4 { margin: 0 0 .8rem; }
  .ig-upload-note p { margin: .5rem 0; }

  .ig-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(205px, 1fr));
    gap: .85rem;
    margin: 1rem 0 1.35rem;
  }

  .ig-card {
    padding: 1rem 1.05rem;
    border: 1px solid var(--ig-line);
    border-radius: 13px;
    background: #fff;
  }

  .ig-card-title {
    color: var(--ig-ink);
    font-size: .93rem;
    font-weight: 800;
    margin-bottom: .35rem;
  }

  .ig-card-meta {
    color: var(--ig-muted);
    font-size: .77rem;
    margin-bottom: .45rem;
  }

  .ig-card-copy {
    color: #3d4b61;
    font-size: .82rem;
    line-height: 1.5;
  }

  .ig-question {
    padding: 1.35rem 1.4rem;
    border: 1px solid var(--ig-line);
    border-left: 5px solid var(--ig-blue);
    border-radius: 14px;
    background: linear-gradient(145deg, #ffffff, #f5fafb);
    color: var(--ig-ink);
    font-size: 1.18rem;
    font-weight: 720;
    line-height: 1.55;
    margin: .65rem 0 1rem;
  }

  .ig-pill {
    display: inline-block;
    margin-right: .4rem;
    padding: .28rem .58rem;
    border-radius: 999px;
    background: #e9f6fa;
    color: #166985;
    font-size: .72rem;
    font-weight: 760;
  }

  .ig-complete {
    padding: 1.6rem;
    border: 1px solid #cfe1c1;
    border-radius: 16px;
    background: linear-gradient(145deg, #faffef, #f5faf8);
    text-align: center;
  }

  [data-testid="stMarkdownContainer"] h1,
  [data-testid="stMarkdownContainer"] h2,
  [data-testid="stMarkdownContainer"] h3,
  [data-testid="stMarkdownContainer"] h4,
  [data-testid="stMarkdownContainer"] p,
  [data-testid="stMarkdownContainer"] li,
  [data-testid="stWidgetLabel"] p {
    color: var(--ig-ink) !important;
  }

  [data-testid="stCaptionContainer"],
  [data-testid="stCaptionContainer"] p { color: #596579 !important; }

  [data-testid="stFileUploaderDropzone"] {
    min-height: 176px;
    background: #f1fafc;
    border: 1.5px dashed #5fb6c6;
    border-radius: 14px;
  }

  /* Streamlit builds the uploaded-file chip from theme colors after upload.
     Pin the completed state so a global dark preference cannot turn it black. */
  [data-testid="stFileChip"] {
    color: var(--ig-ink) !important;
    background: #ffffff !important;
    border: 1px solid #cddbe6 !important;
    box-shadow: 0 2px 5px rgba(44, 62, 80, .08);
  }

  [data-testid="stFileChip"] *,
  [data-testid="stFileChipName"] {
    color: var(--ig-ink) !important;
  }

  [data-testid="stFileChip"] > div:first-child,
  [data-testid="stFileChip"] > div:first-child * {
    color: #ffffff !important;
    background: var(--ig-ink) !important;
  }

  [data-testid="stFileChipDeleteBtn"] button,
  [data-testid="stFileChipDeleteBtn"] button * {
    color: #435169 !important;
    background: transparent !important;
    border-color: transparent !important;
  }

  [data-testid="stAlert"] p,
  [data-testid="stExpander"] summary,
  [data-testid="stFileUploaderDropzone"] * { color: #26364d !important; }

  textarea, input {
    color: var(--ig-ink) !important;
    background: #fff !important;
  }

  .stButton > button,
  [data-testid="stFormSubmitButton"] > button {
    min-height: 2.8rem;
    border-radius: 8px;
    font-weight: 780;
  }

  button[kind="primary"] {
    color: #172033 !important;
    background: var(--ig-lime) !important;
    border-color: #b7df16 !important;
  }

  button[kind="primary"] *,
  button[kind="primary"] p {
    color: #172033 !important;
  }

  button[kind="secondary"] {
    color: #ffffff !important;
    background: #172033 !important;
    border-color: #172033 !important;
  }

  button[kind="secondary"] *,
  button[kind="secondary"] p {
    color: #ffffff !important;
  }

  button[kind="secondary"]:hover {
    color: #ffffff !important;
    background: #26364d !important;
    border-color: #26364d !important;
  }

  @media (max-width: 700px) {
    [data-testid="stMainBlockContainer"] {
      margin-top: .5rem;
      padding: 1.35rem 1rem 2rem;
      border-radius: 16px;
    }
    .ig-header { align-items: flex-start; }
    .ig-steps { gap: .35rem; font-size: .62rem; }
  }
</style>
"""


__all__ = ["APP_STYLES"]
