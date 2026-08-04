from __future__ import annotations

from src.ui.shared.form_actions import FormActionMixin
from src.ui.shared.form_fields import FormFieldMixin


class FormPageMixin(FormFieldMixin, FormActionMixin):
    """Compatibility façade for the shared page form API."""


__all__ = ["FormPageMixin"]
