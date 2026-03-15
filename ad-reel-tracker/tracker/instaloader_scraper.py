"""
Instagram Reel scraper using Instaloader (open-source, free).

Note: This scraper works by accessing public Instagram data via Instagram's
internal GraphQL API, which may violate Instagram's ToS. Use responsibly.
GraphQL endpoints may change; update instaloader package if scraping breaks.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ReelMetrics:
    shortcode: str
    url: str
    label: str
    collected_at: str
    source: str
    views: Optional[int] = None
    plays: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    reach: Optional[int] = None
    caption: Optional[str] = None
    hashtags: list = field(default_factory=list)
    engagement_rate: Optional[float] = None
    owner_username: Optional[str] = None
    owner_name: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "shortcode": self.shortcode,
            "url": self.url,
            "label": self.label,
            "collected_at": self.collected_at,
            "source": self.source,
            "views": self.views,
            "plays": self.plays,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "saves": self.saves,
            "reach": self.reach,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "engagement_rate": self.engagement_rate,
            "owner_username": self.owner_username,
            "owner_name": self.owner_name,
            "error": self.error,
        }


def _compute_engagement_rate(views: Optional[int], likes: Optional[int], comments: Optional[int]) -> Optional[float]:
    if not views or views == 0:
        return None
    interactions = (likes or 0) + (comments or 0)
    return round(interactions / views * 100, 4)


def scrape_reel(
    shortcode: str,
    url: str,
    label: str,
    username: Optional[str] = None,
    session_file: Optional[str] = None,
    sleep_seconds: float = 3.0,
) -> ReelMetrics:
    """
    Scrape a single Instagram reel using Instaloader.

    Args:
        shortcode: The reel shortcode (e.g. 'DV0fRYczORi')
        url: Full reel URL
        label: Human-readable label
        username: Optional Instagram username for logged-in session
        session_file: Path to saved session file (from instaloader)
        sleep_seconds: Delay before request to reduce rate limiting risk

    Returns:
        ReelMetrics dataclass with collected data
    """
    try:
        import instaloader  # noqa: PLC0415
    except ImportError:
        return ReelMetrics(
            shortcode=shortcode,
            url=url,
            label=label,
            collected_at=datetime.utcnow().isoformat(),
            source="instaloader",
            error="instaloader not installed. Run: pip install instaloader",
        )

    collected_at = datetime.utcnow().isoformat()

    try:
        L = instaloader.Instaloader(
            quiet=True,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )

        if session_file and username:
            try:
                L.load_session_from_file(username, session_file)
                logger.info(f"Loaded session for {username}")
            except Exception as e:
                logger.warning(f"Could not load session: {e}. Proceeding without login.")

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        views = None
        try:
            views = post.video_view_count
        except Exception:
            pass

        likes = None
        try:
            likes = post.likes
        except Exception:
            pass

        comments_count = None
        try:
            comments_count = post.comments
        except Exception:
            pass

        caption = None
        try:
            caption = post.caption
        except Exception:
            pass

        hashtags = []
        try:
            hashtags = list(post.caption_hashtags)
        except Exception:
            pass

        engagement_rate = _compute_engagement_rate(views, likes, comments_count)

        return ReelMetrics(
            shortcode=shortcode,
            url=url,
            label=label,
            collected_at=collected_at,
            source="instaloader",
            views=views,
            likes=likes,
            comments=comments_count,
            caption=caption,
            hashtags=hashtags,
            engagement_rate=engagement_rate,
        )

    except Exception as e:
        logger.error(f"Instaloader failed for {shortcode}: {e}")
        return ReelMetrics(
            shortcode=shortcode,
            url=url,
            label=label,
            collected_at=collected_at,
            source="instaloader",
            error=str(e),
        )


def scrape_reels_batch(
    reels: list[dict],
    username: Optional[str] = None,
    session_file: Optional[str] = None,
    sleep_between: float = 5.0,
) -> list[ReelMetrics]:
    """Scrape multiple reels with a delay between each request."""
    results = []
    for i, reel in enumerate(reels):
        logger.info(f"Scraping reel {i+1}/{len(reels)}: {reel['shortcode']}")
        metrics = scrape_reel(
            shortcode=reel["shortcode"],
            url=reel["url"],
            label=reel["label"],
            username=username,
            session_file=session_file,
            sleep_seconds=sleep_between if i > 0 else 2.0,
        )
        results.append(metrics)
        if metrics.error:
            logger.warning(f"  -> Error: {metrics.error}")
        else:
            logger.info(f"  -> views={metrics.views}, likes={metrics.likes}, comments={metrics.comments}")
    return results
