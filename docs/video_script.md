# Video script (max 3:00)

Target length: about 2:45. Speak at a calm pace; the demo parts can be recorded first and narrated over.

## 0:00 - 0:20 Opening (required by CS50x)

On screen: a title slide, then the browser.

- Project title: **Generic Job Listing Filter**
- Name: `<your name>`
- GitHub username: `<github>` / edX username: `<edx>`
- City and country: `<city, country>`
- Date recorded: `<date>`

Say: "This is my CS50x final project. It searches job listings and flags the suspicious ones, such as scams and ghost jobs."

## 0:20 - 0:45 What it is

On screen: the page at `http://127.0.0.1:8000/`, empty form.

Say: "Job boards are full of listings that are fake or long dead. This app fetches jobs from a provider, scores each one from 0 to 100 with transparent rules, and shows the reasons. It has a web page and a JSON API that share the same search code."

## 0:45 - 1:45 Live demo

1. (0:45) Type `e`, source `mock`, press Search. Point at the green, amber and red badges.
2. (1:00) Scroll to a red job (for example "Home Assistant"). Read its flags aloud: scam phrases, off-platform contact (WhatsApp).
3. (1:15) Show an amber job: old listing (400 days) or short description. Say: "Amber means some rule fired but not enough to be suspicious."
4. (1:25) Tick "Exclude suspicious jobs" and search again. The red jobs disappear.
5. (1:35) Mention the JSON endpoint: run `curl "http://127.0.0.1:8000/jobs/search?query=python&source=mock"` in a terminal and show the score and flags in the output.

Say: "Everything scored is also saved to SQLite, even the jobs that were hidden."

## 1:45 - 2:20 Architecture

On screen: the file tree in the editor (or a slide).

```
src/job_filter/
  adapters/   base.py  mock.py  adzuna.py
  core/       schemas.py  scam_detector.py  repository.py ...
  api/        routes.py  web.py  search.py  templates/
```

Say: "Three layers. Adapters talk to providers. Core holds the unified model, the detector and the database. API holds the routes and templates. The search flow lives in one function, `run_search`, used by both the page and the JSON endpoint."

## 2:20 - 2:45 One design decision: Adapter pattern and a single model

On screen: `adapters/base.py`, then `adapters/adzuna.py` translation method.

Say: "Each provider has its own native models, and its adapter translates them into one shared model, `JobSummary`. The detector, the database and the page only know `JobSummary`. Adding a new provider means writing one class, and nothing else changes."

## 2:45 - 3:00 Limitations and close

Say: "The detector is heuristic, so it has false positives and false negatives. And Adzuna only returns truncated descriptions, so some phrases can be missed. Thanks for watching."

## Submission checklist (verified on cs50.harvard.edu/x/project)

- [ ] Video is at most 3 minutes and starts with: project title, name, GitHub and edX usernames, city and country, date recorded.
- [ ] Video uploaded to YouTube (unlisted is fine, private is not), or a similar site if YouTube is blocked.
- [ ] Put the video URL in the "Video Demo" line of `README.md`, replacing `<VIDEO_URL_HERE>`.
- [ ] `README.md` has the project title, video URL and description (this one is well over 750 words).
- [ ] Cite AI tool use in code comments, as the project page requires (the README has a short note; add comments in the source files too).
- [ ] Remove `.env`, `.venv` and `jobs.db` from the submitted folder; keep the total under 100 MB.
- [ ] From the project directory: `submit50 cs50/problems/2026/x/project` and log in with GitHub.
- [ ] Submit the CS50 form with the video URL.
- [ ] Load the gradebook at cs50.me/cs50x and claim the certificate.
- [ ] Deadline: 2027-06-30 23:59 UTC.
