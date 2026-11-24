# CargoFeed

Live shipping-container construction aggregator — serves https://containers.snarkyalma.com/

- `fetch_feeds.py` — stdlib RSS/Atom fetcher + static renderer. Runs locally and in GitHub Actions.
- `feeds.txt` — feed registry (add a line, push, done).
- `template.html` — page template; script renders `index.html` from it at each refresh.
- `.github/workflows/refresh.yml` — cron every 6h (02:17 / 08:17 / 14:17 / 20:17 UTC), commits only when content changes.
- Reddit blocks many datacenter IPs; the runner may see 429s on some sources. The merge logic keeps last-fetched items until they age out (21 days), so the site degrades gracefully instead of going empty.

Local test: `python3 fetch_feeds.py` then open `index.html`.
