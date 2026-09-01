# Santa Bayanian site overlay

GitHub repo: https://github.com/KeithSBB/santabayanian-theme

This repository is the **source of truth** for website chrome and copy you edit by hand.

| Path | Who owns it |
| --- | --- |
| `pages/about/index.html` | You. Edit here, commit, deploy. |
| `pages/contact/index.html` | You. |
| `pages/videos/index.html` | Shell only. Embeds come from Nextcloud `Website/videos/`. |
| `css/theme.css`, `js/theme.js` | Theme overlay. |
| `scripts/` | Builders. Do not put album HTML here. |
| Nextcloud `Website/blog/` | Blog posts. |
| Nextcloud `Website/videos/` | YouTube videos (markdown with a URL). |
| Nextcloud `Website/theme/` | Mascot stills and loops. |
| `/albums/` on the server | release-manager. Do not hand-edit. |

## Deploy

```bash
cd ~/santabayanian-theme
git pull
sudo bash deploy-theme.sh . /mnt/data/santabayanian
sudo -u nginx python3 /mnt/data/santabayanian/scripts/build-theme.py
sudo -u nginx python3 /mnt/data/santabayanian/scripts/site_content.py
```

## Edit the About page

1. Edit [`pages/about/index.html`](pages/about/index.html) on GitHub (or locally, then `git add`, `git commit`, `git push`).
2. On the server: `cd ~/santabayanian-theme && git pull && sudo bash deploy-theme.sh . /mnt/data/santabayanian`

Do not rewrite About only on the live server — the next deploy from GitHub will overwrite it.
