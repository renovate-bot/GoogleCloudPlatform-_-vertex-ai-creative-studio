# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path
from dataclasses import field

import mesop as me


@me.stateclass
class PageState:
    """VTO Page State"""

    person_image_file: me.UploadedFile = None
    person_image_gcs: str = ""
    product_image_file: me.UploadedFile = None
    product_image_gcs: str = ""
    result_images: list[str] = field(default_factory=list)  # pylint: disable=invalid-field-call
    vto_sample_count: int = 4
    vto_base_steps: int = 32
    is_loading: bool = False
    is_generating_person_image: bool = False
    error_dialog_open: bool = False
    error_message: str = ""

    info_dialog_open: bool = False

    # Load options once
    _options: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        config_path = Path(__file__).parent.parent / "config/virtual_model_options.json"
        with open(config_path, "r") as f:
            self._options = json.load(f)
