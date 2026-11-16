import re
from typing import Dict, Any, Tuple, Optional

# --- Used Hardware Market Values (BYN) ---
GPU_VALUES = {
    # RTX 50 series
    "rtx 5090": 8500, "rtx 5080": 4800, "rtx 5070 ti": 3300, "rtx 5070": 2600,
    # RTX 40 series
    "rtx 4090": 6000, "rtx 4080 super": 3500, "rtx 4080": 3200,
    "rtx 4070 ti super": 2700, "rtx 4070 ti": 2300, "rtx 4070 super": 2000, "rtx 4070": 1750,
    "rtx 4060 ti": 1350, "rtx 4060": 1050,
    # RTX 30 series
    "rtx 3090 ti": 2600, "rtx 3090": 2100, "rtx 3080 ti": 1700, "rtx 3080": 1350,
    "rtx 3070 ti": 1100, "rtx 3070": 950, "rtx 3060 ti": 850, "rtx 3060": 750,
    "rtx 3050": 550,
    # RTX 20 series
    "rtx 2080 ti": 950, "rtx 2080 super": 800, "rtx 2080": 700,
    "rtx 2070 super": 650, "rtx 2070": 580, "rtx 2060 super": 550, "rtx 2060": 450,
    # GTX series
    "gtx 1660 ti": 400, "gtx 1660 super": 380, "gtx 1660": 330,
    "gtx 1650 super": 290, "gtx 1650": 240, "gtx 1080 ti": 550,
    "gtx 1080": 420, "gtx 1070 ti": 380, "gtx 1070": 330,
    "gtx 1060 6gb": 260, "gtx 1060": 220, "gtx 1050 ti": 170, "gtx 970": 170,
    # AMD Radeon RX 7000 series
    "rx 7900 xtx": 3400, "rx 7900 xt": 2600, "rx 7800 xt": 1750, "rx 7700 xt": 1400, "rx 7600 xt": 1100, "rx 7600": 850,
    # AMD Radeon RX 6000 series
    "rx 6950 xt": 1800, "rx 6900 xt": 1600, "rx 6800 xt": 1350, "rx 6800": 1150,
    "rx 6750 xt": 950, "rx 6700 xt": 850, "rx 6700": 750,
    "rx 6650 xt": 700, "rx 6600 xt": 640, "rx 6600": 550, "rx 6500 xt": 350,
    # AMD Radeon RX 5000 / 500 series
    "rx 5700 xt": 500, "rx 5700": 430, "rx 5600 xt": 380, "rx 5500 xt": 300,
    "rx 590": 240, "rx 580": 190, "rx 570": 160, "rx 480": 150, "rx 470": 130
}

CPU_VALUES = {
    # AMD AM5
    "7800x3d": 1250, "7950x": 1400, "7900x": 1050, "7700x": 800, "7700": 700, "7600x": 580, "7600": 520, "7500f": 450,
    # AMD AM4 Ryzen 5000
    "5800x3d": 850, "5700x3d": 650, "5950x": 1100, "5900x": 800, "5800x": 520, "5700x": 450, "5700g": 430,
    "5600x": 350, "5600g": 320, "5600": 310, "5500": 240, "4500": 180, "4100": 140,
    # AMD AM4 Ryzen 3000 / 2000 / 1000
    "3900x": 550, "3800x": 380, "3700x": 330, "3600x": 220, "3600": 190, "3500": 160, "3300x": 160, "3100": 140,
    "2700x": 220, "2700": 190, "2600x": 160, "2600": 140, "1600": 110, "1200": 70,
    # Intel LGA1700 (12th-14th gen)
    "14900k": 1800, "14700k": 1300, "14600k": 950, "14400f": 580, "14400": 630,
    "13900k": 1500, "13700k": 1150, "13600k": 850, "13500": 680, "13400f": 520, "13400": 560, "13100f": 260,
    "12900k": 1100, "12700k": 850, "12700f": 750, "12700": 770, "12600k": 620, "12400f": 360, "12400": 400, "12100f": 230, "12100": 270,
    # Intel LGA1200 (10th-11th gen)
    "11900k": 750, "11700k": 580, "11700": 500, "11600k": 450, "11400f": 280, "11400": 310,
    "10900k": 700, "10700k": 520, "10700": 460, "10600k": 380, "10400f": 240, "10400": 270, "10105f": 170, "10100f": 150,
    # Intel LGA1151v2 (8th-9th gen)
    "9900k": 600, "9700k": 450, "9700": 400, "9600k": 300, "9400f": 190, "9400": 220, "9100f": 120,
    "8700k": 400, "8700": 350, "8600k": 260, "8400": 170, "8100": 110,
    # Intel LGA1151v1 (6th-7th gen)
    "7700k": 280, "7700": 240, "6700k": 230, "6700": 200, "6500": 130, "6400": 110,
    # Xeon
    "2670 v3": 50, "2680 v3": 60, "2666 v3": 55, "2678 v3": 60, "2690 v3": 80, "2670 v4": 70, "2680 v4": 80,
    "2650 v3": 40, "2640 v3": 35, "2620 v3": 30, "2630 v3": 30, "xeon": 50
}

