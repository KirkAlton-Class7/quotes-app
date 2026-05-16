# Quote of the Day App

## Local Quote Browser For Mac

Quote of the Day is a small local web app wrapped in a macOS app launcher. It opens a browser-based quote interface, serves your quote library from your Mac, and keeps favorites in the browser with `localStorage`.

The app is designed for quick use:

- open a random quote
- copy quotes
- favorite quotes
- search the full quote library
- search only favorites
- click tags to search by theme
- modify the quote JSON file when you want to add, remove, or edit quotes

> [!NOTE]
> This is a local app. It runs a small Python server on your machine at `http://localhost:8000`. Your quote file lives on disk, and favorites live in the browser profile you use with the app.

---

## Screenshot Placeholders

Add screenshots here when you want the README to show the app visually.

### Main Quote View

![Main quote view](docs/images/main-quote-view.png)

### Search Quotes

![Search quotes](docs/images/search-quotes.png)

### Favorites And Favorites Search

![Favorites search](docs/images/favorites-search.png)

### Developer Mode

![Developer mode](docs/images/developer-mode.png)

---

## Project Layout

Recommended local path:

```text
$HOME/Applications/dev/quotes
```

For example:

```text
/Users/kirk/Applications/dev/quotes
```

Main files:

| Path | Purpose |
| --- | --- |
| `quotes.app` | macOS app launcher. Double-click this to start or reopen the app. |
| `quotes_web.py` | Local Python web server and browser UI. |
| `assets/quotes/quotes.json` | Main quote library. Edit this file to add, remove, or update quotes. |
| `assets/icons/` | Icon source files used by the app bundle or future icon updates. |
| `logs/quotes_web/web_activity.log` | In-app activity log for searches, random quotes, file opens, and shutdown events. |
| `/tmp/quotes_web.log` | Launcher/server log written by the Automator app wrapper. Useful for debugging startup issues. |

> [!IMPORTANT]
> Keep the folder structure intact. The launcher expects the app to live at `$HOME/Applications/dev/quotes` unless you update the launcher path inside `quotes.app`.

---

## Mac Setup

### 1. Put The App Folder In Your Home Applications Folder

Create this folder if it does not already exist:

```text
$HOME/Applications/dev
```

Then place the full `quotes` folder here:

```text
$HOME/Applications/dev/quotes
```

The final structure should look like:

```text
$HOME/Applications/dev/quotes/quotes.app
$HOME/Applications/dev/quotes/quotes_web.py
$HOME/Applications/dev/quotes/assets/quotes/quotes.json
```

### 2. Add The App To Finder Or The Dock

You have a few easy options:

| Option | How |
| --- | --- |
| Finder sidebar | Open `$HOME/Applications/dev/quotes`, then drag `quotes.app` into Finder favorites. |
| Dock | Drag `quotes.app` to the Dock. |
| Applications folder shortcut | Create an alias for `quotes.app` and place the alias in `/Applications` or `$HOME/Applications`. |

> [!WARNING]
> Prefer an alias instead of moving `quotes.app` by itself. The app launcher is tied to the project folder and should stay with `quotes_web.py`, `assets/`, and `logs/`.

---

## Starting And Stopping

### Start The App

Double-click:

```text
quotes.app
```

The app starts the local Python server and opens:

```text
http://localhost:8000
```

If the server is already running because you closed the browser without pressing Stop Server, clicking `quotes.app` again reopens the browser instead of doing nothing.

### Stop The App

Use the red Stop Server button in the app.

Expected result:

```text
Server Stopped
You can close this window now.
```

This releases port `8000` and ends the Python server.

---

## Feature Guide

### Random Quote

Use `Random Quote` to load another quote from the library.

The main quote card shows:

- quote text
- author or speaker
- source details when available
- tags
- copy button
- favorite star

### Copy Quote

Use the copy button on the main quote card to copy the current quote to your clipboard.

### Favorites

Use the star on a quote to add or remove it from Favorites.

Open Favorites with:

```text
⭐ Favorites
```

The Favorites panel shows every starred quote. The right side of the Favorites header shows:

```text
🔎 Search Favorites (98)
```

The number is the current count of favorited quotes.

### Search Favorites

Click:

```text
🔎 Search Favorites (98)
```

This opens a search box below the Favorites header.

Behavior:

