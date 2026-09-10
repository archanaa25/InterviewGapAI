# Yusuf Farooqi

**Machine Learning Engineer moving into AI Engineering**  
yusuf.farooqi@example.com

## Professional Summary
Engineer adapting open text models to specialist vocabulary in insurance and clinical coding. Five years of Python work, mostly training runs, model adaptation, and getting models to run within available hardware.

## Technical Skills
Python, PyTorch, Hugging Face libraries, NumPy, CUDA, Docker, Git, Jupyter, shell scripting.

## Work Experience
**Machine Learning Engineer — Larkspur Grid | Mar 2023–Present**
- Adapted an open text model to insurance wording so that claim notes were continued in house phrasing rather than general prose.
- Investigated why long claim histories were truncated and reorganised inputs to stay inside the model's context limit.
- Found that specialist terms were being split into many small pieces, inflating input length and cost, and adjusted the vocabulary handling accordingly.
- Reduced memory use with reduced-precision weights so a larger model fit on the available GPUs.
- Compared response cost and speed across three model sizes to choose what the team could afford to run.

**Data Engineer — Ochre Lane Health | Aug 2021–Feb 2023**
- Built Python pipelines preparing clinical coding datasets, including de-duplication and format normalisation.
- Packaged training runs so a colleague could reproduce a result from a single command.

## Selected Project
**Clinical phrase tagger:** Trained a smaller model to label diagnosis phrases after the largest available model proved too slow for the intended use. Documented the trade-off between size, speed, and vocabulary coverage for the team.

## Education
MSc, Computer Science — Fictional Ardenwood University, 2021.  
BSc, Mathematics — Fictional Ardenwood University, 2019.