# --- Gaming Consoles Market Values (BYN) ---
CONSOLES_VALUES = {
    "ps5 pro": 3300, "playstation 5 pro": 3300,
    "ps5 slim": 1750, "playstation 5 slim": 1750,
    "ps5": 1600, "playstation 5": 1600,
    "ps4 pro": 680, "playstation 4 pro": 680,
    "ps4 slim": 520, "playstation 4 slim": 520,
    "ps4": 450, "playstation 4": 450,
    "xbox series x": 1550, "series x": 1550,
    "xbox series s": 750, "series s": 750,
    "steam deck oled": 1950, "steam deck": 1250,
    "rog ally x": 2600, "rog ally": 1700, "legion go": 1950,
    "switch oled": 850, "nintendo switch oled": 850,
    "switch v2": 580, "nintendo switch v2": 580,
    "switch lite": 380, "nintendo switch lite": 380,
    "switch": 520, "nintendo switch": 520
}

# --- Apple MacBook Market Values (BYN) ---
MACBOOK_VALUES = {
    "macbook air m3": 3200, "macbook air m2": 2600, "macbook air m1": 1850,
    "macbook pro 16 m3": 6500, "macbook pro 14 m3": 4900,
    "macbook pro 16 m2": 5200, "macbook pro 14 m2": 4100,
    "macbook pro 16 m1": 3900, "macbook pro 14 m1": 3200,
    "macbook pro m2": 3100, "macbook pro m1": 2500
}

# --- Apple iPhone Market Values (BYN) ---
IPHONE_VALUES = {
    "16 pro max": 4400, "16 pro": 3800, "16 plus": 2900, "16": 2700,
    "15 pro max": 3400, "15 pro": 2900, "15 plus": 2300, "15": 2100,
    "14 pro max": 2600, "14 pro": 2200, "14 plus": 1750, "14": 1650,
    "13 pro max": 2000, "13 pro": 1700, "13 mini": 1150, "13": 1350,
    "12 pro max": 1400, "12 pro": 1200, "12 mini": 750,  "12": 950,
    "11 pro max": 1050, "11 pro": 900,  "11": 700
}

# --- Apple iPad Market Values (BYN) ---
IPAD_VALUES = {
    "ipad pro 13 m4": 4200, "ipad pro 11 m4": 3400,
    "ipad pro 12.9 m2": 3200, "ipad pro 11 m2": 2600,
    "ipad pro 12.9 m1": 2500, "ipad pro 11 m1": 2100,
    "ipad air m2": 2200, "ipad air m1": 1600, "ipad air 5": 1600, "ipad air 4": 1250,
    "ipad 10": 1150, "ipad 9": 800, "ipad mini 6": 1350
}

