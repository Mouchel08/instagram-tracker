# Instagram Analytics Tracker

Pull all your historical Instagram content, track performance metrics, and generate data-driven strategy recommendations.

---

## What this does

- Pulls **all historical posts** via the Instagram Graph API (photos, videos, reels, carousels)
- Fetches **per-post insights**: likes, comments, saves, shares, reach, impressions, plays
- Computes **engagement rates**, save rates, reach rates
- Generates a **Streamlit dashboard** with 6 views: Overview, Performance, Content Types, Timing, Hashtags, Strategy
- Exports a fully formatted **Excel tracker** with 8 sheets

---

## Prerequisites

- Python 3.10+
- A **Professional or Creator Instagram account** linked to a **Facebook Page**
- A **Meta Developer app** (free to create)

---

## Step 1 — Create your Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com) and log in with Facebook
2. Click **My Apps → Create App**
3. Choose **"Other"** → **"Business"** type
4. Name your app (e.g. "My Instagram Tracker")
5. In the app dashboard, click **Add Product → Instagram Graph API**

---

## Step 2 — Connect your Instagram account

1. In your app, go to **Instagram Graph API → Settings**
2. Add your **Instagram Professional account** under "Instagram testers" or connect it directly
3. Go to **Tools → Graph API Explorer**
4. Select your app in the top-right dropdown
5. Click **"Generate Access Token"** — log in and grant all requested permissions:
   - `instagram_basic`
   - `instagram_manage_insights`
   - `pages_show_list`
   - `pages_read_engagement`

---

## Step 3 — Get a Long-Lived Access Token (lasts 60 days)

The token from Graph API Explorer is short-lived (1 hour). Exchange it:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token
  ?grant_type=ig_exchange_token
  &client_secret=YOUR_APP_SECRET
  &access_token=YOUR_SHORT_LIVED_TOKEN"
```

This returns a token valid for **60 days**. Copy it.

> To find your App Secret: go to your app dashboard → **Settings → Basic**

---

## Step 4 — Get your Instagram User ID

```bash
curl "https://graph.instagram.com/v18.0/me?fields=id,username&access_token=YOUR_LONG_LIVED_TOKEN"
```

Note the `id` value.

---

## Step 5 — Set up environment

```bash
cd instagram-tracker
cp .env.example .env
```

Edit `.env`:
```
INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
INSTAGRAM_USER_ID=your_instagram_user_id
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
```

---

## Step 6 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 7 — Pull your data

```bash
python fetch_content.py
```

This fetches all posts and saves them to `data/`. On large accounts this may take a few minutes due to API rate limits.

To force a full refresh (skip the cache):
```bash
python fetch_content.py --refresh
```

---

## Step 8 — Launch the dashboard

```bash
streamlit run dashboard.py
```

Opens at `http://localhost:8501`

Dashboard views:
- **Overview** — KPIs, engagement trend, post frequency, content mix
- **Performance** — Top & bottom posts, metric distributions
- **Content Types** — Photo vs Video vs Reel vs Carousel comparison
- **Timing** — Best days and hours to post, frequency over time
- **Hashtags** — Top performing tags, most used tags
- **Strategy** — Data-driven recommendations
- **All Posts** — Searchable table of every post

---

## Step 9 — Export Excel tracker

```bash
python export_excel.py
```

Saves to `data/instagram_tracker_USERNAME_DATE.xlsx` with 8 sheets:
1. **Summary** — KPI overview
2. **All Posts** — Every post with all metrics
3. **By Content Type** — Aggregated by photo/video/reel/carousel
4. **Top 20 Posts** — Highest engagement
5. **Hashtag Performance** — Per-hashtag analytics
6. **Timing** — Best days and hours
7. **Strategy** — Recommendations table
8. **Monthly Breakdown** — Month-by-month trends

---

## Token Refresh

Long-lived tokens expire after 60 days. Refresh before expiry:

```python
from instagram_api import InstagramAPI
api = InstagramAPI()
result = api.refresh_long_lived_token()
print(result["access_token"])  # update your .env
```

---

## File structure

```
instagram-tracker/
├── .env                  ← your credentials (never commit this)
├── .env.example          ← template
├── requirements.txt
├── config.py             ← settings and constants
├── instagram_api.py      ← API client (auth, requests, pagination)
├── fetch_content.py      ← pulls all posts + insights from API
├── analyze.py            ← analysis engine
├── dashboard.py          ← Streamlit dashboard
├── export_excel.py       ← Excel export
├── README.md
└── data/                 ← auto-created, stores cached data
    ├── account.json
    ├── posts_raw.json
    ├── posts_processed.csv
    ├── insights_cache.json
    └── instagram_tracker_*.xlsx
```

---

## Metrics tracked per post

| Metric | Description |
|--------|-------------|
| likes | Total likes |
| comments | Total comments |
| saves | Total saves |
| shares | Total shares (reels) |
| impressions | Total times content was seen |
| reach | Unique accounts reached |
| plays | Video/reel plays |
| engagement_rate | (likes+comments+saves+shares) / followers × 100 |
| save_rate | saves / reach × 100 |
| reach_rate | reach / followers × 100 |
