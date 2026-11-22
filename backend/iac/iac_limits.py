"""Process limits for the in-memory IaC workspace.

These numbers are inputs from the NFR design. Do not lower them to make a
test pass.
"""

SLOT_LIMIT_BYTES = 16 * 1024 * 1024
MAX_SLOTS_PER_USER = 3
MAX_GENERATE_IN_FLIGHT = 2
GENERATE_TIMEOUT_SECONDS = 90
CHECKOV_TIMEOUT_SECONDS = 10
CHECKOV_VERSION = "3.4.3"
