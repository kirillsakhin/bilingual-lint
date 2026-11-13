"""Three invented contracts, with no defects.

UN documents carry numbers, dates and references, but almost no prices, bank
details, defined party names or prevailing-language clauses. These contracts
supply them. All names, numbers and accounts are made up.

They were written by the author of the rules, so they are a weaker test than
the UN text: results on them are reported separately and never merged with
the UN figures."""
from __future__ import annotations

SERVICES = [
    ("SERVICES AGREEMENT No. 27", "ДОГОВОР ОКАЗАНИЯ УСЛУГ № 27"),
    ("Yerevan, 4 September 2025", "г. Ереван, 4 сентября 2025 г."),
    ('Orion Data LLC (the "Customer") and Meridian Soft GmbH (the "Contractor") '
     "have agreed as follows.",
     "ООО «Орион Дата» (далее – «Заказчик») и Meridian Soft GmbH (далее – «Исполнитель») "
     "договорились о нижеследующем."),
    ("1.1. The Contractor shall provide the software support services listed in Annex 1.",
     "1.1. Исполнитель обязуется оказать услуги по сопровождению программного обеспечения, "
     "перечисленные в Приложении 1."),
    ("1.2. The services shall be provided from 1 October 2025 to 30 September 2026.",
     "1.2. Услуги оказываются с 1 октября 2025 года по 30 сентября 2026 года."),
    ("2.1. The monthly fee is EUR 12,500 (twelve thousand five hundred euros), "
     "excluding VAT.",
     "2.1. Ежемесячное вознаграждение составляет 12 500 (двенадцать тысяч пятьсот) евро "
     "без учёта НДС."),
    ("2.2. The Customer shall pay each invoice within 15 (fifteen) business days of receipt.",
     "2.2. Заказчик обязан оплатить каждый счёт в течение 15 (пятнадцати) рабочих дней "
     "с даты его получения."),
    ("2.3. Late payment bears interest at 0.05% of the overdue amount per day, "
     "as provided in clause 2.2.",
     "2.3. За просрочку оплаты начисляются пени в размере 0,05% от просроченной суммы "
     "за каждый день согласно п. 2.2."),
    ("3.1. The Contractor may not engage subcontractors without the prior written consent "
     "of the Customer.",
     "3.1. Исполнитель не вправе привлекать субподрядчиков без предварительного "
     "письменного согласия Заказчика."),
    ("3.2. The Contractor shall remedy any defect in the services within 5 (five) working "
     "days of the Customer's notice.",
     "3.2. Исполнитель обязан устранить любой недостаток услуг в течение 5 (пяти) рабочих "
     "дней с даты уведомления Заказчика."),
    ("4.1. The liability of the Contractor under this Agreement shall not exceed EUR 150,000.",
     "4.1. Ответственность Исполнителя по Договору не может превышать 150 000 евро."),
    ("5.1. Either party may terminate this Agreement by giving 60 (sixty) days' "
     "written notice.",
     "5.1. Любая из сторон вправе расторгнуть Договор, направив письменное уведомление "
     "за 60 (шестьдесят) дней."),
    ("6.1. Bank details of the Contractor: IBAN DE44 5001 0517 5407 3249 31, "
     "registration number 5263018847.",
     "6.1. Банковские реквизиты Исполнителя: IBAN DE44 5001 0517 5407 3249 31, "
     "регистрационный номер 5263018847."),
    ("7.1. This Agreement is made in English and Russian. In case of discrepancy "
     "the English text shall prevail.",
     "7.1. Договор составлен на английском и русском языках. В случае расхождений "
     "преимущество имеет текст на английском языке."),
    ("7.2. This Agreement is made in 2 (two) copies, one for each party.",
     "7.2. Договор составлен в 2 (двух) экземплярах, по одному для каждой из сторон."),
]

LOAN = [
    ("LOAN AGREEMENT No. 8", "ДОГОВОР ЗАЙМА № 8"),
    ("Almaty, 17 February 2026", "г. Алматы, 17 февраля 2026 г."),
    ('Cedar Capital Ltd (the "Lender") and Polar Logistics LLP (the "Borrower") '
     "have agreed as follows.",
     "Cedar Capital Ltd (далее – «Займодавец») и ТОО «Полар Логистикс» (далее – «Заёмщик») "
     "договорились о нижеследующем."),
    ("1.1. The Lender shall lend the Borrower USD 400,000 (four hundred thousand US dollars).",
     "1.1. Займодавец предоставляет Заёмщику заём в размере 400 000 (четыреста тысяч) "
     "долларов США."),
    ("1.2. The loan shall be disbursed within 3 (three) banking days after the date "
     "of this Agreement.",
     "1.2. Заём предоставляется в течение 3 (трёх) банковских дней с даты заключения "
     "Договора."),
    ("2.1. Interest accrues at 9.5% per annum on the outstanding amount of the loan.",
     "2.1. На непогашенную сумму займа начисляются проценты по ставке 9,5% годовых."),
    ("2.2. Interest is payable on the last business day of each calendar quarter.",
     "2.2. Проценты уплачиваются в последний рабочий день каждого календарного квартала."),
    ("3.1. The Borrower shall repay the loan in full not later than 17 February 2029.",
     "3.1. Заёмщик обязан полностью возвратить заём не позднее 17 февраля 2029 года."),
    ("3.2. The Borrower may repay the loan early in instalments of not less than USD 50,000.",
     "3.2. Заёмщик вправе досрочно возвращать заём частями не менее 50 000 долларов США."),
    ("3.3. If repayment is delayed, the Borrower shall pay a penalty of 0.1% of the overdue "
     "amount per day, in addition to the interest under clause 2.1.",
     "3.3. При просрочке возврата Заёмщик уплачивает неустойку в размере 0,1% от "
     "просроченной суммы за каждый день сверх процентов, предусмотренных п. 2.1."),
    ("4.1. The Borrower must not dispose of its fixed assets worth more than USD 100,000 "
     "without the consent of the Lender.",
     "4.1. Заёмщик не вправе отчуждать основные средства стоимостью свыше 100 000 "
     "долларов США без согласия Займодавца."),
    ("4.2. The Lender may demand early repayment if the Borrower is more than 30 (thirty) "
     "days late with any payment.",
     "4.2. Займодавец вправе потребовать досрочного возврата займа, если Заёмщик допустил "
     "просрочку любого платежа более чем на 30 (тридцать) дней."),
    ("5.1. Account of the Lender: IBAN GB29 NWBK 6016 1331 9268 19, "
     "company number 104417750032.",
     "5.1. Счёт Займодавца: IBAN GB29 NWBK 6016 1331 9268 19, "
     "регистрационный номер компании 104417750032."),
    ("6.1. This Agreement is made in English and Russian. In case of discrepancy "
     "the Russian text shall prevail.",
     "6.1. Договор составлен на английском и русском языках. В случае расхождений "
     "преимущество имеет текст на русском языке."),
    ("6.2. Notices shall be sent within 5 (five) business days to the addresses stated "
     "in this Agreement.",
     "6.2. Уведомления направляются в течение 5 (пяти) рабочих дней по адресам, "
     "указанным в Договоре."),
]

