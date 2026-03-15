"""
Instagram Reel scraper using Apify's apify/instagram-scraper actor.

Costs ~$0.002 per result. More reliable than Instaloader as Apify
manages proxy rotation and rate limiting internally.

Requires: pip install apify-client
Requires: APIFY_API_TOKEN env var or config.yaml apify.api_token
"""

import logging
import os
from datetime import datetime
from typing import Optional

from .instaloader_scraper import ReelMetrics, _compute_engagement_rate

logger = logging.getLogger(__name__)

# Default actor that supports directUrls for individual reels
DEFAULT_ACTOR = "apify/instagram-scraper"


def _parse_apify_item(data: dict, shortcode: str, url: str, label: str, collected_at: str) -> ReelMetrics:
    """Map apify/instagram-scraper response fields to ReelMetrics."""
    views = data.get("videoViewCount")        # unique views
    plays = data.get("videoPlayCount")        # total plays (incl. replays)
    likes = data.get("likesCount")
    comments_count = data.get("commentsCount")
    shares = data.get("sharesCount")
    saves = data.get("savesCount")
    caption = data.get("caption")
    hashtags = data.get("hashtags", [])

    # Use views if available, else fall back to plays for engagement calc
    engagement_views = views or plays
    engagement_rate = _compute_engagement_rate(engagement_views, likes, comments_count)

    return ReelMetrics(
        shortcode=shortcode,
        url=url,
        label=label,
        collected_at=collected_at,
        source="apify",
        views=views,
        likes=likes,
        comments=comments_count,
        shares=shares,
        saves=saves,
        caption=caption,
        hashtags=hashtags if isinstance(hashtags, list) else [],
        engagement_rate=engagement_rate,
    )


def scrape_reel_apify(
    shortcode: str,
    url: str,
    label: str,
    api_token: str,
    actor_id: str = DEFAULT_ACTOR,
) -> ReelMetrics:
    """Scrape a single reel via Apify."""
    try:
        from apify_client import ApifyClient  # noqa: PLC0415
    except ImportError:
        return ReelMetrics(
            shortcode=shortcode, url=url, label=label,
            collected_at=datetime.utcnow().isoformat(), source="apify",
            error="apify-client not installed. Run: pip install apify-client",
        )

    collected_at = datetime.utcnow().isoformat()
    try:
        client = ApifyClient(api_token)
        run = client.actor(actor_id).call(
            run_input={
                "directUrls": [url],
                "resultsType": "posts",
                "resultsLimit": 1,
            }
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return ReelMetrics(
                shortcode=shortcode, url=url, label=label,
                collected_at=collected_at, source="apify",
                error="No results returned from Apify",
            )
        return _parse_apify_item(items[0], shortcode, url, label, collected_at)
    except Exception as e:
        logger.error(f"Apify failed for {shortcode}: {e}")
        return ReelMetrics(
            shortcode=shortcode, url=url, label=label,
            collected_at=collected_at, source="apify", error=str(e),
        )


def scrape_reels_batch_apify(
    reels: list[dict],
    api_token: str,
    actor_id: str = DEFAULT_ACTOR,
) -> list[ReelMetrics]:
    """
    Scrape all reels in a single Apify run (most cost-efficient).
    Apify handles proxy rotation and rate limiting automatically.
    """
    try:
        from apify_client import ApifyClient  # noqa: PLC0415
    except ImportError:
        return [
            ReelMetrics(
                shortcode=r["shortcode"], url=r["url"], label=r["label"],
                collected_at=datetime.utcnow().isoformat(), source="apify",
                error="apify-client not installed. Run: pip install apify-client",
            )
            for r in reels
        ]

    collected_at = datetime.utcnow().isoformat()
    urls = [r["url"] for r in reels]
    # Build lookup by shortcode for matching results
    reel_by_shortcode = {r["shortcode"]: r for r in reels}
    reel_by_url = {r["url"]: r for r in reels}

    try:
        client = ApifyClient(api_token)
        logger.info(f"Apify batch run for {len(urls)} reels")

        run = client.actor(actor_id).call(
            run_input={
                "directUrls": urls,
                "resultsType": "posts",
                "resultsLimit": len(urls),
            }
        )

        results_by_shortcode: dict[str, ReelMetrics] = {}
        for data in client.dataset(run["defaultDatasetId"]).iterate_items():
            sc = data.get("shortCode") or data.get("shortcode", "")
            matched = reel_by_shortcode.get(sc)
            if not matched:
                # Try URL matching
                item_url = data.get("inputUrl") or data.get("url", "")
                for reel_url, reel in reel_by_url.items():
                    if reel["shortcode"] in item_url:
                        matched = reel
                        sc = reel["shortcode"]
                        break
            if not matched:
                continue
            results_by_shortcode[sc] = _parse_apify_item(
                data, matched["shortcode"], matched["url"], matched["label"], collected_at
            )

        # Return results in original order, fill missing with errors
        output = []
        for reel in reels:
            m = results_by_shortcode.get(reel["shortcode"])
            if m:
                output.append(m)
            else:
                output.append(ReelMetrics(
                    shortcode=reel["shortcode"], url=reel["url"], label=reel["label"],
                    collected_at=collected_at, source="apify",
                    error="No result returned from Apify batch",
                ))
        return output

    except Exception as e:
        logger.error(f"Apify batch failed: {e}")
        return [
            ReelMetrics(
                shortcode=r["shortcode"], url=r["url"], label=r["label"],
                collected_at=collected_at, source="apify", error=str(e),
            )
            for r in reels
        ]


def get_api_token(config: dict) -> Optional[str]:
    """Get Apify token from env var or config."""
    token = os.environ.get("APIFY_API_TOKEN") or config.get("apify", {}).get("api_token", "")
    return token if token else None
