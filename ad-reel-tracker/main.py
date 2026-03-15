"""
Instagram Ad Reel Performance Tracker

Usage:
  python main.py --collect          # Collect metrics (tries Instaloader, falls back to Apify)
  python main.py --collect --apify  # Use Apify directly (recommended)
  python main.py --report           # Generate HTML dashboard from stored data
  python main.py --all              # Collect + report in one step
  python main.py --test-scrape      # Dry run: test scraping without saving
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # Allow env var override for Apify token
    env_token = os.environ.get("APIFY_API_TOKEN")
    if env_token:
        cfg.setdefault("apify", {})["api_token"] = env_token
    return cfg


def collect(cfg: dict, force_apify: bool = False) -> list:
    from tracker.storage import init_db, save_metrics_batch

    reels = cfg["reels"]
    db_path = cfg["storage"]["db_path"]
    conn = init_db(db_path)

    apify_token = cfg.get("apify", {}).get("api_token", "")
    primary = cfg["collection"].get("primary", "instaloader")

    metrics_list = []

    # Determine which scraper to use
    use_apify = force_apify or primary == "apify" or not apify_token == ""

    if force_apify or (apify_token and (primary == "apify" or force_apify)):
        logger.info("Using Apify scraper (batch mode)")
        from tracker.apify_scraper import scrape_reels_batch_apify
        actor_id = cfg.get("apify", {}).get("actor_id", "apify/instagram-reel-scraper")
        metrics_list = scrape_reels_batch_apify(reels, api_token=apify_token, actor_id=actor_id)
    else:
        logger.info("Using Instaloader scraper")
        from tracker.instaloader_scraper import scrape_reels_batch
        ig_username = cfg["collection"].get("instagram_username")
        session_file = cfg["collection"].get("instagram_session_file")
        metrics_list = scrape_reels_batch(reels, username=ig_username, session_file=session_file)

        # Fallback: retry failed reels with Apify if token available
        failed = [cfg["reels"][i] for i, m in enumerate(metrics_list) if m.error]
        if failed and apify_token:
            logger.info(f"Instaloader failed for {len(failed)} reels, falling back to Apify")
            from tracker.apify_scraper import scrape_reels_batch_apify
            actor_id = cfg.get("apify", {}).get("actor_id", "apify/instagram-reel-scraper")
            fallback_metrics = scrape_reels_batch_apify(failed, api_token=apify_token, actor_id=actor_id)
            # Replace failed results
            fallback_by_sc = {m.shortcode: m for m in fallback_metrics}
            metrics_list = [
                fallback_by_sc.get(m.shortcode, m) if m.error else m
                for m in metrics_list
            ]

    # Save to DB
    saved_ids = save_metrics_batch(conn, metrics_list)
    conn.close()

    success = sum(1 for m in metrics_list if not m.error)
    logger.info(f"Collected {success}/{len(metrics_list)} reels successfully → saved to {db_path}")

    for m in metrics_list:
        status = f"views={m.views}, likes={m.likes}, comments={m.comments}"
        if m.error:
            status = f"ERROR: {m.error}"
        logger.info(f"  [{m.label}] {m.shortcode}: {status}")

    return metrics_list


def report(cfg: dict) -> str:
    from tracker.storage import get_all_metrics_history, get_latest_metrics, init_db
    from tracker.funnel_db import get_funnel_by_version
    from reporter.html_report import generate_html_dashboard

    db_path = cfg["storage"]["db_path"]
    output_dir = cfg["report"]["output_dir"]
    html_file = cfg["report"]["html_file"]
    output_path = str(Path(output_dir) / html_file)

    conn = init_db(db_path)
    latest = get_latest_metrics(conn)
    history = get_all_metrics_history(conn, days=30)
    conn.close()

    funnel = get_funnel_by_version(cfg)
    if funnel:
        logger.info("Funnel data loaded — version split applied")
    else:
        logger.info("Funnel data unavailable — skipping version comparison")

    path = generate_html_dashboard(
        latest_metrics=latest,
        history=history,
        output_path=output_path,
        history_days=30,
        funnel=funnel,
    )
    logger.info(f"Dashboard saved: {path}")
    return path


def test_scrape(cfg: dict) -> None:
    """Test scrape without saving to DB."""
    apify_token = cfg.get("apify", {}).get("api_token", "")
    if not apify_token:
        logger.error("No Apify token configured. Set APIFY_API_TOKEN env var.")
        sys.exit(1)

    from tracker.apify_scraper import scrape_reels_batch_apify
    actor_id = cfg.get("apify", {}).get("actor_id", "apify/instagram-reel-scraper")
    reels = cfg["reels"]

    logger.info(f"Test scraping {len(reels)} reels via Apify (no DB write)")
    metrics_list = scrape_reels_batch_apify(reels, api_token=apify_token, actor_id=actor_id)

    print("\n" + "=" * 60)
    print("TEST SCRAPE RESULTS")
    print("=" * 60)
    for m in metrics_list:
        print(f"\n{m.label} ({m.shortcode})")
        print(f"  URL:         {m.url}")
        print(f"  Source:      {m.source}")
        if m.error:
            print(f"  ERROR:       {m.error}")
        else:
            print(f"  Views:       {m.views}")
            print(f"  Likes:       {m.likes}")
            print(f"  Comments:    {m.comments}")
            print(f"  Shares:      {m.shares}")
            print(f"  Saves:       {m.saves}")
            print(f"  Engagement:  {m.engagement_rate}%")
            if m.caption:
                print(f"  Caption:     {m.caption[:80]}...")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Instagram Ad Reel Performance Tracker")
    parser.add_argument("--collect", action="store_true", help="Collect metrics")
    parser.add_argument("--report", action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--all", action="store_true", help="Collect + generate report")
    parser.add_argument("--test-scrape", action="store_true", help="Test scrape (no DB write)")
    parser.add_argument("--apify", action="store_true", help="Force Apify scraper")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()

    # Change to script directory so relative paths work
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    cfg = load_config(args.config)

    if args.test_scrape:
        test_scrape(cfg)
    elif args.all:
        collect(cfg, force_apify=args.apify)
        report(cfg)
    elif args.collect:
        collect(cfg, force_apify=args.apify)
    elif args.report:
        report(cfg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
