# Putting the site online (GitHub Pages)

This site is plain HTML and CSS, so GitHub can host it for free. Steps marked **You** need your own account and clicks; Claude can do the rest when you ask.

## Before launch

1. **You:** open `source/Asia_Le_Resume_updated.docx` in Word, check it, then **File → Save As → PDF** to `assets/Asia_Le_Resume.pdf` in this project folder.
2. **You:** read every page and tell Claude any wording changes.
3. **Claude:** run the checks (`python3 -m unittest discover -s tests`) — all must pass.

## One-time setup

1. **You:** create a free account at github.com. Pick your username carefully: the free address will be `https://<username>.github.io`.
2. **You:** click **New repository**. Name it exactly `<username>.github.io` for the shortest address (any other name works too, but the address becomes `https://<username>.github.io/<repo-name>/`). Make it **Public**. Don't add a README.
3. **You:** give Claude the repository URL. Claude merges the `build-site` branch into `main` and pushes it. (GitHub will ask you to sign in the first time — do that yourself.)
4. **You:** in the repository, go to **Settings → Pages**. Under "Build and deployment", choose **Deploy from a branch**, branch `main`, folder `/ (root)`, and save.
5. Wait a minute or two, then open `https://<username>.github.io`. Claude can check every page loads.

## Optional: your own domain (about $12/year)

1. **You:** buy a domain (for example `asiale.com`) from a registrar such as Cloudflare, Namecheap or Squarespace Domains.
2. **You:** in **Settings → Pages → Custom domain**, enter the domain and save.
3. **You:** at your registrar, add the DNS records GitHub shows you (four `A` records for the bare domain, or a `CNAME` pointing `www` to `<username>.github.io`).
4. **You:** once GitHub confirms the domain, tick **Enforce HTTPS**.

## Making changes later

Ask Claude for the change. Claude edits the files, runs the checks, commits, and pushes; the live site updates within a couple of minutes.
