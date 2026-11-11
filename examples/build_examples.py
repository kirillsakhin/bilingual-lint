"""Rebuild the example documents: python examples/build_examples.py

The sample contract is invented. Every defect in it is planted on purpose and
listed next to the row, so the expected report is known in advance."""
from __future__ import annotations

from pathlib import Path

from docx import Document as new_docx

HERE = Path(__file__).resolve().parent

# (English, Russian with the defect, Russian without it, rule the defect triggers)
ROWS = [
    ("SUPPLY AGREEMENT No. 15", "ДОГОВОР ПОСТАВКИ № 15", None, None),
    ("Moscow, 12 March 2025", "г. Москва, 21 марта 2025 г.",
     "г. Москва, 12 марта 2025 г.", "BI003"),
    ('Alpha LLC (the "Seller") and Beta GmbH (the "Buyer") have agreed as follows.',
     "ООО «Альфа» (далее – «Продавец») и Beta GmbH (далее – «Покупатель») "
     "договорились о нижеследующем.", None, None),
    ("2.1. The price of the goods is USD 150,000 (one hundred and fifty thousand "
     "US dollars).",
     "2.1. Цена товара составляет 105 000 (сто пять тысяч) долларов США.",
     "2.1. Цена товара составляет 150 000 (сто пятьдесят тысяч) долларов США.", "BI002"),
    ("2.2. The Buyer shall pay for the goods within 10 (ten) business days.",
     "2.2. Покупатель обязан оплатить товар в течение 10 (десяти) дней.",
     "2.2. Покупатель обязан оплатить товар в течение 10 (десяти) рабочих дней.",
     "BI005"),
    ("3.1. The penalty is 0.1% of the price per day of delay, as provided in clause 2.2.",
     "3.1. Неустойка составляет 0,1% от цены за каждый день просрочки согласно п. 2.1.",
     "3.1. Неустойка составляет 0,1% от цены за каждый день просрочки согласно п. 2.2.",
     "BI006"),
    ("3.2. The Seller may not assign its rights under this Agreement.",
     "3.2. Продавец вправе уступать свои права по Договору.",
     "3.2. Продавец не вправе уступать свои права по Договору.", "BI011"),
    ("4.1. Bank details: IBAN DE89 3704 0044 0532 0130 00, e-mail: sales@alpha.example",
     "4.1. Банковские реквизиты: IBAN DE89 3704 0044 0532 0130 01, "
     "эл. почта: sales@alpha.example",
     "4.1. Банковские реквизиты: IBAN DE89 3704 0044 0532 0130 00, "
     "эл. почта: sales@alpha.example", "BI009"),
    ("5.1. In case of discrepancy between the English and Russian texts, "
     "the English text shall prevail.",
     "5.1. В случае расхождений между английским и русским текстами "
     "преимущество имеет текст на русском языке.",
     "5.1. В случае расхождений между английским и русским текстами "
     "преимущество имеет текст на английском языке.", "BI010"),
    ("5.2. This Agreement is made in 2 (two) copies.",
     "5.2. Договор составлен в 3 (двух) экземплярах.",
     "5.2. Договор составлен в 2 (двух) экземплярах.", "BI004"),
    ("6.1. The Buyer shall inspect the goods on delivery.",
     "6.1. Заказчик обязан осмотреть товар при поставке.",
     "6.1. Покупатель обязан осмотреть товар при поставке.", "BI008"),
    ("7. Signatures of the parties", "", "7. Подписи сторон", "BI007"),
    ("This page is intentionally left blank for signatures.",
     "This page is intentionally left blank for signatures.",
     "Эта страница намеренно оставлена пустой для подписей.", "BI007"),
]

SAMPLE = [(en, ru) for en, ru, _, _ in ROWS]
CLEAN = [(en, fixed if fixed is not None else ru) for en, ru, fixed, _ in ROWS]
PLANTED = [rule for _, _, _, rule in ROWS if rule]


def write_two_column(path: Path, rows: list) -> None:
    document = new_docx()
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for left, right in rows:
        cells = table.add_row().cells
        cells[0].text = left
        cells[1].text = right
    document.save(str(path))


def write_plain(path: Path, paragraphs: list) -> None:
    document = new_docx()
    for text in paragraphs:
        if text:
            document.add_paragraph(text)
    document.save(str(path))


def main() -> None:
    write_two_column(HERE / "sample_en_ru.docx", SAMPLE)
    write_two_column(HERE / "clean_en_ru.docx", CLEAN)
    write_plain(HERE / "sample_en.docx", [en for en, _ in SAMPLE])
    write_plain(HERE / "sample_ru.docx", [ru for _, ru in SAMPLE])
    print(f"wrote 4 example files to {HERE}")


if __name__ == "__main__":
    main()
