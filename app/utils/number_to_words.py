try:
    from num2words import num2words
except ImportError:
    num2words = None


def amount_to_words(amount: float, lang: str = "fr", currency: str = "FCFA") -> str:
    if num2words is None:
        return f"{amount} {currency}"

    try:
        units = int(amount)
        decimals = int(round((amount - units) * 100))
        lang_code = lang.lower() if lang in ["fr", "en", "ar"] else "fr"
        words = num2words(units, lang=lang_code)

        if decimals > 0:
            decimals_words = num2words(decimals, lang=lang_code)
            if lang_code == "fr":
                return f"{words} {currency} et {decimals_words} centimes"
            elif lang_code == "en":
                return f"{words} {currency} and {decimals_words} cents"
            elif lang_code == "ar":
                return f"{words} {currency} و {decimals_words} سنتيم"
        else:
            return f"{words} {currency}"

    except Exception:
        return f"{amount} {currency}"