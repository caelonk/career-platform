---
target: public home page
total_score: 13
max_score: 32
na_heuristics: 7,10
p0_count: 1
p1_count: 3
target_identity: "file:C:\\Users\\caekn\\career-platform\\app\\templates\\public\\home.html"
target_fingerprint: "sha256:a0bc913aab4e4cfd14b84780fc1122e254604663a000984f4dcf2f7b8af335b3"
target_path: "C:\\Users\\caekn\\career-platform\\app\\templates\\public\\home.html"
timestamp: 2026-10-06T22-21-39Z
slug: app-templates-public-home-html
---
Method: dual-agent (A: design review · B: detector + browser)
Target: app/templates/public/home.html (live data via SSH tunnel to the VM)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | No current-page state in nav; resume links don't say they open a PDF |
| 2 | Match System / Real World | 2 | "Resume highlights" is actually a project list; "Profile" means home; "Roadmap" is not recruiter language |
| 3 | User Control and Freedom | 2 | Detail pages only offer "Back to profile"; no next project, no contact |
| 4 | Consistency and Standards | 1 | `.button` CTAs render as raw links; featured project appears twice; detail headline repeats home summary verbatim |
| 5 | Error Prevention | 2 | Bare mailto Contact; Admin link in public nav beside Resume |
| 6 | Recognition Rather Than Recall | 2 | Cards show no role/org/date/tech although the data model has them |
| 7 | Flexibility and Efficiency | n/a | Single-purpose portfolio page |
| 8 | Aesthetic and Minimalist Design | 1 | 90-word hero wall, duplicate card, three "coming soon" cards, no type or spacing scale |
| 9 | Error Recovery | 1 | Unknown slug returns raw JSON `{"detail":"Project not found."}`; owner-facing empty states |
| 10 | Help and Documentation | n/a | Portfolio needs no help system |
| **Total** | | **13/32** | **Poor (41%)** |

## Design Specificity Verdict

LLM: Nothing visual is authored for Caelon. The only styling is a generic white card (1rem radius, soft shadow) on blue-gray, an uppercase blue eyebrow, and Arial, applied identically to every block. The content is specific and strong (10,000-user dispatch rollout, 47-control GDPR/CCPA framework, 5-run LLM consensus layer); the design flattens it. Hardcoded eyebrow "Business Transformation" (home.html:8) and Roadmap filler (public.py:27-31) read as consultancy template, not an IS/analytics builder.

Root cause (both assessments agree, verified): site.css is 52 lines and styles only :root, body, .error-page, .card, .eyebrow, h1, p. The templates use .page-shell, .site-header, .nav, .hero, .headline, .cta-row, .button, .button.secondary, .section-block, .project-card, .placeholder-card, none of which have rules. Unchanged since the first commit (ed50790).

Deterministic scan: CLI on templates returned clean, but it could not resolve the Jinja stylesheet link, so that is weak evidence. Rendered-page scan with CSS: overused-font (Arial, 100% of text) and flat-type-hierarchy (h2/h3 at 16px; likely false positive from clamp() resolution, though h2/h3 truly have no custom sizes). Browser overlay: overused-font and kicker-above-heading (p.eyebrow above h1, home.html:8-9). Project page reported clean despite the same eyebrow and font, so the detector was inconsistent there. The detector missed the biggest issue: unstyled component classes.

## Overall Impression

Strong copy inside a page that looks unfinished. Largest opportunity: write the missing layout and component CSS; most heuristic scores move with that one change.

## What's Working

- Copy is metric-led and specific; the summaries name real systems and scale.
- Structure is sound: one h1, h2 sections, h3 cards, semantic header/nav/main/article, empty sections hidden by conditionals, a case-study data model.
- Contrast passes: muted #4b5563 ~7.5:1, accent #1d4ed8 ~6.7:1 on white.

## Priority Issues

- [P0] Layout and component CSS missing. CTAs render as touching underlined links, cards stack with no gap, nav jammed top-left, h2s flush at x=0, 32rem cards pinned left at desktop width. Fix: style .page-shell (centered ~64rem + gutter), .site-header/.nav, .button/.secondary, .cta-row, .section-block rhythm, .headline; let cards fill the shell. Command: /impeccable layout, then /impeccable polish.
- [P1] Page ends on "coming soon" and duplicates the featured project. Fix: remove Roadmap (home.html:47-55, public.py:27-31), drop the featured project from the list or promote it to one larger card, rename "Resume highlights" to "Projects", end with a contact block. Command: /impeccable distill.
- [P1] No identity. Arial everywhere, template card look, consultancy eyebrow. Fix: real type pairing and scale, data-driven or removed eyebrow, metrics as large numerals, role/org/date tags from existing fields. Command: /impeccable typeset, then /impeccable bolder.
- [P1] Detail pages thinner than the home card. media_links (demo/GitHub) built by the service but never rendered; summary repeated; metrics as a bullet list. Fix: render media_links, role, org, dates; stat tiles; next-project and contact CTAs. Command: /impeccable clarify.
- [P2] Edge cases and states. Raw JSON 404 for bad slug and missing PDF; empty white hero card when profile is missing; owner-facing empty-state copy; no :focus-visible style; no skip link; Admin in public nav. Command: /impeccable harden.

## Persona Red Flags

Jordan (recruiter, 10-second skim): headline and 90-word summary run together; no sentence stating target role and availability; CTAs don't look clickable; "Resume highlights" turns out to be projects; no LinkedIn, location, or grad date.

Riley (stress tester): /projects/bad-slug returns raw JSON; missing profile leaves an empty hero card; zero projects shows two differently worded empty messages and still renders Roadmap; no line clamping on long titles.

Casey (mobile, from CSS): cards left-aligned at 90vw with uneven gutters; h2s against the screen edge; ~18px-tall inline nav links with Admin beside Resume; adjacent tiny CTA links; hero paragraph fills the first screen so no project shows above the fold.

## Minor Observations

- title is only "Caelon King"; no meta description, Open Graph tags, or favicon, so shared links get no preview.
- Global `p { color: var(--muted) }` makes the headline the same gray as body copy.
- Links are browser default #0000EE, clashing with --accent.
- Resume link lacks a "(PDF)" label.

## Questions to Consider

- If a recruiter reads only the first viewport, which sentence and which number should they leave with, and is either visible now?
- Builder's portfolio or transformation consultant's site? The content argues builder; the eyebrow and Roadmap argue consultant.
- Should the home page lead with the Technician Dispatch story as one full case study instead of five equal cards?
