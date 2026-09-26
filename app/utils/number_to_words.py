from num2words import num2words


def amount_to_words(amount: float, lang: str = "fr", currency: str = "FCFA") -> str:
    """
    Convertit un montant numérique en lettres selon la langue spécifiée.
    Langues supportées : 'fr' (Français), 'en' (Anglais), 'ar' (Arabe).
    """
    try:
        # Séparation de la partie entière et des centimes
        units = int(amount)
        decimals = int(round((amount - units) * 100))

        # Support de la langue
        lang_code = lang.lower() if lang in ["fr", "en", "ar"] else "fr"

        # Conversion de la partie entière
        words = num2words(units, lang=lang_code)

        # Construction de la phrase avec la devise
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

    except Exception as e:
        return f"{amount} {currency}"