# Copyright 2026 Google LLC
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

from google.adk.apps.app import App
import vertexai
from .auth_utils import resolve_project_id
from .ca_toolbox_kc_wrapper import app as _wrapper_app
from .ca_toolbox_engine_app import _attach_mcp_tools

project_id = resolve_project_id()
vertexai.init(project=project_id)
_attach_mcp_tools()

app = App(
    root_agent=_wrapper_app.root_agent,
    name="app",
)

__all__ = ["app"]
