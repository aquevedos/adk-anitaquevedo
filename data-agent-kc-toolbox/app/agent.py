"""Entrypoint for CMI Data Governance Specialist Agent."""

import os
from app.ca_toolbox_kc_wrapper import orchestration_agent, app as kc_app

# Re-export the CMI Data Governance Specialist Agent as root_agent and app for ADK compatibility
root_agent = orchestration_agent
app = kc_app
