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
    padding: 1.15rem 1.25rem;
    border: 1px solid var(--ig-line);
    border-radius: 14px;
    background: linear-gradient(160deg, #f8fbfd, #f1f8f9);
  }


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



  /* ---- Stage 1: the candidate's own card -------------------------- */
  .ig-profile {
    border-radius: 18px;
    background: #ffffff;
    overflow: hidden;
    border: 1px solid var(--ig-line);
    box-shadow: 0 6px 20px rgba(10,74,110,.16);
  }
  .ig-profile-head {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    padding: 1.15rem 1.25rem;
    /* White clears 5:1 against every stop in this ramp. */
    background: linear-gradient(115deg, #0a4a6e 0%, #0d6f9c 58%, #11798c 100%);
  }
  .ig-avatar {
    flex: none;
    width: 58px;
    height: 58px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: .01em;
    color: #10303f;
    background: var(--ig-lime);
    box-shadow: 0 3px 14px rgba(197,242,31,.42);
  }
  .ig-profile-id { display: flex; flex-direction: column; min-width: 0; flex: 1 1 190px; }
  .ig-profile-name {
    font-size: 1.5rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.18;
    letter-spacing: -.015em;
  }
  .ig-profile-role {
    align-self: flex-start;
    font-size: .73rem;
    font-weight: 700;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: #ffffff;
    background: rgba(255,255,255,.18);
    border: 1px solid rgba(255,255,255,.28);
    border-radius: 999px;
    padding: .16rem .6rem;
    margin-top: .4rem;
  }
  .ig-stats { display: flex; gap: .5rem; flex: none; }
  .ig-stat {
    min-width: 68px;
    padding: .42rem .6rem .48rem;
    border-radius: 12px;
    background: rgba(255,255,255,.14);
    border: 1px solid rgba(255,255,255,.26);
    border-top: 3px solid var(--ig-lime);
    text-align: center;
  }
  .ig-stat-n { font-size: 1.35rem; font-weight: 800; color: #ffffff; line-height: 1.05; }
  .ig-stat-l {
    font-size: .56rem;
    font-weight: 600;
    letter-spacing: .1em;
    color: rgba(255,255,255,.82);
  }
  .ig-chips {
    display: flex;
    flex-wrap: wrap;
    gap: .32rem;
    padding: .8rem 1.25rem .95rem;
  }
  .ig-chip {
    font-size: .73rem;
    font-weight: 600;
    padding: .22rem .62rem;
    border-radius: 999px;
    background: #eef7fb;
    color: #0b5f85;
    border: 1px solid #cfe7ef;
  }
  .ig-chip-more { background: var(--ig-soft); color: #607087; border-color: var(--ig-line); }

  /* ---- Upload aside ----------------------------------------------- */
  .ig-note-title {
    font-size: .95rem;
    font-weight: 720;
    color: var(--ig-ink);
    margin-bottom: .7rem;
  }
  .ig-note-row {
    display: flex;
    align-items: flex-start;
    gap: .6rem;
    margin-bottom: .6rem;
  }
  .ig-note-ico {
    flex: none;
    width: 28px;
    height: 28px;
    border-radius: 9px;
    display: grid;
    place-items: center;
    font-size: .9rem;
  }
  .ig-note-row b {
    display: block;
    font-size: .8rem;
    font-weight: 660;
    color: var(--ig-ink);
    line-height: 1.3;
  }
  .ig-note-row i {
    display: block;
    font-style: normal;
    font-size: .72rem;
    color: #607087;
    line-height: 1.35;
    margin-top: .05rem;
  }

  /* ---- Stage 2: evidence, framed as coverage not deficit ----------- */
  .ig-ev {
    display: flex;
    align-items: flex-start;
    gap: .7rem;
    padding: .7rem .9rem;
    border: 1px solid var(--ig-line);
    border-left: 3px solid var(--ig-line);
    border-radius: 11px;
    background: #ffffff;
    margin-bottom: .4rem;
  }
  .ig-ev-shown   { border-left-color: #4fae6b; background: linear-gradient(100deg,#f6fdf8,#ffffff 45%); }
  .ig-ev-mark { font-size: 1rem; line-height: 1.35; }
  .ig-ev-body { flex: 1; min-width: 0; }
  .ig-ev-name { font-weight: 680; font-size: .88rem; color: var(--ig-ink); }
  .ig-ev-state { font-size: .73rem; color: #56657c; margin-top: .1rem; }
  .ig-ev-count {
    font-size: .68rem;
    color: #56657c;
    white-space: nowrap;
    padding-top: .12rem;
  }

  /* ---- Stage 2: headline counts instead of a wall of prose --------- */
  .ig-tally { display: flex; flex-wrap: wrap; gap: .55rem; margin: .1rem 0 .8rem; }
  .ig-tally-item {
    flex: 1 1 130px;
    padding: .6rem .8rem .65rem;
    border-radius: 12px;
    border: 1px solid var(--ig-line);
    border-top: 3px solid var(--ig-line);
    background: #ffffff;
  }
  .ig-meter {
    display: flex;
    gap: 2px;
    height: 10px;
    margin: .15rem 0 .6rem;
    border-radius: 999px;
    overflow: hidden;
    background: var(--ig-soft);
  }
  .ig-meter-seg:first-child { border-radius: 999px 0 0 999px; }
  .ig-meter-seg:last-child { border-radius: 0 999px 999px 0; }
  .ig-dot {
    display: inline-block;
    width: .5rem;
    height: .5rem;
    border-radius: 999px;
    margin-right: .32rem;
    vertical-align: baseline;
  }
  .ig-tally-n { font-size: 1.5rem; font-weight: 720; line-height: 1.1; color: var(--ig-ink); }
  .ig-tally-l {
    font-size: .66rem;
    letter-spacing: .05em;
    color: #607087;
    margin-top: .15rem;
  }
  .ig-summary {
    border-left: 3px solid var(--ig-teal);
    padding: .6rem .95rem;
    margin: .1rem 0 .2rem;
    background: var(--ig-soft);
    border-radius: 0 11px 11px 0;
    color: #3d4b61;
    font-size: .87rem;
    line-height: 1.55;
  }
  .ig-reassure {
    font-size: .78rem;
    color: #56657c;
    margin: .15rem 0 .1rem;
  }

  .ig-pending {
    color: #8793a2;
    font-size: .84rem;
    padding: 1.1rem .2rem;
    margin: 0;
  }
  .ig-section-title {
    font-size: .68rem;
    letter-spacing: .13em;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--ig-blue);
    margin: 1.35rem 0 .5rem;
    padding-bottom: .3rem;
    border-bottom: 1px solid var(--ig-line);
  }
  .ig-grid-compact { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
  .ig-grid-compact .ig-card { padding: .75rem .9rem .8rem; }
  .ig-card-count {
    font-size: 1.6rem;
    font-weight: 720;
    line-height: 1.05;
    color: var(--ig-ink);
    margin-top: .35rem;
  }
  .ig-grid-compact .ig-card-meta {
    font-size: .66rem;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: #8793a2;
  }

  @media (max-width: 700px) {
    [data-testid="stMainBlockContainer"] {
      margin-top: .5rem;
      padding: 1.35rem 1rem 2rem;
      border-radius: 16px;
    }
    .ig-header { align-items: flex-start; }
    .ig-steps { gap: .35rem; font-size: .62rem; }
    .ig-profile-head { gap: .6rem; }
    .ig-stats { width: 100%; }
  }
</style>
"""


__all__ = ["APP_STYLES"]
