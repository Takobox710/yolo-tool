from src.ui.features.validation.detection_actions import ValidationDetectionActionsMixin
from src.ui.features.validation.helpers import ResultNavigator, ValidationYamlPatch
from src.ui.features.validation.result_actions import ValidationResultActionsMixin
from src.ui.features.validation.source_actions import ValidationSourceActionsMixin


class ValidationPageActionsMixin(
    ValidationSourceActionsMixin,
    ValidationDetectionActionsMixin,
    ValidationResultActionsMixin,
):
    def _build_result_navigator(self):
        self.validation_yaml_patch = ValidationYamlPatch()
        self.result_navigator = ResultNavigator(
            lambda: self.detect_results,
            lambda: self.detect_index,
            lambda index: setattr(self, "detect_index", index),
            lambda selected: setattr(self, "user_selected_result", selected),
            self.show_detection_payload,
        )