def extract_cpu(text: str) -> Tuple[Optional[str], float]:
    lower = text.lower()
    sorted_cpus = sorted(CPU_VALUES.keys(), key=lambda x: len(x), reverse=True)
    for model in sorted_cpus:
        pattern = r'(?:\b|i[3579]-?|r[3579]-?|ryzen\s*[3579]\s*|core\s*)' + re.escape(model) + r'(?:\b|[fka-z]*)'
        if re.search(pattern, lower):
            return f"CPU: {model.upper()}", CPU_VALUES[model]

    if "xeon" in lower or "e5-" in lower or "e5 " in lower:
        return "CPU: Intel Xeon", 50.0
    if "i7" in lower:
        return "CPU: Intel Core i7", 250.0
    if "i5" in lower:
        return "CPU: Intel Core i5", 180.0
    if "i3" in lower:
        return "CPU: Intel Core i3", 120.0
    if "ryzen 7" in lower or "r7" in lower:
        return "CPU: AMD Ryzen 7", 300.0
    if "ryzen 5" in lower or "r5" in lower:
        return "CPU: AMD Ryzen 5", 200.0
    if "ryzen 3" in lower or "r3" in lower:
        return "CPU: AMD Ryzen 3", 120.0
    return None, 0.0

def extract_gpu(text: str) -> Tuple[Optional[str], float]:
    lower = text.lower()
    sorted_gpus = sorted(GPU_VALUES.keys(), key=lambda x: len(x), reverse=True)
    for model in sorted_gpus:
        parts = model.split()
        if len(parts) == 2:
            prefix, code = parts
            pattern = rf'\b(?:{prefix}[ -]?)?{re.escape(code)}\b'
        else:
            pattern = rf'\b{re.escape(model)}\b'
            
        if re.search(pattern, lower):
            return f"GPU: {model.upper()}", GPU_VALUES[model]
            
    if "встроенная" in lower or "интегрированная" in lower or "vega" in lower or "uhd" in lower:
        return "GPU: Встроенная (iGPU)", 0.0
    return None, 0.0

def extract_ram(text: str) -> Tuple[str, float]:
    lower = text.lower()
    ddr_type = "DDR4"
    if "ddr5" in lower:
        ddr_type = "DDR5"
    elif "ddr3" in lower:
        ddr_type = "DDR3"
        
    size = 16
    m = re.search(r'\b(64|32|16|8|4)\s*(?:gb|гб|g|г)\b', lower)
    if m:
        size = int(m.group(1))
        
    val_map = {
        "DDR5": {64: 600, 32: 320, 16: 180, 8: 90},
        "DDR4": {64: 380, 32: 200, 16: 100, 8: 55, 4: 30},
        "DDR3": {32: 120, 16: 65, 8: 35, 4: 20}
    }
    price = val_map.get(ddr_type, val_map["DDR4"]).get(size, 100.0)
    return f"{size}GB {ddr_type}", float(price)

def extract_storage(text: str) -> Tuple[str, float]:
    lower = text.lower()
    val = 0.0
    desc = []
    if re.search(r'\b(2\s*(?:tb|тб)|2000\s*(?:gb|гб))\b', lower):
        desc.append("2TB SSD")
        val += 300.0
    elif re.search(r'\b(1\s*(?:tb|тб)|1000\s*(?:gb|гб))\b', lower):
        desc.append("1TB SSD")
        val += 180.0
    elif re.search(r'\b(512|500)\s*(?:gb|гб)\b', lower):
        desc.append("500GB SSD")
        val += 100.0
    elif re.search(r'\b(256|250|240)\s*(?:gb|гб)\b', lower):
        desc.append("256GB SSD")
        val += 60.0
    else:
        desc.append("SSD ~500GB")
        val += 90.0
    return " ".join(desc), val

