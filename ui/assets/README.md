# Landing assets

## Hero illustration

Save the landing illustration in this folder as `.png`, `.jpg`, `.jpeg`,
`.webp` or `.svg`.

`hero.*`, `image.*` and `landing.*` are preferred in that order; failing those,
any image in this folder is used, because putting one here is the signal. It
replaces the numbered journey rail in the right-hand column of the upload
screen; with no file present the rail renders instead, so the page is complete
either way.

If the illustration already carries the stage labels (Resume Analysis,
Personalized Interview, Evidence-Based Evaluation, Interview Insights), that is
expected — the rail exists to say the same four things when there is no image,
and only one of the two is ever shown.

Notes:

- Keep it roughly portrait or square. The column is about 40% of a 960px
  container, and the image scales to the column width.
- Export at 2x the displayed size so it stays sharp on high-density screens,
  then compress; this file ships to every visitor.
- Streamlit serves it from disk, so no CDN or external host is involved.
- `ui/styles.py` is imported, not re-executed on rerun, so restart the server
  after changing styling. Adding or replacing an image here needs no restart.
