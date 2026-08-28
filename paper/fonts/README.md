# Bundled CJK fallback fonts

Place these two files here:

- `FandolSong-Regular.otf`
- `FandolSong-Bold.otf`

The paper preamble uses this order:

1. Windows `SimSun` when available;
2. the repository-local Fandol OTF files in this directory;
3. TeX Live's installed Fandol family as a final fallback.

This avoids TeX Live/fontconfig differences around `BoldFont=...otf` file-name resolution.
