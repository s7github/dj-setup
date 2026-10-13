# DJ Setup

DJ Setup is a Windows-first control panel for a complete DJ music workflow.
It brings source links, downloader choices, local settings, and future library
tools together in one place. Spotify downloads are available now; library
management, playlist tools, tag fixing, analytics, and other providers are
planned and shown as unavailable until implemented.

## Start here

1. Install Python 3.10 or newer and Git for Windows. Enable the Python launcher
   (`py`) during Python installation.
2. Download or clone this repository.
3. Double-click **`Start DJ Setup.bat`** in the repository root.
4. Open **Settings** to choose where downloads are stored. The panel keeps its
   settings in `%APPDATA%\DJ Setup\settings.json` and applies the destination to
   Zotify without requiring manual JSON edits.
5. On **Home** or **Downloads**, choose **Set up / repair** under Zotify. The
   panel installs Zotify and configures MP3, a 30-second bulk wait, credential
   saving, and skip-existing options.
6. Choose **Open song list**, add one Spotify track, album, or playlist URL per
   line, save the file, and click **Start download**.

The URL list is `providers\spotify\download-links.txt` by default. It can be
changed in Settings. Successfully downloaded entries are marked `[DONE]`, so
you can retry the list without repeating completed URLs. Failed entries remain
unmarked.

## Spotify downloader choices

- **Zotify** is integrated with setup, download-folder configuration, and the
  resumable URL list.
- **Spotify Downloader** is an independent Windows GUI project, not bundled or
  installed by this repository. Use **Explore releases** to review it, install
  it yourself, then select `Spotify Downloader.exe` in DJ Setup Settings to
  launch it from the panel. The upstream project currently notes that its
  v2 rework is in progress:
  [WilliamSchack/Spotify-Downloader](https://github.com/WilliamSchack/Spotify-Downloader).

Third-party tools may have different licensing, source, and account
requirements. Review each project before installing or using it.

## Local data and credentials

Zotify's configuration is stored in `%APPDATA%\Zotify\config.json`. Zotify
credential saving is enabled, so sign-in information remains on the local
computer and must not be committed or shared. DJ Setup settings and the local
download URL list are excluded from Git.

To use Zotify from a terminal instead, run `py -3 -m zotify <Spotify URL>` after
setup.
