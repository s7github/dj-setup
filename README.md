# DJ Setup

Windows-first helpers for downloading music with third-party providers. Spotify
is supported today; additional providers can live in their own folders under
`providers/`.

## Spotify setup

1. Install Python 3.10 or newer and Git for Windows. During Python installation,
   enable the Python launcher (`py`).
2. Download or clone this repository.
3. Double-click `providers\spotify\setup.bat`.
4. When prompted, enter the absolute folder where downloaded music should go,
   or press Enter to use the displayed default. The folder is created if needed.
5. Create `providers\spotify\download-links.txt` by copying
   `providers\spotify\download-links.txt.example`, then add one Spotify URL per line.
6. Double-click `providers\spotify\spotify-download.bat`.

The setup wizard installs Zotify from
[Googolplexed0/zotify](https://github.com/Googolplexed0/zotify), creates or
updates its configuration, and sets the download folder, credential saving,
30-second bulk wait, skip-existing options, and MP3 format. Existing Zotify
settings are preserved.

The wizard saves Zotify's configuration under
`%APPDATA%\Zotify\config.json`. It also enables Zotify credential saving, so
sign-in information stays on the local computer and must not be committed or
shared. The repository ignores the local Spotify link list and common generated
files; review your changes before publishing anything.

The download helper marks successfully processed lines `[DONE]`, saves progress
after each URL, skips completed lines, and continues after a failed URL. Failed
downloads are left unmarked and cause a non-zero exit status. Run the batch file
again to retry them. You can also pass a different text file as an argument to
`spotify-download.bat`.

To run Zotify directly from a terminal, use the same Python installation used
by setup, for example `py -3 -m zotify <Spotify URL>`.
