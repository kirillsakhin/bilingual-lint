# bilingual-lint report

- Source: `examples\sample_en_ru.docx`
- Mode: two-column, en / ru
- Pairs checked: 13 (0 without a counterpart)
- Findings: 12, 8 error, 3 warning, 1 info

## BI003 · error · pair 2

dates differ — en only: 12 March 2025 · ru only: 21 марта 2025

| en (table 1, row 2) | ru (table 1, row 2) |
|---|---|
| Moscow, 12 March 2025 | г. Москва, 21 марта 2025 г. |

## BI002 · error · pair 4

amounts differ — en only: 150,000 · ru only: 105 000

| en (table 1, row 4) | ru (table 1, row 4) |
|---|---|
| 2.1. The price of the goods is USD 150,000 (one hundred and fifty thousand US dollars). | 2.1. Цена товара составляет 105 000 (сто пять тысяч) долларов США. |

## BI005 · error · pair 5

duration day type differs — business against calendar days (en: 10, ru: 10)

| en (table 1, row 5) | ru (table 1, row 5) |
|---|---|
| 2.2. The Buyer shall pay for the goods within 10 (ten) business days. | 2.2. Покупатель обязан оплатить товар в течение 10 (десяти) дней. |

## BI009 · error · pair 8

identifiers differ — en only: DE89370400440532013000 · ru only: DE89370400440532013001

| en (table 1, row 8) | ru (table 1, row 8) |
|---|---|
| 4.1. Bank details: IBAN DE89 3704 0044 0532 0130 00, e-mail: sales@alpha.example | 4.1. Банковские реквизиты: IBAN DE89 3704 0044 0532 0130 01, эл. почта: sales@alpha.example |

## BI010 · error · pair 9

the two sides disagree on which language prevails — en side: en · ru side: ru

| en (table 1, row 9) | ru (table 1, row 9) |
|---|---|
| 5.1. In case of discrepancy between the English and Russian texts, the English text shall prevail. | 5.1. В случае расхождений между английским и русским текстами преимущество имеет текст на русском языке. |

## BI001 · error · pair 10

numbers differ — ru only: 3

| en (table 1, row 10) | ru (table 1, row 10) |
|---|---|
| 5.2. This Agreement is made in 2 (two) copies. | 5.2. Договор составлен в 3 (двух) экземплярах. |

## BI004 · error · pair 10

digits and words disagree on the ru side — 3 against "двух"

| en (table 1, row 10) | ru (table 1, row 10) |
|---|---|
| 5.2. This Agreement is made in 2 (two) copies. | 5.2. Договор составлен в 3 (двух) экземплярах. |

## BI007 · error · pair 12

empty on the ru side

| en (table 1, row 12) | ru (table 1, row 12) |
|---|---|
| 7. Signatures of the parties | — |

## BI006 · warning · pair 6

cross-references differ — en only: 2.2 · ru only: 2.1

| en (table 1, row 6) | ru (table 1, row 6) |
|---|---|
| 3.1. The penalty is 0.1% of the price per day of delay, as provided in clause 2.2. | 3.1. Неустойка составляет 0,1% от цены за каждый день просрочки согласно п. 2.1. |

## BI008 · warning · pair 11

term "Buyer" is used, but "Покупатель" is not on the ru side

| en (table 1, row 11) | ru (table 1, row 11) |
|---|---|
| 6.1. The Buyer shall inspect the goods on delivery. | 6.1. Заказчик обязан осмотреть товар при поставке. |

## BI007 · warning · pair 13

text on the ru side does not look like ru — possibly left untranslated

| en (table 1, row 13) | ru (table 1, row 13) |
|---|---|
| This page is intentionally left blank for signatures. | This page is intentionally left blank for signatures. |

## BI011 · info · pair 7

negation on the en side only — check the meaning

| en (table 1, row 7) | ru (table 1, row 7) |
|---|---|
| 3.2. The Seller may not assign its rights under this Agreement. | 3.2. Продавец вправе уступать свои права по Договору. |
