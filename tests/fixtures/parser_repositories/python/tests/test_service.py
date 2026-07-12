from src.service import Service


def test_service() -> None:
    assert Service().run(1) == 2
