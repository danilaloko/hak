import scrapy

class BankiruSpider(scrapy.Spider):
    name = "bankiru"  # Имя паука, используется при запуске
    allowed_domains = ["banki.ru"]  # Ограничиваем домены для парсинга
    start_urls = ["https://www.banki.ru/products/creditcards/"]  # Начальная страница

    def parse(self, response):
        """
        Основная функция парсинга главной страницы со списком кредитных карт.
        Извлекает данные о каждой карте и переходит в раздел "Подробнее".
        """
        # Находим все блоки с кредитными картами
        card_blocks = response.css('div.ui-product-card')

        for card in card_blocks:
            # Извлекаем название банка
            bank_name = card.css('div.ui-product-card__bank-title a::text').get()
            if not bank_name:
                bank_name = "Не указано"  # Если название банка не найдено

            # Извлекаем базовое название карты (если есть)
            card_title = card.css('div.ui-product-card__title a::text').get()

            # Ссылка на страницу "Подробнее"
            detail_link = card.css('div.ui-product-card__title a::attr(href)').get()
            if detail_link:
                # Полный URL для перехода
                detail_url = response.urljoin(detail_link)
                # Передаем данные банка и название карты в следующую функцию
                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail_page,
                    meta={'bank_name': bank_name, 'card_title': card_title}
                )

            # Проверяем наличие дополнительных предложений ("еще X предложений")
            more_offers = card.css('div.ui-product-card__more-offers a::attr(href)').get()
            if more_offers:
                more_offers_url = response.urljoin(more_offers)
                yield scrapy.Request(
                    url=more_offers_url,
                    callback=self.parse_detail_page,
                    meta={'bank_name': bank_name, 'card_title': card_title}
                )

    def parse_detail_page(self, response):
        """
        Функция для парсинга страницы "Подробнее" каждой карты.
        Извлекает условия карты и выводит их в консоль.
        """
        bank_name = response.meta['bank_name']  # Получаем название банка из meta
        card_title = response.meta['card_title']  # Получаем название карты из meta

        # Извлекаем ключевые условия карты (пример, структура может отличаться)
        details = {}
        detail_rows = response.css('div.product-details__row')  # Блоки с условиями
        for row in detail_rows:
            key = row.css('div.product-details__label::text').get()
            value = row.css('div.product-details__value::text').get()
            if key and value:
                details[key.strip()] = value.strip()

        # Форматированный вывод в консоль
        print(f"\n=== Кредитная карта ===")
        print(f"Банк: {bank_name}")
        print(f"Название карты: {card_title}")
        print("Условия:")
        for key, value in details.items():
            print(f"  {key}: {value}")
        print("=====================\n")

        # Возвращаем данные в виде словаря (для дальнейшей обработки, если нужно)
        yield {
            'bank_name': bank_name,
            'card_title': card_title,
            'details': details
        }
