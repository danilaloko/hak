import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import os
import time
import sqlite3
import datetime
from typing import Dict, List, Any, Tuple, Optional, Set
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


def get_html_content_from_file(file_path: str) -> str:
    """Загружает HTML-контент из локального файла."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def clean_text(text: str) -> str:
    """Очищает текст от лишних пробелов и переносов строк."""
    return re.sub(r'\s+', ' ', text).strip()


def parse_date(date_str: str) -> str:
    """Преобразует строку с датой в формат YYYY-MM-DD."""
    # Предполагаем, что дата в формате DD.MM.YYYY
    if not date_str:
        return ""

    try:
        # Разбиваем строку по точкам и переставляем части
        parts = date_str.split('.')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass

    # Если не удалось разобрать дату, возвращаем исходную строку
    return date_str


def get_current_date() -> str:
    """Возвращает текущую дату в формате YYYY-MM-DD."""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def setup_selenium_driver():
    """Настраивает и возвращает драйвер Selenium."""
    chrome_options = Options()
    # Добавляем опции для оптимизации работы
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Устанавливаем таймаут загрузки страницы
    chrome_options.add_argument("--page-load-strategy=eager")  # Загружать только DOM, не ждать полной загрузки ресурсов
    # Можно раскомментировать для работы в фоновом режиме
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    # Устанавливаем таймаут загрузки страницы в 5 секунд
    driver.set_page_load_timeout(5)
    return driver


def load_all_cards(driver, url: str) -> None:
    """Загружает страницу и нажимает на кнопку 'показать ещё' до тех пор, пока она не исчезнет."""
    try:
        driver.get(url)

        # Ждем загрузки страницы
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".offers-list"))
        )

        # Нажимаем на кнопку "показать ещё", пока она существует
        while True:
            try:
                # Проверяем наличие кнопки "показать ещё"
                load_more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "load_more"))
                )

                # Прокручиваем страницу к кнопке
                driver.execute_script("arguments[0].scrollIntoView();", load_more_button)

                # Небольшая пауза для стабильности
                time.sleep(1)

                # Нажимаем на кнопку
                load_more_button.click()

                # Ждем загрузки новых карт
                time.sleep(2)

            except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
                # Кнопка не найдена или больше не доступна - все карты загружены
                print("Все карты загружены.")
                break
    except TimeoutException:
        print(f"Превышено время ожидания загрузки страницы {url}. Продолжаем с уже загруженными данными.")


def get_original_offer_url(driver, card_id: str) -> str:
    """Получает URL оригинального предложения банка с помощью Selenium."""
    try:
        # Находим кнопку "Перейти на сайт" для конкретной карты
        button_selector = f"#card-{card_id} .offer-btn"
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
        )

        # Прокручиваем страницу к кнопке
        driver.execute_script("arguments[0].scrollIntoView();", button)

        # Запоминаем текущее количество вкладок
        original_window = driver.current_window_handle

        # Нажимаем на кнопку
        button.click()

        # Ждем открытия новой вкладки
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

        # Переключаемся на новую вкладку
        for window_handle in driver.window_handles:
            if window_handle != original_window:
                driver.switch_to.window(window_handle)
                break

        try:
            # Ждем загрузки страницы и получаем URL
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            offer_url = driver.current_url
        except TimeoutException:
            print(f"Превышено время ожидания загрузки страницы для карты {card_id}. Используем текущий URL.")
            offer_url = driver.current_url

        # Закрываем новую вкладку и возвращаемся к исходной
        driver.close()
        driver.switch_to.window(original_window)

        return offer_url

    except Exception as e:
        print(f"Ошибка при получении URL для карты {card_id}: {e}")

        # Проверяем, не остались ли мы на новой вкладке
        try:
            if len(driver.window_handles) > 1:
                # Если есть больше одной вкладки, закрываем текущую и возвращаемся к исходной
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except Exception as close_error:
            print(f"Ошибка при закрытии вкладки: {close_error}")

        return ""


def extract_card_data(card_element, driver=None) -> Dict[str, Any]:
    """Извлекает данные о кредитной карте из HTML-элемента."""
    card_data = {}

    # Извлечение оригинального ID карты
    original_id = card_element.get('id', '').replace('card-', '')
    card_data['original_id'] = original_id

    # Название банка и продукта
    card_name = card_element.select_one('.adaptive-name')
    if card_name:
        card_data['name'] = card_name.text.strip()

    # Кредитный лимит, обслуживание, беспроцентный период
    card_head_intros = card_element.select('.card-head-center-block .card-head-intro')
    card_conts = card_element.select('.card-head-center-block .card-cont')

    for i, (intro, cont) in enumerate(zip(card_head_intros, card_conts)):
        label = cont.text.strip().lower()
        value = intro.text.strip()

        if 'кредитный лимит' in label:
            card_data['credit_limit'] = value
        elif 'обслуживание' in label:
            card_data['service_fee'] = value
        elif 'беспроцентный период' in label:
            card_data['grace_period'] = value

    # Дата обновления
    update_date = card_element.select_one('.card-upd')
    if update_date:
        update_date_text = update_date.text.replace('Обновлено ', '')
        card_data['update_date'] = update_date_text
        # Добавляем поле updated_at с датой в формате YYYY-MM-DD
        card_data['updated_at'] = parse_date(update_date_text)

    # Добавляем поле created_at с текущей датой
    card_data['created_at'] = get_current_date()

    # Данные из таблицы условий
    table_rows = card_element.select('.table-vertical-block .tr')
    for row in table_rows:
        label_elem = row.select_one('.td:first-child')
        value_elem = row.select_one('.td:last-child')

        if not label_elem or not value_elem:
            continue

        label = label_elem.text.strip().lower()
        value = clean_text(value_elem.text)

        if 'максимальный лимит' in label:
            card_data['max_limit'] = value
        elif 'полная стоимость кредита' in label:
            # Разделение на минимум и максимум
            match = re.search(r'от\s+(\d+[\.,]\d+)\s+до\s+(\d+[\.,]\d+)', value)
            if match:
                card_data['min_full_cost'] = match.group(1).replace(',', '.')
                card_data['max_full_cost'] = match.group(2).replace(',', '.')
        elif 'беспроцентный период' in label:
            card_data['grace_period'] = value
        elif 'открытие' in label:
            card_data['opening_cost'] = value
        elif 'обслуживание' in label:
            card_data['service_fee'] = value
        elif 'кэшбэк' in label:
            card_data['cashback'] = value
        elif 'срок выпуска' in label:
            card_data['issue_period'] = value
        elif 'скорость рассмотрения заявки' in label:
            card_data['review_speed'] = value

    # Требования и документы
    requirements_tab = card_element.select('.tab-content')[1] if len(card_element.select('.tab-content')) > 1 else None
    if requirements_tab:
        req_rows = requirements_tab.select('.tr')
        for row in req_rows:
            label_elem = row.select_one('.td:first-child')
            value_elem = row.select_one('.td:last-child')

            if not label_elem or not value_elem:
                continue

            label = label_elem.text.strip().lower()
            value = clean_text(value_elem.text)

            if 'возраст' in label:
                card_data['age_requirements'] = value
            elif 'документы' in label:
                card_data['documents'] = value
            elif 'регистрация' in label:
                card_data['registration'] = value

    # Описание продукта
    description_tab = card_element.select('.tab-content')[2] if len(card_element.select('.tab-content')) > 2 else None
    if description_tab and description_tab.select_one('p'):
        card_data['description'] = clean_text(description_tab.select_one('p').text)

    # Теги (свойства карты)
    tags = []
    card_tooltips = card_element.select('.card-tooltip')
    for tooltip in card_tooltips:
        text_cont = tooltip.select_one('.text-cont')
        if text_cont:
            tags.append(text_cont.text.strip())

    card_data['tags'] = tags

    # Получение ссылки на оригинальное предложение банка с помощью Selenium
    if driver and original_id:
        offer_url = get_original_offer_url(driver, original_id)
        if offer_url:
            card_data['offer_url'] = offer_url

    return card_data


def assign_sequential_ids(cards_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Присваивает последовательные ID картам, начиная с 0."""
    for i, card in enumerate(cards_data):
        card['id'] = i
    return cards_data