- searches only starred quotes
- updates as you type
- updates as you backspace
- clicking the control again hides the box
- clearing the search returns the full favorites list

Result count example:

```text
Found 1 quote(s) for "guilt"
```

### Search Quotes

Use `Search` to search the full quote library.

Search checks quote text, author, speaker, source, and tags. Results update as you type once the search has at least two characters.

### Tag Search

Tags are clickable.

| Where you click a tag | What happens |
| --- | --- |
| Main quote card | Opens the main Search panel for that tag. |
| Normal search result | Opens the main Search panel for that tag. |
| Favorites result | Opens Favorites Search for that tag. |

---

## Developer Mode

Open Developer Mode from the lower-right button.

| Button | Use |
| --- | --- |
| `Edit quotes.json` | Opens `assets/quotes/quotes.json` in your default editor. |
| `Show Code` | Opens the app folder in Finder. |
| `Close` | Closes the Developer Mode dialog. |

### Editing Quotes

The quote file lives here:

```text
assets/quotes/quotes.json
```

> [!WARNING]
> Quote entries must follow the exact attribution structure and JSON schema below. App features depend on consistent field names and valid formatting. Incorrect structure, missing keys, or broken JSON may break functionality or cause app failure.

**When documenting quotes, use the following structure and attribution rules:**<br>

- speaker = who says it
- author = who created it
- source = where it appears

**Each quote entry must follow this JSON schema:**

```JSON
{
  "id": "Unique numeric ID",
  "text": "Quote text",
  "speaker": "Character, speaker, or attributed voice (`null` if unknown or same as author)",
  "author": "Original author, creator, or source authority (`null` if unknown)",
  "source": "Book, speech, film, show, video, or contextual source (`null` if unknown)",
  "tags": ["tag-one", "tag-two", "tag-three", "tag-four"]
}
```

Example entry:
```JSON
{
    "id": 2,
    "text": "It's no use going back to yesterday because I was a different person then.",
    "speaker": "Alice",
    "author": "Lewis Carroll",
    "source": "Alice in Wonderland",
    "tags": ["growth", "change"]
  },
```

After editing `quotes.json`, refresh the browser or load another quote. The server reloads quotes often, so most quote-file changes show up quickly.

> [!TIP]
> Keep `id` values unique by assigning them chronologically. Favorites are tracked by quote `id`, so duplicate IDs can make favorites behave strangely.

---

## Assets And Icons

Assets live under:

```text
assets/
```

Current asset folders:

| Path | Use |
| --- | --- |
| `assets/quotes/` | Quote data files. |
| `assets/icons/` | App icon source images and `.icns` files. |

If you want to change the icon, start with `assets/icons/`. The visible app icon is controlled by the macOS app bundle, so after changing or replacing icon files you may also need to update the icon inside:

```text
quotes.app
```

Mac Finder may cache app icons. If an icon does not update right away, remove and re-add the app or alias from the Dock, then reopen Finder.

---

## Logs

There are two useful logs.

| Log | What it tells you |
| --- | --- |
| `logs/quotes_web/web_activity.log` | App activity such as random quote loads, searches, opening files, and shutdown requests. |
| `/tmp/quotes_web.log` | Startup and server output from the macOS launcher. Useful if `quotes.app` does not open correctly. |

Use the activity log when you want to see how the app is being used. Use `/tmp/quotes_web.log` when the app does not start, does not reopen the browser, or cannot bind to port `8000`.

---

## Troubleshooting

### App Click Does Not Open A Browser

Check whether the server is already running:

```text
http://localhost:8000
```

If that opens the app, the server is fine and the browser just needed to be reopened.

If it does not open, check:

```text
/tmp/quotes_web.log
```

### Port 8000 Is Already In Use

The app normally handles this by checking whether the existing server is Quote of the Day. If it is, the browser reopens.

If another app is using port `8000`, stop that app or change the port in `quotes_web.py`.

### Favorites Are Missing

Favorites are stored in the browser, not in `quotes.json`.

If favorites disappear, common causes are:

- using a different browser profile
- clearing site data
- using private browsing
- changing quote IDs in `quotes.json`

### Stop Server Was Not Clicked Before Closing The Browser

That is okay. The server can keep running in the background. Click `quotes.app` again to reopen the browser.

Use Stop Server when you want to fully end the server process.

---
