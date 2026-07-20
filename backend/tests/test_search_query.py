from app.providers.query import build_search_query


def test_plain_name_becomes_a_prefix_search():
    assert build_search_query("charizard") == 'name:"charizard*"'


def test_multi_word_name_stays_one_prefix_search():
    assert build_search_query("dark charizard") == 'name:"dark charizard*"'


def test_card_id_becomes_an_exact_lookup():
    assert build_search_query("base1-4") == "id:base1-4"


def test_card_id_lookup_is_case_insensitive():
    assert build_search_query("BASE1-4") == "id:base1-4"


def test_card_id_with_a_letter_suffix_is_still_an_exact_lookup():
    assert build_search_query("swsh1-25a") == "id:swsh1-25a"


def test_name_with_trailing_number_filters_by_that_number():
    assert build_search_query("charizard 4") == 'name:"charizard*" number:4'


def test_number_over_set_total_uses_only_the_card_number():
    assert build_search_query("charizard 4/102") == 'name:"charizard*" number:4'


def test_hash_prefixed_number_is_understood():
    assert build_search_query("charizard #4") == 'name:"charizard*" number:4'


def test_multi_word_name_keeps_its_trailing_number_filter():
    assert build_search_query("dark charizard 4") == 'name:"dark charizard*" number:4'


def test_surrounding_whitespace_is_ignored():
    assert build_search_query("  charizard  ") == 'name:"charizard*"'


def test_a_bare_number_searches_by_number_alone():
    assert build_search_query("4") == "number:4"


def test_quotes_in_a_name_are_stripped_so_the_query_stays_valid():
    assert build_search_query('char"izard') == 'name:"charizard*"'


def test_empty_query_is_an_empty_string():
    assert build_search_query("   ") == ""