def save_to_json(data: List[Dict[str, Any]], filename: str) -> None:
    """Сохраняет данные в JSON-файл."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_to_csv(data: List[Dict[str, Any]], filename: str) -> None:
    """Сохраняет данные в CSV-файл."""
    if not data:
        return

    # Получаем все возможные ключи из всех словарей
    fieldnames = set()
    for item in data:
        for key in item.keys():
            if key != 'tags':  # Теги обрабатываем отдельно
                fieldnames.add(key)

    # Добавляем поля для тегов
    all_tags = set()
    for item in data:
        if 'tags' in item:
            all_tags.update(item['tags'])

    fieldnames = sorted(list(fieldnames))
    tag_fields = [f'tag_{i + 1}' for i in range(len(all_tags))]

    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames + tag_fields)
        writer.writeheader()

        for item in data:
            row = {k: v for k, v in item.items() if k != 'tags'}

            # Добавляем теги в отдельные колонки
            if 'tags' in item:
                for i, tag in enumerate(item['tags']):
                    row[f'tag_{i + 1}'] = tag

            writer.writerow(row)


def create_database(db_name: str) -> None:
    """Создает базу данных SQLite с необходимыми таблицами."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Создаем таблицу cards
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        original_id TEXT,
        name TEXT,
        credit_limit TEXT,
        service_fee TEXT,
        grace_period TEXT,
        update_date TEXT,
        max_limit TEXT,
        min_full_cost TEXT,
        max_full_cost TEXT,
        opening_cost TEXT,
        cashback TEXT,
        issue_period TEXT,
        review_speed TEXT,
        age_requirements TEXT,
        documents TEXT,
        registration TEXT,
        description TEXT,
        offer_url TEXT,
        updated_at TEXT,
        created_at TEXT
    )
    ''')

    # Создаем таблицу tags
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    ''')

    # Создаем таблицу card_tag для связи многие-ко-многим
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_tag (
        card_id INTEGER,
        tag_id INTEGER,
        PRIMARY KEY (card_id, tag_id),
        FOREIGN KEY (card_id) REFERENCES cards (id),
        FOREIGN KEY (tag_id) REFERENCES tags (id)
    )
    ''')

    conn.commit()
    conn.close()


def save_to_database(data: List[Dict[str, Any]], db_name: str) -> None:
    """Сохраняет данные в базу данных SQLite."""
    if not data:
        return

    # Создаем базу данных, если она не существует
    create_database(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Собираем все уникальные теги
    all_tags: Set[str] = set()
    for item in data:
        if 'tags' in item and item['tags']:
            all_tags.update(item['tags'])

    # Добавляем теги в таблицу tags
    for tag in all_tags:
        cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag,))

    # Получаем id всех тегов
    cursor.execute('SELECT id, name FROM tags')
    tag_id_map = {name: tag_id for tag_id, name in cursor.fetchall()}

    # Добавляем карты в таблицу cards
    for item in data:
        # Создаем список полей и значений для вставки
        fields = []
        values = []

        for key, value in item.items():
            if key != 'tags':  # Теги обрабатываем отдельно
                fields.append(key)
                values.append(value)

        # Формируем SQL-запрос для вставки
        placeholders = ', '.join(['?' for _ in fields])
        fields_str = ', '.join(fields)

        # Вставляем данные о карте
        cursor.execute(f'INSERT OR REPLACE INTO cards ({fields_str}) VALUES ({placeholders})', values)

        # Добавляем связи карта-тег
        if 'id' in item and 'tags' in item and item['tags']:
            card_id = item['id']
            for tag in item['tags']:
                if tag in tag_id_map:
                    tag_id = tag_id_map[tag]
                    cursor.execute('INSERT OR IGNORE INTO card_tag (card_id, tag_id) VALUES (?, ?)',
                                   (card_id, tag_id))

    conn.commit()
    conn.close()

    print(f"Данные успешно сохранены в базу данных {db_name}.")


def load_from_json(filename: str) -> List[Dict[str, Any]]:
    """Загружает данные из JSON-файла."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

        # Добавляем поле created_at, если его нет
        current_date = get_current_date()
        for item in data:
            if 'created_at' not in item:
                item['created_at'] = current_date

        return data


def parse_credit_cards_from_website(url: str) -> List[Dict[str, Any]]:
    """Функция для парсинга кредитных карт с веб-сайта."""
    driver = setup_selenium_driver()

    try:
        # Загружаем страницу и нажимаем на кнопку "показать ещё", пока она не исчезнет
        load_all_cards(driver, url)

        # Получаем HTML-контент страницы после загрузки всех карт
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        cards_data = []
        card_elements = soup.select('.offers-list .card')

        print(f"Найдено карт для парсинга: {len(card_elements)}")

        for i, card_element in enumerate(card_elements):
            print(f"Обработка карты {i + 1}/{len(card_elements)}...")
            card_data = extract_card_data(card_element, driver)
            cards_data.append(card_data)

            # Небольшая пауза между обработкой карт для стабильности
            time.sleep(0.5)

        # Присваиваем последовательные ID
        cards_data = assign_sequential_ids(cards_data)

        return cards_data

    finally:
        # Закрываем драйвер Selenium
        driver.quit()


def main():
    # URL страницы с кредитными картами
    url = 'https://vsezaimyonline.ru/credit-cards'  # Замените на реальный URL

    # Имя файла JSON для сохранения/загрузки данных
    json_filename = 'credit_cards.json'

    # Имя базы данных SQLite
    db_name = 'credit_cards.db'

    try:
        # Проверяем, существует ли уже файл JSON с данными
        if os.path.exists(json_filename):
            print(f"Загружаем данные из существующего файла {json_filename}...")
            cards_data = load_from_json(json_filename)

            # Проверяем, есть ли последовательные ID, если нет - присваиваем
            if any('id' not in card for card in cards_data):
                print("Присваиваем последовательные ID...")
                cards_data = assign_sequential_ids(cards_data)
                # Сохраняем обновленные данные
                save_to_json(cards_data, json_filename)
        else:
            print(f"Начинаем парсинг кредитных карт с сайта: {url}")
            cards_data = parse_credit_cards_from_website(url)

            if cards_data:
                # Сохраняем данные в JSON и CSV
                save_to_json(cards_data, json_filename)
                save_to_csv(cards_data, 'credit_cards.csv')
                print(f"Данные успешно сохранены в файлы. Обработано карт: {len(cards_data)}")

        if cards_data:
            # Сохраняем данные в базу данных SQLite
            save_to_database(cards_data, db_name)
        else:
            print("Не удалось найти данные о кредитных картах.")

    except Exception as e:
        print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()
