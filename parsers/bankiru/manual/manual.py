from bs4 import BeautifulSoup
import json
import csv

# ЗАГРУЗИТЕ html ФАЙЛ!!!
with open("path_to_html_file.html", "r", encoding="utf-8") as file:
    html_content = file.read()

soup = BeautifulSoup(html_content, "html.parser")

cards_data = []

card_blocks = soup.find_all("div", class_="Flexbox__sc-1yjv98p-0 bCaZtO")

for block in card_blocks:
    try:
        bank = block.find("div", class_="Text__sc-vycpdy-0 blzkYn").text.strip()
        card_type = block.find("div", class_="Text__sc-vycpdy-0 Lwbrb").text.strip()
        grace_period = block.find("div", string="Льготный период").find_next("div", class_="Text__sc-vycpdy-0 blzkYn").text.strip()
        annual_fee = block.find("div", string="Годовое обслуживание").find_next("div", class_="Text__sc-vycpdy-0 blzkYn").text.strip()
        psk = block.find("div", string="ПСК").find_next("div", class_="Text__sc-vycpdy-0 blzkYn").text.strip()
        interest_rate = block.find("div", string="Ставка").find_next("div", class_="Text__sc-vycpdy-0 blzkYn").text.strip()

        cards_data.append({
            "bank": bank,
            "card_type": card_type,
            "grace_period": grace_period,
            "annual_fee": annual_fee,
            "psk": psk,
            "interest_rate": interest_rate
        })
    except AttributeError:
        continue

# Удаляем дубликаты
unique_cards_data = []
seen = set()

for card in cards_data:
    card_tuple = tuple(card.items())
    if card_tuple not in seen:
        seen.add(card_tuple)
        unique_cards_data.append(card)

with open("credit_cards.json", "w", encoding="utf-8") as json_file:
    json.dump(unique_cards_data, json_file, indent=4, ensure_ascii=False)

with open("credit_cards.csv", "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["bank", "card_type", "grace_period", "annual_fee", "psk", "interest_rate"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for card in unique_cards_data:
        writer.writerow(card)

print("Данные успешно сохранены в credit_cards.json и credit_cards.csv (дубликаты удалены)")