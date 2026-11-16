import random
import re
from typing import Dict, Any, Optional

GREETINGS = [
    "Здравствуйте!",
    "Добрый день!",
    "Приветствую!"
]

OFFER_TEMPLATES = [
    "{greeting} Заинтересовал ваш системный блок. Готов подъехать и забрать самовывозом без лишних вопросов за {price} руб, если всё исправно. Уступите?",
    "{greeting} Хорошая сборка. Если готовы отдать за {price} BYN, могу забрать сегодня с наличными в удобное для вас время. Что скажете?",
    "{greeting} Ищу ПК себе для работы и игр. Бюджет ограничен {price} руб. Отдадите за эту сумму? Могу подъехать оперативно.",
    "{greeting} За {price} руб готов забрать ваш ПК сегодня/завтра. Базовые проверки на месте при вас. Устроит такое предложение?",
    "{greeting} Рассматриваю ваш компьютер к покупке. Если сойдемся на {price} рублях — готов выехать за ним в ближайшее время."
]

COUNTER_OFFER_TEMPLATES = [
    "Спасибо за ответ! А за {price} руб не сойдемся? Сразу приеду и заберу без долгих тестов.",
    "Понял вас. Если согласитесь на {price} BYN — предложение в силе, готов выехать."
]

def generate_first_offer_message(deal: Dict[str, Any], custom_offer_price: Optional[float] = None) -> str:
    """
    Generates a polite, natural-sounding initial bargaining message
    tailored to the PC listing and proposed offer price.
    """
    price = int(custom_offer_price or deal.get("recommended_offer") or (deal.get("price_byn", 0) * 0.85))
    greeting = random.choice(GREETINGS)
    template = random.choice(OFFER_TEMPLATES)
    return template.format(greeting=greeting, price=price)

def analyze_seller_reply(reply_text: str, current_offer: float, min_acceptable: float) -> Dict[str, Any]:
    """
    Analyzes the seller's reply message to determine:
    - ACCEPTED: seller agreed (e.g., 'давайте', 'хорошо', 'приезжайте', 'договорились')
    - DECLINED: seller refused (e.g., 'без торга', 'нет', 'мало', 'не уступлю')
    - COUNTER: seller named another counter price (e.g., 'отдам за 1400')
    """
    lower = reply_text.lower().strip()
    
    # 1. Check Acceptance
    accept_words = ["давайте", "хорошо", "согласен", "договорились", "забирайте", "приезжайте", "подходит", "ок", "ok"]
    if any(w in lower for w in accept_words) and not any(w in lower for w in ["не", "нет"]):
        return {
            "status": "ACCEPTED",
            "message": "Продавец согласился на сделку!",
            "suggested_reply": "Отлично! Напишите, пожалуйста, точный адрес и когда удобнее подъехать."
        }
        
    # 2. Check Counter Price
    price_matches = re.findall(r'\b(\d{3,4})\b', lower)
    for p_str in price_matches:
        counter_price = float(p_str)
        if counter_price > current_offer and counter_price < current_offer * 1.5:
            # Found counter offer
            if counter_price <= min_acceptable:
                return {
                    "status": "COUNTER_ACCEPTABLE",
                    "counter_price": counter_price,
                    "message": f"Продавец предложил встречную цену {counter_price} BYN (выгодно!)"
                }
            else:
                return {
                    "status": "COUNTER_HIGH",
                    "counter_price": counter_price,
                    "message": f"Продавец предложил встречную цену {counter_price} BYN (выше нашего лимита)"
                }

    # 3. Check Outright Decline
    decline_words = ["без торга", "торга нет", "не интересно", "мало", "нет", "отказано", "не уступлю"]
    if any(w in lower for w in decline_words):
        return {
            "status": "DECLINED",
            "message": "Продавец отказался от торга."
        }

    return {
        "status": "NEEDS_REVIEW",
        "message": "Требуется ручной просмотр ответа продавца."
    }
