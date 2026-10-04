## H8 Studio 0.8.0

- Fixed looping: **Loop** works without an export selection. **A–B…** sets an independent, saved loop range; without one, the entire take repeats.
- Amber loop markers appear in all three views. Export ranges remain independent.
- English is now the default interface language. **About…** lets you select English or Spanish for the next launch and lists dependency, app, and system versions.
- Short loops render once per audio callback, split L/R channels share source reads, and only the visible view repaints when its playhead or meters change.
- Space and Home now retain their normal behavior inside text fields.

Download the package for Windows x64, Fedora 43 x64, macOS Apple Silicon, or macOS Intel.
Extract the package and keep all its contents together. Fedora requires the libraries in the platform guide.
macOS packages are ad-hoc signed, not notarized. Native playback on Fedora/macOS still needs manual testing.

Original recordings remain unchanged. MUSIC edits, regions, and overdubs are not yet supported.
