from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable


CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_period_amount(
    principal: Decimal,
    periods: Iterable[dict],
) -> dict:
    """
    Calcule des intérêts simples par période.
    Chaque période attend : start, end, annual_rate.
    Le taux est fourni en pourcentage, par exemple Decimal("12.5").
    """
    if principal < 0:
        raise ValueError("Le principal ne peut pas être négatif.")

    total_interest = Decimal("0")
    details = []

    for period in periods:
        start = date.fromisoformat(period["start"])
        end = date.fromisoformat(period["end"])

        try:
            annual_rate = Decimal(str(period["annual_rate"]))
        except InvalidOperation as exc:
            raise ValueError("Taux invalide.") from exc

        if end <= start:
            raise ValueError("La fin de période doit être après le début.")
        if annual_rate < 0:
            raise ValueError("Le taux ne peut pas être négatif.")

        days = Decimal((end - start).days)
        interest = principal * (annual_rate / Decimal("100")) * days / Decimal("365")
        interest = money(interest)
        total_interest += interest

        details.append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": int(days),
            "annual_rate": str(annual_rate),
            "interest": str(interest),
        })

    total_interest = money(total_interest)
    return {
        "principal": str(money(principal)),
        "total_interest": str(total_interest),
        "total": str(money(principal + total_interest)),
        "periods": details,
    }