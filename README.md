# action-crosspost

[![GitHub Marketplace](https://img.shields.io/badge/marketplace-action--crosspost-blue?logo=github)](https://github.com/marketplace/actions/crosspost-action)
[![GitHub release](https://img.shields.io/github/v/release/tgagor/action-crosspost?logo=github)](https://github.com/tgagor/action-crosspost/releases)
[![CI](https://github.com/tgagor/action-crosspost/actions/workflows/build.yml/badge.svg)](https://github.com/tgagor/action-crosspost/actions/workflows/build.yml)
[![License](https://img.shields.io/github/license/tgagor/action-crosspost)](https://github.com/tgagor/action-crosspost/blob/main/LICENSE)
[![Issues](https://img.shields.io/github/issues/tgagor/action-crosspost)](https://github.com/tgagor/action-crosspost/issues)

**Crosspost your latest content to social media directly from GitHub Actions.**
This action fetches URLs from a `sitemap.xml` or RSS/Atom feed, filters them by age, and posts them to your configured social networks using [humanwhocodes/crosspost](https://github.com/humanwhocodes/crosspost).

---

## ✨ Features

* Supports both **sitemaps** and **RSS/Atom feeds**.
* Crosspost to **multiple networks in one go** (Twitter/X, Mastodon, Bluesky, LinkedIn, etc.).
* Filter by **age** (`since` + `since-unit`) and by **URL include/exclude patterns**.
* Run in **dry-run mode** to safely preview what would be posted.
* Flexible failure strategies: stop on error or continue with other posts.

---

## ⚠️ Important First Step

Start with `dry-run: true` to ensure you don’t flood your social networks with hundreds of posts on the first run.
Once you confirm the filtering works as expected, remove `dry-run` or set it to `false`.

---

## 📆 Recommended Scheduling

Run this action **once a day** at a time when your audience is most likely online — for example:

* **09:00** (morning commute)
* **17:00** (after work)

Example scheduler trigger:

```yaml
on:
  schedule:
    - cron: '0 9 * * *'   # every day at 09:00 UTC
```

---

## 📌 Inputs

Here are the most important inputs (see [`action.yml`](./action.yml) for the full list):

| Input              | Required | Description                                                                                                                            |
| ------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `feed-url`         | ✅ Yes   | URL of the sitemap (`.xml`) or RSS/Atom feed to fetch posts from.                                                                      |
| `since`            | No       | How far back to fetch posts. Use with `since-unit`. Default: `1`.                                                                      |
| `since-unit`       | No       | Unit for `since`: `minutes`, `hours`, `days`, `weeks`, `months`, `years`. Both singular and plural forms are accepted. Default: `day`. |
| `limit`            | No       | Maximum number of posts to publish. **Do not flood!**                                                                                  |
| `failure-strategy` | No       | Either `fail` (default) or `continue` when a single post fails.                                                                        |
| `dry-run`          | No       | If `true`, shows what would be posted without actually posting.                                                                        |
| `exclude-urls`     | No       | Newline-separated list of URL patterns to exclude (supports wildcards like `*`).                                                       |
| `filter-urls`      | No       | Newline-separated list of URL substrings that must be present to include the post.                                                     |

### Social network credentials

The action accepts credentials as inputs and maps them to environment variables expected by **crosspost**. Examples:

- **Mastodon**
  - `mastodon-access-token` → `MASTODON_ACCESS_TOKEN`
  - `mastodon-host` → `MASTODON_URL`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#mastodon).

- **Twitter/X**
  - `twitter-access-token-key`
  - `twitter-access-token-secret`
  - `twitter-api-consumer-key`
  - `twitter-api-consumer-secret`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#twitter).

- **Bluesky**
  - `bluesky-host`
  - `bluesky-identifier`
  - `bluesky-password`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#mastodon).

- **LinkedIn**
  - `linkedin-access-token`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#linkedin).

- **Discord Bot**
  - `discord-bot-token`
  - `discord-channel-id`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#discord-bot).

- **Discord Webhook**
  - `discord-webhook-url`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#discord-webhook).

- **Dev.to**
  - `devto-api-key`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#devto).

- **Telegram**
  - `telegram-bot-token`
  - `telegram-chat-id`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#telegram).

- **Slack**
  - `slack-token`
  - `slack-channel`
  - [more on configuration details](https://github.com/humanwhocodes/crosspost?tab=readme-ov-file#slack).


...and so on for other networks supported by [crosspost](https://github.com/humanwhocodes/crosspost#options).

Use **GitHub secrets** for these values.

---

## 📝 Usage Examples

### Example 1 — Post from a sitemap

```yaml
jobs:
  crosspost:
    runs-on: ubuntu-latest
    steps:
      - name: Run action-crosspost on a test sitemap
        uses: tgagor/action-crosspost@v1
        with:
          dry-run: true
          feed-url: https://example.com/sitemap.xml
          since: '1'
          since-unit: day
          mastodon-access-token: ${{ secrets.MASTODON_ACCESS_TOKEN }}
          mastodon-host: mastodon.social
          exclude-urls: |
            https://example.com/
            https://example.com/author*
            https://example.com/tags/*
            https://example.com/categories/*
            https://example.com/posts/*
            https://example.com/about/
          filter-urls: |
            /blog/
```

---

### Example 2 — Post from an RSS feed

```yaml
jobs:
  crosspost:
    runs-on: ubuntu-latest
    steps:
      - name: Run action-crosspost on a test RSS feed
        uses: tgagor/action-crosspost@v1
        with:
          dry-run: true
          feed-url: https://example.com/index.xml
          since: '1'
          since-unit: week
          twitter-api-key: ${{ secrets.TWITTER_API_KEY }}
          twitter-api-secret: ${{ secrets.TWITTER_API_SECRETS }}$
          exclude-urls: |
            https://example.com/
            https://example.com/about/
          filter-urls: |
            book
```

---

## 💡 Notes & Best Practices

* **Sitemaps** may mark pages as updated, so posts could appear again even if they were published earlier.

  * If you want to avoid reposting updated content, prefer using **RSS/Atom feeds**, which rely on the original publication date.
* Always begin with `dry-run: true` to validate your filtering before posting.
* Use `exclude-urls` and `filter-urls` to fine-tune which links should actually be posted.
