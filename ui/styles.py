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

  /* Was 176px, which made the upload column tall enough to leave the hero
     illustration stranded at the top of its own column with dead space under
     it. The dropzone only ever holds a button and one line of hint text. */
  [data-testid="stFileUploaderDropzone"] {
    min-height: 104px;
    padding-top: .55rem;
    padding-bottom: .55rem;
    background: #f4fbfd;
    border: 1.5px dashed #7cc6d6;
    border-radius: 14px;
  }

  /* The reference centres the dropzone's contents under a heading rather than
     left-aligning a button against a wide empty box. */
  [data-testid="stFileUploaderDropzone"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
  }

  [data-testid="stFileUploaderDropzone"] > div,
  [data-testid="stFileUploaderDropzoneInstructions"] {
    justify-content: center !important;
    text-align: center;
  }

  .ig-upload-head {
    margin: 0 0 .35rem;
    font-size: .95rem;
    font-weight: 820;
    text-align: center;
    color: var(--ig-ink);
  }

  .ig-upload-formats {
    margin: 0 0 .5rem;
    font-size: .76rem;
    text-align: center;
    color: var(--ig-muted);
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

  /* The reference CTA is a green-to-teal sweep in white type, not flat lime.
     Matched by prefix: Streamlit labels a form's submit button
     "primaryFormSubmit", not "primary", so an exact match left every
     in-form CTA - the whole interview screen - painted Streamlit red. */
  button[kind^="primary"] {
    color: #ffffff !important;
    background: linear-gradient(95deg, #12c06a, #10b6a8) !important;
    border-color: transparent !important;
    min-height: 3.1rem !important;
    font-size: .98rem !important;
    box-shadow: 0 10px 24px rgba(16, 182, 168, .28);
  }

  button[kind^="primary"] *,
  button[kind^="primary"] p {
    color: #ffffff !important;
  }

  button[kind^="primary"]:hover {
    background: linear-gradient(95deg, #0fae5f, #0ea497) !important;
    border-color: transparent !important;
  }

  button[kind^="secondary"] {
    color: #ffffff !important;
    background: #172033 !important;
    border-color: #172033 !important;
  }

  button[kind^="secondary"] *,
  button[kind^="secondary"] p {
    color: #ffffff !important;
  }

  button[kind^="secondary"]:hover {
    color: #ffffff !important;
    background: #26364d !important;
    border-color: #26364d !important;
  }

  /* The top-right sign-in is a quiet secondary door, not a call to action:
     the solid dark default competed with the primary CTA on the same screen.
     Keyed on the widget's own key so no other secondary button changes. */
  .st-key-ig-top-signin button {
    min-height: 2.35rem !important;
    color: var(--ig-ink) !important;
    background: #ffffff !important;
    border: 1px solid var(--ig-line) !important;
    font-size: .82rem !important;
  }

  .st-key-ig-top-signin button * ,
  .st-key-ig-top-signin button p {
    color: var(--ig-ink) !important;
  }

  .st-key-ig-top-signin button:hover {
    background: var(--ig-soft) !important;
    border-color: var(--ig-blue) !important;
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

  /* ---------- landing hero ---------- */

  .ig-tagline {
    margin: -.35rem 0 0 2.55rem;
    font-size: .62rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--ig-muted);
  }

  .ig-hero-title {
    margin: .1rem 0 .55rem;
    font-size: 2.45rem;
    font-weight: 860;
    line-height: 1.08;
    letter-spacing: -.02em;
    color: var(--ig-ink);
  }

  /* The accent half of the headline. A gradient needs a painted background
     clipped to the glyphs, so the fallback colour matters when that is
     unsupported: set it first, then let the clip override it. */
  .ig-hero-accent {
    color: var(--ig-blue);
    background: linear-gradient(95deg, #12a8c4, #5b4bd6 78%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .ig-hero-lede {
    max-width: 34rem;
    margin: 0 0 1.15rem;
    font-size: .95rem;
    line-height: 1.62;
    color: #43536b;
  }

  .ig-secure {
    display: flex;
    align-items: center;
    gap: .4rem;
    margin: .5rem 0 0;
    font-size: .72rem;
    color: var(--ig-muted);
  }

  .ig-cta-note {
    margin: .45rem 0 0;
    font-size: .72rem;
    text-align: center;
    color: var(--ig-muted);
  }

  /* ---------- hero illustration ---------- */

  /* The art is a full-bleed panel, not a framed thumbnail: it runs past the
     container's right padding and up under the header row, which is what
     removes the dead space a centred, shadowed box left beneath it. No
     border or shadow - the source already sits on its own near-white ground,
     so a frame would read as a second edge. */
  /* No negative top margin: it slid the panel up under the header row and
     over the sign-in button. Bleed right only. */
  .st-key-ig-hero-art {
    margin: 0 -3.1rem 0 0;
  }

  /* object-fit:cover lets the panel match the upload column's height instead
     of ending well above it. The focal point is biased left of centre and
     high, which keeps the person and the numbered cards in frame when the
     sides are trimmed. */
  .st-key-ig-hero-art img {
    width: 100%;
    /* 410px keeps the crop to about a tenth of the width. At 480px the
       panel filled the column but cut the hand-lettered notes off both
       edges, which are the parts that explain the four steps. */
    height: 410px;
    object-fit: cover;
    object-position: 50% 34%;
    border-top-left-radius: 20px;
    border-bottom-left-radius: 20px;
  }

  /* The dropzone repeats the accepted formats and size limit that the heading
     above it already states. One statement is enough. */
  [data-testid="stFileUploaderDropzoneInstructions"] span:not([data-testid]) {
    display: none !important;
  }

  @media (max-width: 700px) {
    /* Stacked on a phone: a negative right margin would push it off screen. */
    .st-key-ig-hero-art { margin: .4rem 0 0; }
    .ig-hero-art [data-testid="stImage"] img,
    .ig-hero-art [data-testid="stImageContainer"] img { border-radius: 16px; }
  }

  /* ---------- journey rail (fallback when no illustration is saved) ---------- */

  .ig-rail {
    display: grid;
    gap: .6rem;
  }

  .ig-rail-item {
    display: flex;
    align-items: flex-start;
    gap: .7rem;
    padding: .72rem .85rem;
    background: #fff;
    border: 1px solid var(--ig-line);
    border-radius: 14px;
    box-shadow: 0 6px 16px rgba(44, 62, 80, .06);
  }

  .ig-rail-n {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--ig-blue), var(--ig-teal));
    color: #fff;
    font-size: .72rem;
    font-weight: 800;
  }

  .ig-rail-item b {
    display: block;
    font-size: .82rem;
    font-weight: 800;
    color: var(--ig-ink);
  }

  .ig-rail-item i {
    display: block;
    margin-top: .1rem;
    font-size: .73rem;
    font-style: normal;
    line-height: 1.45;
    color: var(--ig-muted);
  }

  /* ---------- feature strip ---------- */

  .ig-features {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 0;
    margin-top: 1.9rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--ig-line);
  }

  /* Vertical rules between the four items, as in the reference. The first
     child has none, so a wrapped row never starts with a stray line. */
  .ig-feature {
    padding: 0 1.1rem;
    border-left: 1px solid var(--ig-line);
  }

  .ig-feature:first-child {
    padding-left: 0;
    border-left: 0;
  }

  .ig-feature b {
    display: block;
    margin-top: .45rem;
    font-size: .8rem;
    font-weight: 800;
    color: var(--ig-ink);
  }

  .ig-feature i {
    display: block;
    margin-top: .15rem;
    font-size: .73rem;
    font-style: normal;
    line-height: 1.5;
    color: var(--ig-muted);
  }

  .ig-feature-ico {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    font-size: .92rem;
  }

  /* ---------- interviewer console ---------- */

  [data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--ig-line);
  }

  [data-testid="stSidebar"] .ig-brand { margin-bottom: 1.35rem; }

  /* Turn the sidebar radio into nav rows: full-width, icon + label, and a
     tinted pill on the selected one. The radio dot is hidden because the
     highlight already says which row is current, and a dot plus a highlight
     reads as two controls. */
  [data-testid="stSidebar"] [role="radiogroup"] {
    gap: .2rem !important;
  }

  [data-testid="stSidebar"] [role="radiogroup"] > label {
    width: 100%;
    padding: .55rem .7rem;
    border-radius: 10px;
    cursor: pointer;
    transition: background .12s ease;
  }

  [data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: var(--ig-soft);
  }

  /* The radio glyph is kept. Hiding it needs a selector that reaches past
     the screen-reader input wrapper into the flex row, and every candidate
     for that also matched the label text - which silently emptied the whole
     nav. A visible control that looks like a control is the better trade.
     It is shrunk and tinted to the active colour instead. */
  [data-testid="stSidebar"] [role="radiogroup"] > label svg {
    width: 14px;
    height: 14px;
  }

  [data-testid="stSidebar"] [role="radiogroup"] > label p {
    font-size: .86rem !important;
    font-weight: 640 !important;
    color: #3d4b61 !important;
  }

  /* :has() gives us "the label whose input is checked" without a wrapper. */
  [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: #eef1fe;
  }

  [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {
    color: #3f32a0 !important;
    font-weight: 800 !important;
  }

  /* Report sub-navigation: indented, smaller, and visually subordinate to
     the section rows above it. */
  .ig-subnav-title {
    margin: 1rem 0 .2rem .2rem;
    font-size: .66rem;
    font-weight: 850;
    letter-spacing: .09em;
    text-transform: uppercase;
    color: var(--ig-muted);
  }

  .ig-subnav-group {
    margin: .6rem 0 .1rem .75rem;
    font-size: .67rem;
    font-weight: 800;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: #9aa6b6;
  }

  /* Sub-nav buttons are nav rows: flush left, no chrome, no min-height. */
  [data-testid="stSidebar"] [class*="st-key-ig_rep_"] button {
    justify-content: flex-start !important;
    min-height: 2.1rem !important;
    padding: .3rem .7rem .3rem 1.15rem !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    box-shadow: none !important;
  }

  /* Streamlit centres a button's label in a nested flex div, so aligning the
     button alone left the text centred. */
  [data-testid="stSidebar"] [class*="st-key-ig_rep_"] button > div {
    justify-content: flex-start !important;
    width: 100% !important;
  }

  [data-testid="stSidebar"] [class*="st-key-ig_rep_"] button p {
    font-size: .8rem !important;
    font-weight: 600 !important;
    color: #3d4b61 !important;
    text-align: left !important;
  }

  [data-testid="stSidebar"] [class*="st-key-ig_rep_"] button:hover {
    background: var(--ig-soft) !important;
    border-color: var(--ig-line) !important;
  }

  .st-key-ig-subnav [role="radiogroup"] > label {
    padding: .38rem .7rem .38rem 1.15rem;
    border-radius: 8px;
  }

  .st-key-ig-subnav [role="radiogroup"] > label p {
    font-size: .8rem !important;
    font-weight: 600 !important;
  }

  .st-key-ig-subnav [role="radiogroup"] > label:has(input:checked) {
    background: #e8f1fc;
  }

  .st-key-ig-subnav [role="radiogroup"] > label:has(input:checked) p {
    color: #14639e !important;
    font-weight: 800 !important;
  }

  /* The sub-nav rows are already indented under a heading, so their radio
     glyphs are shrunk further to keep the hierarchy readable. */
  .st-key-ig-subnav [role="radiogroup"] > label svg {
    width: 11px;
    height: 11px;
  }

  [data-testid="stSidebar"] hr {
    margin: .9rem 0 !important;
    border-color: var(--ig-line) !important;
  }

  .ig-side-user {
    display: flex;
    align-items: center;
    gap: .6rem;
    margin-top: .5rem;
    padding-top: .9rem;
    border-top: 1px solid var(--ig-line);
  }

  .ig-side-avatar {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--ig-blue), var(--ig-teal));
    color: #fff;
    font-size: .8rem;
    font-weight: 800;
  }

  .ig-side-user b {
    display: block;
    font-size: .82rem;
    color: var(--ig-ink);
  }

  .ig-side-user i {
    display: block;
    font-size: .7rem;
    font-style: normal;
    color: var(--ig-muted);
  }

  /* Panel header: an icon, the title pair, and the run stamp on the right. */
  .ig-panel-head {
    display: flex;
    align-items: center;
    gap: .85rem;
    margin: .2rem 0 1.1rem;
  }

  .ig-panel-ico {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 42px;
    height: 42px;
    border-radius: 12px;
    font-size: 1.15rem;
  }

  .ig-panel-title {
    flex: 1 1 auto;
  }

  .ig-panel-title b {
    display: block;
    font-size: 1.05rem;
    font-weight: 840;
    color: var(--ig-ink);
  }

  .ig-panel-title i {
    display: block;
    margin-top: .1rem;
    font-size: .8rem;
    font-style: normal;
    color: var(--ig-muted);
  }

  .ig-stamp {
    flex: 0 0 auto;
    padding: .45rem .8rem;
    border: 1px solid var(--ig-line);
    border-radius: 11px;
    background: var(--ig-soft);
    font-size: .72rem;
    line-height: 1.35;
    color: var(--ig-muted);
    text-align: right;
  }

  .ig-stamp b {
    display: block;
    color: var(--ig-ink);
    font-weight: 760;
  }

  /* KPI cards. The meter is a magnitude bar, so it is a single hue and is
     only drawn for values that are genuinely a 0-100% fraction - a count
     like "26 judgements" has no meaningful full-width, so it gets a badge
     instead of a bar that would imply one. */
  .ig-kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
    gap: .75rem;
    margin-bottom: 1.15rem;
  }

  .ig-kpi {
    padding: .9rem .95rem 1rem;
    border: 1px solid var(--ig-line);
    border-radius: 15px;
    background: #fff;
    box-shadow: 0 4px 12px rgba(44, 62, 80, .05);
  }

  .ig-kpi-top {
    display: flex;
    align-items: center;
    gap: .55rem;
    margin-bottom: .45rem;
  }

  .ig-kpi-ico {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    font-size: .9rem;
  }

  .ig-kpi-label {
    font-size: .76rem;
    font-weight: 700;
    color: var(--ig-muted);
  }

  .ig-kpi-value {
    font-size: 1.65rem;
    font-weight: 850;
    line-height: 1.1;
    color: var(--ig-ink);
  }

  .ig-meter-track {
    height: 6px;
    margin-top: .6rem;
    border-radius: 999px;
    background: #eef3f8;
    overflow: hidden;
  }

  .ig-meter-fill {
    height: 100%;
    border-radius: 999px;
  }

  .ig-kpi-badge {
    display: inline-block;
    margin-top: .55rem;
    padding: .2rem .5rem;
    border-radius: 999px;
    background: #e8f5ee;
    color: #0a6b34;
    font-size: .69rem;
    font-weight: 750;
  }

  /* Donut legend: the exact count and share sit beside every swatch, so two
     close arcs are compared as numbers rather than by eye. */
  .ig-legend {
    display: grid;
    gap: .45rem;
    padding-top: .35rem;
  }

  .ig-legend-row {
    display: grid;
    grid-template-columns: 12px 1fr auto auto;
    align-items: center;
    gap: .55rem;
    font-size: .8rem;
    color: var(--ig-ink);
  }

  .ig-legend-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
  }

  .ig-legend-row span:nth-child(3) { font-weight: 800; }
  .ig-legend-row span:nth-child(4) { color: var(--ig-muted); min-width: 3.1rem; text-align: right; }

  .ig-insight {
    display: flex;
    gap: .8rem;
    margin-top: 1.1rem;
    padding: .95rem 1.1rem;
    border: 1px solid #cfe6d8;
    border-radius: 14px;
    background: linear-gradient(150deg, #f2fbf5, #f6fbf9);
  }

  .ig-insight-ico {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    background: #dff2e6;
    color: #0a6b34;
  }

  .ig-insight b {
    display: block;
    font-size: .85rem;
    font-weight: 820;
    color: var(--ig-ink);
  }

  .ig-insight span {
    display: block;
    margin-top: .2rem;
    font-size: .8rem;
    line-height: 1.55;
    color: #3d4b61;
  }

  .ig-panel-card {
    padding: 1rem 1.1rem 1.15rem;
    border: 1px solid var(--ig-line);
    border-radius: 15px;
    background: #fff;
  }

  .ig-panel-card-title {
    margin-bottom: .5rem;
    font-size: .88rem;
    font-weight: 820;
    color: var(--ig-ink);
  }

  /* Nudges the refresh button down to sit level with the select beside it,
     which carries a label the button does not. */
  .ig-refresh-pad { height: 1.65rem; }

  /* ---------- results scorecard ---------- */

  .ig-score {
    display: flex;
    gap: 1.6rem;
    align-items: center;
    padding: 1.35rem 1.5rem;
    border: 1px solid var(--ig-line);
    border-radius: 18px;
    background: linear-gradient(135deg, #f7fbfd, #ffffff 60%);
  }

  /* The ring is drawn with a conic gradient rather than a chart library: it
     is one number, and a dependency for one number is not worth the weight. */
  .ig-donut {
    position: relative;
    flex: 0 0 auto;
    width: 132px;
    height: 132px;
    border-radius: 50%;
    display: grid;
    place-items: center;
  }

  .ig-donut::after {
    content: "";
    position: absolute;
    inset: 13px;
    border-radius: 50%;
    background: #ffffff;
  }

  .ig-donut-face {
    position: relative;
    z-index: 1;
    text-align: center;
    line-height: 1.05;
  }

  .ig-donut-score {
    font-size: 2.15rem;
    font-weight: 800;
    color: var(--ig-ink);
  }

  .ig-donut-total {
    font-size: .78rem;
    font-weight: 700;
    color: var(--ig-muted);
  }

  .ig-score-meta h3 {
    margin: 0 0 .2rem;
    font-size: 1.05rem;
    font-weight: 800;
  }

  .ig-score-meta p {
    margin: 0 0 .45rem;
    font-size: .85rem;
    line-height: 1.55;
    color: #43536b;
  }

  .ig-bars { margin-top: 1.1rem; }

  .ig-bar-row {
    display: grid;
    grid-template-columns: 180px 1fr 52px;
    align-items: center;
    gap: .75rem;
    padding: .3rem 0;
  }

  .ig-bar-name {
    font-size: .82rem;
    font-weight: 700;
    color: var(--ig-ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ig-bar-track {
    height: 9px;
    border-radius: 999px;
    background: #e8eef4;
    overflow: hidden;
  }

  .ig-bar-fill {
    height: 100%;
    border-radius: 999px;
  }

  .ig-bar-value {
    font-size: .8rem;
    font-weight: 800;
    text-align: right;
    color: var(--ig-ink);
  }

  /* Band colour is a redundant cue: every row also carries its number, and
     gap rows carry a word, so the screen still reads without hue. */
  .ig-band {
    display: inline-block;
    padding: .16rem .5rem;
    border-radius: 999px;
    font-size: .66rem;
    font-weight: 800;
    letter-spacing: .03em;
    text-transform: uppercase;
  }

  .ig-band-strong { background: #e4f3e4; color: #14631a; }
  .ig-band-developing { background: #e7f0fb; color: #1b4f8f; }
  .ig-band-gap { background: #fdeade; color: #9a3c11; }
  .ig-band-none { background: #eceff3; color: #4a5666; }

  .ig-concept-list {
    margin: .35rem 0 0;
    padding-left: 1.1rem;
    font-size: .84rem;
    line-height: 1.65;
    color: #43536b;
  }

  .ig-res {
    margin-bottom: .7rem;
    padding: .85rem 1rem;
    border: 1px solid var(--ig-line);
    border-left: 4px solid var(--ig-blue);
    border-radius: 12px;
    background: #ffffff;
  }

  .ig-res-title {
    margin: 0 0 .2rem;
    font-size: .9rem;
    font-weight: 760;
  }

  .ig-res-title a { color: #0b5c86; text-decoration: none; }
  .ig-res-title a:hover { text-decoration: underline; }

  .ig-res-meta {
    margin: 0;
    font-size: .76rem;
    color: var(--ig-muted);
  }

  .ig-res-head {
    display: flex;
    align-items: baseline;
    gap: .6rem;
    margin: 0 0 .15rem;
  }

  .ig-res-head h4 {
    margin: 0;
    font-size: .98rem;
    font-weight: 800;
  }

  @media (max-width: 700px) {
    .ig-score { flex-direction: column; text-align: center; }
    .ig-bar-row { grid-template-columns: 120px 1fr 44px; gap: .5rem; }
  }

  /* ---------- featured / from the academy ---------- */

  .ig-featured-head {
    margin: .2rem 0 .7rem;
    padding-top: .9rem;
    border-top: 1px solid var(--ig-line);
  }

  .ig-featured-head h4 {
    margin: 0 0 .15rem;
    font-size: .95rem;
    font-weight: 800;
    letter-spacing: .01em;
  }

  .ig-featured-head p {
    margin: 0;
    font-size: .8rem;
    line-height: 1.55;
    color: var(--ig-muted);
  }

  /* The standing recommendation is the only card on the screen with a filled
     ground, so it reads as a different kind of thing from the scored gaps
     above it rather than as the most urgent one. */
  .ig-highlight {
    margin-bottom: .7rem;
    padding: .95rem 1.05rem;
    border: 1px solid #cfe4d6;
    border-radius: 14px;
    background: linear-gradient(135deg, #f3fbf6, #f7fdfb 70%);
  }

  .ig-highlight-title {
    margin: .4rem 0 .2rem;
    font-size: .96rem;
    font-weight: 800;
  }

  .ig-highlight-title a { color: #0b5c86; text-decoration: none; }
  .ig-highlight-title a:hover { text-decoration: underline; }

  .ig-highlight-note {
    margin: .4rem 0 0;
    font-size: .78rem;
    font-weight: 700;
    color: #14631a;
  }

  .ig-person {
    display: flex;
    align-items: center;
    gap: .6rem;
    padding: .5rem .2rem;
    border-bottom: 1px solid var(--ig-line);
  }

  .ig-person:last-child { border-bottom: 0; }

  .ig-person-mark {
    display: grid;
    place-items: center;
    flex: 0 0 auto;
    width: 26px;
    height: 26px;
    border-radius: 7px;
    background: #e9f2fb;
    color: #14639e;
    font-size: .7rem;
    font-weight: 800;
  }

  .ig-person-body { display: flex; flex-direction: column; line-height: 1.35; }

  .ig-person-body a {
    color: #0b5c86;
    font-size: .87rem;
    font-weight: 760;
    text-decoration: none;
  }

  .ig-person-body a:hover { text-decoration: underline; }

  .ig-person-body i {
    font-style: normal;
    font-size: .74rem;
    color: var(--ig-muted);
  }

  /* ---------- sign-in card ---------- */

  .ig-signin-note {
    margin: 0 0 1rem;
    font-size: .85rem;
    line-height: 1.6;
    color: #43536b;
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
    .ig-hero-title { font-size: 1.85rem; }
    .ig-tagline { margin-left: 0; }
  }
</style>
"""


__all__ = ["APP_STYLES"]
