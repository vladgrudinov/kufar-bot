import re
import json
import time
import logging
import requests
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    CATEGORIES,
    MIN_PRICE_BYN,
    MAX_PRICE_BYN,
    EXCLUDE_COMPANIES,
    MIN_PROFIT_BYN,
    MIN_PROFIT_PERCENT
)
from db import is_ad_seen, save_ad
from hardware_evaluator import evaluate_generic_item

logger = logging.getLogger("kufar_scanner")

class KufarScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        })
        self.search_url = "https://api.kufar.by/search-api/v2/search/rendered-paginated"

    def fetch_category_ads(self, cat_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Queries Kufar search API for the specified category."""
        params = dict(cat_cfg.get("url_params", {}))
        params["lang"] = "ru"
        try:
            resp = self.session.get(self.search_url, params=params, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("ads", [])
            else:
                logger.warning(f"Kufar API ({cat_cfg['name']}) returned HTTP {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching Kufar ads for {cat_cfg['name']}: {e}")
            return []

    def fetch_ad_details(self, ad_id: str) -> Optional[Dict[str, Any]]:
        """Fetches full ad description and metadata from item webpage."""
        item_url = f"https://www.kufar.by/item/{ad_id}"
        try:
            resp = self.session.get(item_url, timeout=10)
            if resp.status_code != 200:
                return None
            
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text)
            if match:
                data = json.loads(match.group(1))
                ad_view = data.get('props', {}).get('initialState', {}).get('adView', {})
                return ad_view.get('data', {})
        except Exception as e:
            logger.debug(f"Failed to fetch details for ad {ad_id}: {e}")
            
        return None

    def scan_for_deals(self) -> List[Dict[str, Any]]:
        """
        Scans all gaming and top tech categories (PCs, Laptops, Consoles, GPUs).
        Returns list of newly discovered profitable deals.
        """
        profitable_deals = []

        for cat_cfg in CATEGORIES:
            cat_type = cat_cfg["type"]
            cat_name = cat_cfg["name"]
            
            recent_ads = self.fetch_category_ads(cat_cfg)

            for item in recent_ads:
                ad_id = str(item.get("ad_id"))
                
                if is_ad_seen(ad_id):
                    continue

                price_byn = float(item.get("price_byn", 0)) / 100.0
                price_usd = float(item.get("price_usd", 0)) / 100.0 if item.get("price_usd") else 0.0
                is_company = bool(item.get("company_ad", False))
                
                # Check price bounds
                if price_byn < MIN_PRICE_BYN or price_byn > MAX_PRICE_BYN:
                    save_ad({
                        "ad_id": ad_id,
                        "title": item.get("subject", ""),
                        "price_byn": price_byn,
                        "price_usd": price_usd,
                        "is_company": is_company,
                        "status": "OUT_OF_PRICE_BOUNDS"
                    })
                    continue

                # Filter company stores if configured
                if EXCLUDE_COMPANIES and is_company:
                    save_ad({
                        "ad_id": ad_id,
                        "title": item.get("subject", ""),
                        "price_byn": price_byn,
                        "price_usd": price_usd,
                        "is_company": is_company,
                        "status": "SKIPPED_COMPANY"
                    })
                    continue

                time.sleep(0.2)
                details = self.fetch_ad_details(ad_id)
                
                title = details.get("subject") if details else item.get("subject", "")
                body = details.get("body") if details else ""
                account_id = details.get("accountId") if details else item.get("account_id", "")
                ad_link = details.get("adViewLink") if details else item.get("ad_link", f"https://www.kufar.by/item/{ad_id}")
                
                ad_params = {}
                for p in item.get("ad_parameters", []):
                    ad_params[p.get("p")] = p.get("vl")

                # Evaluate item with appropriate specialized evaluator
                eval_result = evaluate_generic_item(
                    category_type=cat_type,
                    title=title,
                    body=body,
                    params=ad_params,
                    price=price_byn
                )

                if not eval_result:
                    # Item could not be recognized as high-value target
                    save_ad({
                        "ad_id": ad_id,
                        "title": title,
                        "price_byn": price_byn,
                        "price_usd": price_usd,
                        "is_company": is_company,
                        "status": "NOT_TARGET_MODEL"
                    })
                    continue

                profit_byn = eval_result["profit_byn"]
                profit_percent = eval_result["profit_percent"]
                
                is_profitable = (profit_byn >= MIN_PROFIT_BYN and profit_percent >= MIN_PROFIT_PERCENT)
                ad_status = "PROFITABLE" if is_profitable else "REGULAR"

                deal_record = {
                    "ad_id": ad_id,
                    "title": title,
                    "price_byn": price_byn,
                    "price_usd": price_usd,
                    "market_value": eval_result["market_value"],
                    "profit_byn": profit_byn,
                    "profit_percent": profit_percent,
                    "recommended_offer": eval_result["recommended_offer"],
                    "cpu": eval_result.get("cpu", "-"),
                    "gpu": eval_result.get("gpu", "-"),
                    "ram": eval_result.get("ram", "-"),
                    "storage": eval_result.get("storage", "-"),
                    "warnings": eval_result.get("warnings", "Нет"),
                    "is_company": is_company,
                    "ad_link": ad_link,
                    "account_id": account_id,
                    "status": ad_status
                }

                save_ad(deal_record)

                if is_profitable:
                    category_badge = eval_result.get("category_title", cat_name)
                    logger.info(f"🔥 [{category_badge}] {title} | Price: {price_byn} BYN | Est: {eval_result['market_value']} BYN | Profit: +{profit_byn} BYN (+{profit_percent}%)")
                    deal_record["category_title"] = category_badge
                    deal_record["body"] = body
                    profitable_deals.append(deal_record)

        return profitable_deals
