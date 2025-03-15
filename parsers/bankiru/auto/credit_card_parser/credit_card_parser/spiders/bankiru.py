import scrapy
import json
import re

class BankiruSpider(scrapy.Spider):
    name = "bankiru"
    allowed_domains = ["banki.ru"]
    start_urls = ["https://www.banki.ru/products/creditcards/"]

    def parse(self, response):
        self.logger.info(f"Парсим страницу: {response.url}")
        self.logger.debug(f"Код ответа: {response.status}")

        # Пробуем найти все data-module-options
        module_options_list = response.css('div[data-module-options]::attr(data-module-options)').getall()
        self.logger.info(f"Найдено элементов data-module-options: {len(module_options_list)}")

        for i, module_options in enumerate(module_options_list):
            try:
                data = json.loads(module_options)
                self.logger.debug(f"JSON #{i}: {json.dumps(data, ensure_ascii=False, indent=2)}")
                if "offers" in data and "items" in data["offers"]:
                    self.logger.info(f"Найден нужный JSON с offers в data-module-options #{i}")
                    for item in self.process_offers(data):
                        yield item
                    break
            except json.JSONDecodeError as e:
                self.logger.error(f"Ошибка парсинга JSON #{i} из data-module-options: {e}")

        # Сохраняем HTML для отладки
        with open("page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        self.logger.info("HTML сохранён в page.html")

    def process_offers(self, data):
        """Обработка предложений из JSON"""
        offers = data.get("offers", {}).get("items", [])
        self.logger.info(f"Найдено предложений: {len(offers)}")

        if not offers:
            self.logger.warning("Список offers пустой! Структура JSON может отличаться.")
            return

        for offer in offers:
            for item in offer.get("items", []):
                product_data = item.get("data", {})
                features = product_data.get("features", [])
                card_title = item.get("productInfo", {}).get("name", "Без названия")
                detail_url = item.get("productInfo", {}).get("url", "")
                # Извлекаем банк из productInfo.partner
                bank_name = item.get("productInfo", {}).get("partner", {}).get("name", "Не указано")

                details = {feature["label"]: feature["value"] for feature in features if "label" in feature and "value" in feature}

                print(f"\n=== Кредитная карта ===")
                print(f"Банк: {bank_name}")
                print(f"Название карты: {card_title}")
                print("Условия:")
                for key, value in details.items():
                    print(f"  {key}: {value}")
                print("=====================\n")

                yield {
                    "bank_name": bank_name,
                    "card_title": card_title,
                    "details": details,
                    "detail_url": detail_url
                }

    def parse_detail_page(self, response):
        self.logger.info(f"Парсим детальную страницу: {response.url}")
        bank_name = response.meta["bank_name"]
        card_title = response.meta["card_title"]

        details = {}
        detail_rows = response.css('div.product-details__row')
        for row in detail_rows:
            key = row.css('div.product-details__label::text').get()
            value = row.css('div.product-details__value::text').get()
            if key and value:
                details[key.strip()] = value.strip()

        if details:
            print(f"\n=== Дополнительные данные карты ===")
            print(f"Банк: {bank_name}")
            print(f"Название карты: {card_title}")
            print("Дополнительные условия:")
            for key, value in details.items():
                print(f"  {key}: {value}")
            print("=====================\n")

        yield {
            "bank_name": bank_name,
            "card_title": card_title,
            "details": details
        }