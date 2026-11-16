import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                ad_id TEXT PRIMARY KEY,
                title TEXT,
                price_byn REAL,
                price_usd REAL,
                market_value REAL,
                profit_byn REAL,
                profit_percent REAL,
                recommended_offer REAL,
                cpu TEXT,
                gpu TEXT,
                ram TEXT,
                storage TEXT,
                warnings TEXT,
                is_company INTEGER DEFAULT 0,
                ad_link TEXT,
                account_id TEXT,
                status TEXT DEFAULT 'NEW',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_id TEXT,
                offer_price REAL,
                message_text TEXT,
                status TEXT DEFAULT 'PENDING',
                reply_text TEXT,
                sent_at TIMESTAMP,
                replied_at TIMESTAMP,
                FOREIGN KEY(ad_id) REFERENCES ads(ad_id)
            )
        """)
        conn.commit()

def is_ad_seen(ad_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM ads WHERE ad_id = ?", (str(ad_id),))
        return cursor.fetchone() is not None

def save_ad(data: Dict[str, Any]):
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO ads (
                ad_id, title, price_byn, price_usd, market_value,
                profit_byn, profit_percent, recommended_offer,
                cpu, gpu, ram, storage, warnings, is_company,
                ad_link, account_id, status, created_at, updated_at
            ) VALUES (
                :ad_id, :title, :price_byn, :price_usd, :market_value,
                :profit_byn, :profit_percent, :recommended_offer,
                :cpu, :gpu, :ram, :storage, :warnings, :is_company,
                :ad_link, :account_id, :status, :created_at, :updated_at
            )
        """, {
            "ad_id": str(data.get("ad_id")),
            "title": data.get("title", ""),
            "price_byn": float(data.get("price_byn", 0.0)),
            "price_usd": float(data.get("price_usd", 0.0)),
            "market_value": float(data.get("market_value", 0.0)),
            "profit_byn": float(data.get("profit_byn", 0.0)),
            "profit_percent": float(data.get("profit_percent", 0.0)),
            "recommended_offer": float(data.get("recommended_offer", 0.0)),
            "cpu": data.get("cpu", ""),
            "gpu": data.get("gpu", ""),
            "ram": data.get("ram", ""),
            "storage": data.get("storage", ""),
            "warnings": data.get("warnings", ""),
            "is_company": 1 if data.get("is_company") else 0,
            "ad_link": data.get("ad_link", ""),
            "account_id": str(data.get("account_id", "")),
            "status": data.get("status", "NEW"),
            "created_at": now,
            "updated_at": now
        })
        conn.commit()

def update_ad_status(ad_id: str, status: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ad_id = ?",
            (status, str(ad_id))
        )
        conn.commit()

def get_ad(ad_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ads WHERE ad_id = ?", (str(ad_id),))
        row = cursor.fetchone()
        return dict(row) if row else None

def record_offer(ad_id: str, offer_price: float, message_text: str, status: str = "SENT"):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offers (ad_id, offer_price, message_text, status, sent_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (str(ad_id), offer_price, message_text, status))
        conn.commit()

init_db()
