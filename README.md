# bibi

```
 (\(\
 ( -.-)  bibi
 o_(")(")
```

An intuitive, efficient, and vim-based TUI for bibliography management.

## Install

```
git clone https://github.com/soh3e/bibi
cd bibi
uv sync
uv tool install .
```

## Getting Started

```
bibi init
```

## Dependencies

To copy links to the clipboard, `bibi` uses the following tools in this order:
1. `wl-copy` (from the `wl-clipboard` package) - Wayland
2. `xclip` or `xsel` - X11
3. `pbcopy` - macOS 

If `c` isn't copying anything for you, try installing `wl-clipboard` (Wayland) 
or `xclip`/`xsel` (X11).

## Configuration 

The configuration file is located at ~/.config/bibi/config.toml.

```toml
library_dir = "~/bibi-lib"
```

## Keybinds

Keybinds are made to be as intuitive as possible in relation to `vim`,
but you can find the exact keybinds and corresponding behavior here:

| Key                  | Action                                     |
|----------------------|---------------------------------------------|
| `a`                  | Add an entry, choosing arXiv or a PDF      |
| `j` / `k`            | Move down / up                             |
| `g` / `G`            | Scroll to top / bottom (entry list)        |
| `gg` / `G`           | Scroll to top / bottom (previews/detail)   |
| `enter`              | Toggle the Read checkbox for an entry      |
| `l`                  | View entry details                         |
| `o`                  | Open the entry's file in the browser       |
| `c`                  | Copy the entry's link to the clipboard     |
| `e`                  | Edit the entry (title, authors, year)      |
| `t`                  | Edit the entry's tags                      |
| `d`                  | Delete the entry (asks for confirmation)   |
| `escape` / `q` / `h` | Close the current screen                   |
| `q`                  | Quit (from the main entry list)            |

In any dialog with buttons (e.g. confirming a delete, or saving a new
entry), `h`/`l` (and the arrow keys) move focus between them, same as
Tab/Shift+Tab.

## Adding entries

Press `a` to choose how to add an entry:

- **arXiv**: paste a URL (`https://arxiv.org/abs/...`) or a bare arXiv id.
  Title, authors, year, and the PDF are fetched automatically.
- **PDF**: choose whether it's a **local file** or a **URL** (bibi doesn't
  try to guess which from the string). A local file is *moved* into
  bibi's library (the original no longer exists at its old location
  afterward); a URL is downloaded. Either way, you're then asked to fill
  in the entry's metadata -- only the title is required.
