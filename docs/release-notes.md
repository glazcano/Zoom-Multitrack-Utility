## H8 Studio 0.11.0

- Console now combines aligned horizontal waveforms and a shared time ruler with a compact monitoring mixer below.
- Channels scroll independently of the waveform time axis, including on narrow windows and with split stereo inputs.
- Console track tooltips show full names; channel labels identify stereo, mono, and split L/R inputs in both console views and Timeline.
- Double-click any track fader to restore listening gain to 0 dB.
- Input meters hold peaks for 1.2 seconds and clipping indicators for 2 seconds, independently of listening gain.
- Analyze is directly available in the action row for checked takes or the open take: missing audio, silence, low levels, and possible clipping.
- Fedora 44 / Python 3.14 development checks cover the native Wayland Qt interface, lossless WAV/FLAC export, REAPER output, and silent playback/pause/seek through the default audio device. Audible playback still requires manual listening.

Download the package for Windows x64, Fedora 43 x64, macOS Apple Silicon, or macOS Intel after the native packaging workflow succeeds.
Extract the package and keep all its contents together. Fedora requires the libraries in the platform guide.
macOS packages are ad-hoc signed, not notarized. Native playback on macOS still needs manual testing.

Original recordings remain unchanged. MUSIC edits, regions, and overdubs are not yet supported.
