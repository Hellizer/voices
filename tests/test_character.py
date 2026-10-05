from sim.character import (
    create_character,
    derive_self_name,
    SELF_NAME_TEMPLATES,
)


def test_default_name_and_gender():
    c = create_character()
    assert c.name == ""
    assert c.gender == "female"
    assert c.self_name == ""


def test_derive_self_name_female():
    assert derive_self_name("female", "control") == "та, кто держит"
    assert derive_self_name("female", "body") == "та, кто слушает тело"


def test_derive_self_name_male():
    assert derive_self_name("male", "control") == "тот, кто держит"
    assert derive_self_name("male", "interest") == "тот, кто ищет"


def test_derive_self_name_unknown_gender_fallback():
    assert derive_self_name("unknown", "control") == "та, кто держит"


def test_derive_self_name_unknown_voice_empty():
    assert derive_self_name("female", "unknown") == ""
    assert derive_self_name("male", "unknown") == ""


def test_templates_have_all_voices():
    for gender in ("male", "female"):
        for voice in ("body", "safety", "connection", "recognition", "interest", "control"):
            assert SELF_NAME_TEMPLATES[gender].get(voice)
