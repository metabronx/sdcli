import pytest


def test_module_call(capfd):
    """this is a silly test for module-level execution, but here for code coverage"""
    with pytest.raises(SystemExit):
        import sdcli.__main__  # noqa
