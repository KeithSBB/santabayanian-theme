# Santa Bayanian site overlay

GitHub repo: https://github.com/KeithSBB/santabayanian-theme

This repository is the **source of truth** for website chrome. Nextcloud holds the copy you write often.

| Path | Who owns it |
| --- | --- |
| `pages/about/index.html` | Chrome only. Body comes from Nextcloud `Website/about.md`. |
| `pages/contact/index.html` | You (GitHub). |
| `pages/index.html` | Homepage chrome. |
| `pages/videos/index.html` | Shell. Embeds from Nextcloud `Website/videos/`. |
| `css/theme.css`, `js/theme.js` | Theme overlay. |
| Nextcloud `Website/about.md` | About page. One markdown file, like a blog post. |
| Nextcloud `Website/blog/` | Blog posts. |
| Nextcloud `Website/videos/` | YouTube videos. |
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

Put **one** markdown file here:

`/mnt/data/ncdata/musicuser/files/Website/about.md`

(Nextcloud: `Website/about.md`.)

```markdown
---
title: About
portrait: keith.jpg
---

Your words here.

![Playing the bayan](keith.jpg)
```

Drop photos next to that file, or in `Website/about/`. They are copied to `/images/about/` so they work from any page.
