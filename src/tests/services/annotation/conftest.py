"""Fixtures for annotation service tests."""

import pytest

from src.tests.helpers.images import make_image


@pytest.fixture
def image_factory():
    return make_image