def evaluate_platform_allowance(cpu_name: Optional[str], gpu_name: Optional[str], text: str) -> float:
    lower = text.lower()
    if cpu_name and "xeon" in cpu_name.lower():
        return 160.0
    if (gpu_name and any(x in gpu_name.lower() for x in ["4090", "4080", "4070 ti", "7900 xtx", "7900 xt"])) or \
       (cpu_name and any(x in cpu_name.lower() for x in ["7800x3d", "14700", "14900", "13900", "13700"])):
        return 650.0
    if (gpu_name and any(x in gpu_name.lower() for x in ["4060", "4070", "3060", "3070", "6700", "6600"])) or \
       (cpu_name and any(x in cpu_name.lower() for x in ["5600", "7500f", "12400", "13400", "10400", "11400", "3600"])):
        return 400.0
    return 260.0

def evaluate_gaming_console(title: str, body: str, price_byn: float) -> Optional[Dict[str, Any]]:
    full = f"{title} {body}".lower()
    sorted_consoles = sorted(CONSOLES_VALUES.keys(), key=lambda x: len(x), reverse=True)
    detected_model = None
    market_val = 0.0
    
    for c_model in sorted_consoles:
        pattern = rf'\b{re.escape(c_model)}\b'
        if re.search(pattern, full):
            detected_model = c_model.upper()
            market_val = CONSOLES_VALUES[c_model]
            break
            
    if not detected_model:
        return None
        
    if any(w in full for w in ["2 геймпада", "2 джойстика", "два геймпада", "второй геймпад"]):
        market_val += 150.0
        
    profit_byn = market_val - price_byn
    profit_percent = (profit_byn / price_byn * 100.0) if price_byn > 0 else 0.0
    offer_price = round(price_byn * 0.84 / 10.0) * 10.0
    
    return {
        "item_type": "CONSOLE",
        "category_title": "🎮 Игровая Консоль",
        "model": detected_model,
        "cpu": "-", "gpu": "-", "ram": "-", "storage": "-",
        "market_value": round(market_val, 2),
        "price_byn": round(price_byn, 2),
        "profit_byn": round(profit_byn, 2),
        "profit_percent": round(profit_percent, 1),
        "recommended_offer": round(offer_price, 2),
        "warnings": "Проверить пломбы, бан в PSN/Live и дрифт стиков"
    }

def evaluate_laptop(title: str, body: str, price_byn: float) -> Optional[Dict[str, Any]]:
    full = f"{title} {body}".lower()
    for m_model, val in sorted(MACBOOK_VALUES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf'\b{re.escape(m_model)}\b', full):
            profit_byn = val - price_byn
            pct = (profit_byn / price_byn * 100.0) if price_byn > 0 else 0.0
            return {
                "item_type": "LAPTOP",
                "category_title": "💻 Apple MacBook",
                "model": m_model.upper(),
                "cpu": "Apple Silicon", "gpu": "Apple GPU", "ram": "-", "storage": "-",
                "market_value": round(val, 2),
                "price_byn": round(price_byn, 2),
                "profit_byn": round(profit_byn, 2),
                "profit_percent": round(pct, 1),
                "recommended_offer": round(price_byn * 0.85 / 10.0) * 10.0,
                "warnings": "Проверить аккумулятор (циклы) и отсутствие iCloud/MDM"
            }
            
    gpu_name, gpu_val = extract_gpu(full)
    cpu_name, cpu_val = extract_cpu(full)
    if not gpu_val or gpu_val < 300:
        return None
        
    ram_desc, _ = extract_ram(full)
    storage_desc, _ = extract_storage(full)
    laptop_market_val = gpu_val * 1.55 + (cpu_val * 0.7 if cpu_val else 200) + 300
    profit_byn = laptop_market_val - price_byn
    pct = (profit_byn / price_byn * 100.0) if price_byn > 0 else 0.0
    
    return {
        "item_type": "LAPTOP",
        "category_title": "💻 Игровой Ноутбук",
        "model": f"{gpu_name} + {cpu_name or 'CPU'}",
        "cpu": cpu_name or "Не определен",
        "gpu": gpu_name or "Не определена",
        "ram": ram_desc, "storage": storage_desc,
        "market_value": round(laptop_market_val, 2),
        "price_byn": round(price_byn, 2),
        "profit_byn": round(profit_byn, 2),
        "profit_percent": round(pct, 1),
        "recommended_offer": round(price_byn * 0.84 / 20.0) * 20.0,
        "warnings": "Обязательно стресс-тест температур (Furmark/AIDA64)"
    }

