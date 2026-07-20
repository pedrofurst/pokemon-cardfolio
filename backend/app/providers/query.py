"""Turn what a collector types into a pokemontcg.io query.

Searching by name alone is the weak point of every collection app: "charizard"
returns twenty near-identical Charizards across twenty sets with no way to say
which one you mean. But every card already carries a unique key on its face —
its set and collector number — so an exact match is available whenever someone
types it.

Three shapes are recognised, most specific first:

    base1-4          -> id:base1-4                      (exactly one card)
    charizard 4/102  -> name:"charizard*" number:4      (the printed number)
    charizard        -> name:"charizard*"               (prefix search)
"""

import re

# A pokemontcg.io card id: set id, hyphen, collector number. The number can
# carry a letter suffix (secret rares like "25a"), and set ids themselves
# contain digits (base1, swsh9, sv3pt5).
_CARD_ID = re.compile(r"^([a-z0-9]+)-(\d+[a-z]?)$")

# A trailing collector number, written any of the ways it appears in the wild:
# "charizard 4", "charizard #4", "charizard 4/102".
_TRAILING_NUMBER = re.compile(r"^(.*?)\s*#?(\d+)\s*(?:/\s*\d+)?$")


def _escape(value: str) -> str:
    # Double quotes would terminate the quoted term and break the query.
    return value.replace('"', "")


def build_search_query(raw_query: str) -> str:
    query = raw_query.strip().lower()
    if not query:
        return ""

    card_id = _CARD_ID.match(query)
    if card_id:
        return f"id:{query}"

    trailing = _TRAILING_NUMBER.match(query)
    if trailing:
        name, number = trailing.group(1).strip(), trailing.group(2)
        if not name:
            return f"number:{number}"
        return f'name:"{_escape(name)}*" number:{number}'

    return f'name:"{_escape(query)}*"'
