# Bundled CJK fonts

This directory vendors the Fandol Song faces used by the paper shell:

- `FandolSong-Bold.otf` — the actual bold face for Chinese Song-style text;
- `FandolSong-Regular.otf` — portable regular fallback only when `SimSun` is unavailable.

The intended typography is:

1. English letters and numbers: `Times New Roman` (fallback: TeX Gyre Termes);
2. Chinese regular Song-style text: Windows `SimSun` when available;
3. Chinese `\songti\bfseries`: repository-local `FandolSong-Bold.otf`;
4. machines without `SimSun`: repository-local FandolSong Regular + Bold;
5. if repository fonts are absent, TeX Live's installed Fandol family is the final fallback.

Keep the upstream Fandol license when redistributing the OTF files.