def evaluate_standalone_gpu(title: str, body: str, price_byn: float) -> Optional[Dict[str, Any]]:
    full = f"{title} {body}".lower()
    gpu_name, gpu_val = extract_gpu(full)
    if not gpu_name or gpu_val < 350:
        return None
        
    profit_byn = gpu_val - price_byn
    pct = (profit_byn / price_byn * 100.0) if price_byn > 0 else 0.0
    warnings = "Риск майнинга" if ("rx 580" in gpu_name.lower() or "rx 570" in gpu_name.lower()) else "Тест Furmark на артефакты"
    
    return {
        "item_type": "GPU",
        "category_title": "⚡ Топовая Видеокарта",
        "model": gpu_name,
        "cpu": "-", "gpu": gpu_name, "ram": "-", "storage": "-",
        "market_value": round(gpu_val, 2),
        "price_byn": round(price_byn, 2),
        "profit_byn": round(profit_byn, 2),
        "profit_percent": round(pct, 1),
        "recommended_offer": round(price_byn * 0.84 / 10.0) * 10.0,
        "warnings": warnings
    }

def evaluate_iphone(title: str, body: str, price_byn: float) -> Optional[Dict[str, Any]]:
    """Evaluates Apple iPhone models (11 to 16 Pro Max)."""
    full = f"{title} {body}".lower()
    if "iphone" not in full and "айфон" not in full:
        return None
        
    for model_code, val in sorted(IPHONE_VALUES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf'(?:iphone|айфон)\s*{re.escape(model_code)}\b', full):
            profit = val - price_byn
            pct = (profit / price_byn * 100.0) if price_byn > 0 else 0.0
            return {
                "item_type": "IPHONE",
                "category_title": "📱 Смартфон Apple iPhone",
                "model": f"iPhone {model_code.upper()}",
                "cpu": "Apple A-Bionic", "gpu": "Apple GPU", "ram": "-", "storage": "-",
                "market_value": round(val, 2),
                "price_byn": round(price_byn, 2),
                "profit_byn": round(profit, 2),
                "profit_percent": round(pct, 1),
                "recommended_offer": round(price_byn * 0.85 / 10.0) * 10.0,
                "warnings": "Проверить TrueTone, FaceID, АКБ (емкость), отсутствие iCloud/MDM"
            }
    return None

def evaluate_ipad(title: str, body: str, price_byn: float) -> Optional[Dict[str, Any]]:
    """Evaluates Apple iPad models."""
    full = f"{title} {body}".lower()
    if "ipad" not in full and "айпад" not in full:
        return None
        
    for model_code, val in sorted(IPAD_VALUES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf'\b{re.escape(model_code)}\b', full):
            profit = val - price_byn
            pct = (profit / price_byn * 100.0) if price_byn > 0 else 0.0
            return {
                "item_type": "IPAD",
                "category_title": "📟 Планшет Apple iPad",
                "model": model_code.upper(),
                "cpu": "Apple Silicon", "gpu": "Apple GPU", "ram": "-", "storage": "-",
                "market_value": round(val, 2),
                "price_byn": round(price_byn, 2),
                "profit_byn": round(profit, 2),
                "profit_percent": round(pct, 1),
                "recommended_offer": round(price_byn * 0.85 / 10.0) * 10.0,
                "warnings": "Проверить дисплей (оригинал), Touch/FaceID, отсутствие iCloud"
            }
    return None

