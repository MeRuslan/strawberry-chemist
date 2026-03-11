import string
from dataclasses import dataclass


@dataclass
class ConversionData:
    ALPHABET: str
    ALPHABET_SIZE: int
    ALPHABET_CONVERTER: dict


_url_alphabet = string.ascii_letters + string.digits

URL_CONVERSION_DATA = ConversionData(
    ALPHABET=_url_alphabet,
    ALPHABET_SIZE=len(_url_alphabet),
    ALPHABET_CONVERTER={
        v: i for i, v in enumerate(_url_alphabet)
    }
)
LOWERCASE_CONVERSION_DATA = ConversionData(
    ALPHABET=string.ascii_lowercase,
    ALPHABET_SIZE=len(string.ascii_lowercase),
    ALPHABET_CONVERTER={
        v: i for i, v in enumerate(string.ascii_lowercase)
    }
)


def _decompose(number, conversion_data: ConversionData):
    """Generate digits from `number` in base alphabet"""

    while number:
        number, remainder = divmod(number, conversion_data.ALPHABET_SIZE)
        yield remainder


def base_10_to_alphabet(number, conversion_data: ConversionData):
    """Convert a decimal number to its base alphabet representation"""

    return ''.join(
        conversion_data.ALPHABET[part]
        for part in _decompose(number, conversion_data)
    )[::-1]


def base_alphabet_to_10(letters, conversion_data: ConversionData):
    """Convert an alphabet number to its decimal representation"""

    return sum(
        (conversion_data.ALPHABET_CONVERTER[letter]) * conversion_data.ALPHABET_SIZE ** i
        for i, letter in enumerate(reversed(letters))
    )
