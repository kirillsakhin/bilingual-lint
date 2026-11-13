"""Invented data in the layout of the UN test-set archive."""
from pathlib import Path


def make_set(root: Path, part: str = "devset", n: int = 5, ru_lines: list | None = None,
             en_lines: list | None = None) -> Path:
    folder = root / part
    folder.mkdir(parents=True)
    en = en_lines or [f"Sentence {i} of the report." for i in range(n)]
    ru = ru_lines or [f"Предложение {i} доклада." for i in range(n)]
    ids = [f"2015/a/69/{i // 2} en:{i}:1 ru:{i}:1" for i in range(len(en))]
    for suffix, lines in (("en", en), ("ru", ru), ("ids", ids)):
        (folder / f"UNv1.0.{part}.{suffix}").write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return root


# Eight aligned sentences with figures and dates, enough to plant defects in.
EN = [
    "The Committee held its 14th meeting on 12 March 2015 and adopted the agenda.",
    "The budget for the biennium amounts to 250 million dollars, as stated in paragraph 7.",
    "A total of 48 delegations took part in the general debate on the item.",
    "The report was submitted on 3 February 2015 in accordance with resolution 69/12.",
    "The Secretary-General shall not disclose the names of the experts consulted.",
    "The working group will meet again in Geneva to continue its consideration.",
    "Contributions received from 31 Member States were recorded by the secretariat.",
    "The session was closed by the Chair after the adoption of the draft decision.",
]
RU = [
    "Комитет провел свое 14-е заседание 12 марта 2015 года и утвердил повестку дня.",
    "Бюджет на двухгодичный период составляет 250 млн. долларов, как указано в пункте 7.",
    "В общих прениях по этому пункту приняли участие в общей сложности 48 делегаций.",
    "Доклад был представлен 3 февраля 2015 года в соответствии с резолюцией 69/12.",
    "Генеральный секретарь не должен разглашать имена экспертов, с которыми он консультировался.",
    "Рабочая группа вновь соберется в Женеве, чтобы продолжить рассмотрение вопроса.",
    "Секретариат зарегистрировал взносы, полученные от 31 государства-члена.",
    "Председатель закрыл сессию после принятия проекта решения.",
]