def evaluate_monitor(title: str, body: str, price_byn: float) -> Optional[Dict[str, Any]]:
    """Evaluates high-refresh gaming monitors (144Hz–240Hz+)."""
    full = f"{title} {body}".lower()
    m_hz = re.search(r'\b(144|165|180|240|280|360)\s*(?:hz|гц)\b', full)
    if not m_hz:
        return None
        
    hz = int(m_hz.group(1))
    market_val = 360.0
    if hz >= 240:
        market_val = 700.0
    elif hz >= 165:
        market_val = 450.0
    elif "2k" in full or "1440p" in full or "27" in full:
        market_val = 550.0
        
    profit = market_val - price_byn
    pct = (profit / price_byn * 100.0) if price_byn > 0 else 0.0
    return {
        "item_type": "MONITOR",
        "category_title": "🖥️ Игровой Монитор",
        "model": f"Игровой Монитор {hz}Hz",
        "cpu": "-", "gpu": "-", "ram": "-", "storage": "-",
        "market_value": round(market_val, 2),
        "price_byn": round(price_byn, 2),
        "profit_byn": round(profit, 2),
        "profit_percent": round(pct, 1),
        "recommended_offer": round(price_byn * 0.85 / 10.0) * 10.0,
        "warnings": "Проверить на битые пиксели и засветы матрицы"
    }

def evaluate_pc(ad_title: str, ad_body: str, ad_params: Dict[str, Any], price_byn: float) -> Dict[str, Any]:
    full_text = f"{ad_title} {ad_body} " + " ".join(str(v) for v in ad_params.values())
    cpu_name, cpu_val = extract_cpu(full_text)
    gpu_name, gpu_val = extract_gpu(full_text)
    ram_desc, ram_val = extract_ram(full_text)
    storage_desc, storage_val = extract_storage(full_text)
    platform_val = evaluate_platform_allowance(cpu_name, gpu_name, full_text)
    
    market_value = cpu_val + gpu_val + ram_val + storage_val + platform_val
    warnings = []
    if not cpu_name:
        warnings.append("CPU не распознан")
    if not gpu_name:
        warnings.append("GPU не определена")
    elif "rx 580" in gpu_name.lower() or "rx 570" in gpu_name.lower():
        warnings.append("Риск майнинг-карты RX 580/570")
    if cpu_name and "xeon" in cpu_name.lower():
        warnings.append("Серверный Xeon / китай-плата")
        
    profit_byn = market_value - price_byn
    profit_percent = (profit_byn / price_byn * 100.0) if price_byn > 0 else 0.0
    
    raw_offer = price_byn * 0.82
    recommended_offer = round(raw_offer / 50.0) * 50.0 if raw_offer > 1000 else round(raw_offer / 20.0) * 20.0
    
    return {
        "item_type": "PC",
        "category_title": "🖥️ Игровой ПК",
        "model": f"{gpu_name or 'PC'} + {cpu_name or ''}",
        "cpu": cpu_name or "Не определен",
        "gpu": gpu_name or "Не определена",
        "ram": ram_desc,
        "storage": storage_desc,
        "market_value": round(market_value, 2),
        "price_byn": round(price_byn, 2),
        "profit_byn": round(profit_byn, 2),
        "profit_percent": round(profit_percent, 1),
        "recommended_offer": round(recommended_offer, 2),
        "warnings": "; ".join(warnings) if warnings else "Нет"
    }

def evaluate_generic_item(category_type: str, title: str, body: str, params: Dict[str, Any], price: float) -> Optional[Dict[str, Any]]:
    if category_type == "CONSOLES":
        return evaluate_gaming_console(title, body, price)
    elif category_type == "LAPTOPS":
        return evaluate_laptop(title, body, price)
    elif category_type == "VIDEOCARDS":
        return evaluate_standalone_gpu(title, body, price)
    elif category_type == "PHONES":
        return evaluate_iphone(title, body, price)
    elif category_type == "TABLETS":
        return evaluate_ipad(title, body, price)
    elif category_type == "MONITORS":
        return evaluate_monitor(title, body, price)
    else:
        return evaluate_pc(title, body, params, price)
