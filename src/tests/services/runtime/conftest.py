"""Fixtures shared by runtime release workflow tests."""

import pytest


@pytest.fixture
def binary_response_factory():
    class BinaryResponse:
        def __init__(self, payload=b"payload"):
            self.payload = payload

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    return BinaryResponse