LEASE = [
    ("LEASE AGREEMENT No. 112", "ДОГОВОР АРЕНДЫ № 112"),
    ("Tbilisi, 23 June 2025", "г. Тбилиси, 23 июня 2025 г."),
    ('Harbour Estates JSC (the "Landlord") and Lumen Retail LLC (the "Tenant") '
     "have agreed as follows.",
     "АО «Харбор Эстейтс» (далее – «Арендодатель») и ООО «Люмен Ритейл» "
     "(далее – «Арендатор») договорились о нижеследующем."),
    ("1.1. The Landlord shall lease to the Tenant office premises with an area of "
     "340 square metres on the 6th floor.",
     "1.1. Арендодатель передаёт Арендатору в аренду офисное помещение площадью "
     "340 квадратных метров на 6 этаже."),
    ("1.2. The lease term is 36 (thirty-six) months from 1 July 2025.",
     "1.2. Срок аренды составляет 36 (тридцать шесть) месяцев с 1 июля 2025 года."),
    ("2.1. The monthly rent is 8,200 euros, payable in advance not later than the 5th day "
     "of each month.",
     "2.1. Ежемесячная арендная плата составляет 8 200 евро и вносится авансом не позднее "
     "5 числа каждого месяца."),
    ("2.2. The Tenant shall pay a security deposit of 24,600 euros within 10 (ten) banking "
     "days after signing.",
     "2.2. Арендатор вносит обеспечительный платёж в размере 24 600 евро в течение "
     "10 (десяти) банковских дней после подписания."),
    ("2.3. The rent may be increased once a year by not more than 4%, as provided "
     "in clause 2.1.",
     "2.3. Арендная плата может быть увеличена один раз в год не более чем на 4% "
     "в порядке, предусмотренном п. 2.1."),
    ("3.1. The Tenant may not sublease the premises or any part of them.",
     "3.1. Арендатор не вправе передавать помещение или его часть в субаренду."),
    ("3.2. The Tenant shall not carry out alterations without the written consent "
     "of the Landlord.",
     "3.2. Арендатор не должен производить перепланировку без письменного согласия "
     "Арендодателя."),
    ("3.3. The Landlord shall carry out major repairs at its own expense within "
     "20 (twenty) working days of the Tenant's request.",
     "3.3. Арендодатель обязан производить капитальный ремонт за свой счёт в течение "
     "20 (двадцати) рабочих дней с даты обращения Арендатора."),
    ("4.1. Either party may terminate this Agreement early by giving 90 (ninety) days' "
     "notice, subject to clause 2.2.",
     "4.1. Любая из сторон вправе досрочно расторгнуть Договор, уведомив другую сторону "
     "за 90 (девяносто) дней, с учётом п. 2.2."),
    ("5.1. Rent is paid to the account of the Landlord: IBAN NL91 ABNA 0417 1643 00, "
     "tax number 7701456982.",
     "5.1. Арендная плата вносится на счёт Арендодателя: IBAN NL91 ABNA 0417 1643 00, "
     "налоговый номер 7701456982."),
    ("6.1. This Agreement is made in Russian and English. In case of discrepancy "
     "the Russian version shall prevail.",
     "6.1. Договор составлен на русском и английском языках. При расхождениях "
     "преимущество имеет текст на русском языке."),
    ("6.2. The premises shall be returned on 30 June 2028 in the condition recorded "
     "in the handover certificate.",
     "6.2. Помещение подлежит возврату 30 июня 2028 года в состоянии, зафиксированном "
     "в акте приёма-передачи."),
]

CONTRACTS = [
    {"name": "services", "rows": SERVICES,
     "parties": {"a": ["Customer", "Contractor"], "b": ["Заказчик", "Исполнитель"]}},
    {"name": "loan", "rows": LOAN,
     "parties": {"a": ["Lender", "Borrower"], "b": ["Займодавец", "Заёмщик"]}},
    {"name": "lease", "rows": LEASE,
     "parties": {"a": ["Landlord", "Tenant"], "b": ["Арендодатель", "Арендатор"]}},
]
