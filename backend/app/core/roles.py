"""Role names used for RBAC across the API."""

ADMIN = "ADMIN"
REGULATOR = "REGULATOR"
MANUFACTURER = "MANUFACTURER"
DISTRIBUTOR = "DISTRIBUTOR"
PHARMACY = "PHARMACY"
TRANSPORTER = "TRANSPORTER"

# Every role an account may hold.
ROLES = (
    ADMIN,
    REGULATOR,
    MANUFACTURER,
    DISTRIBUTOR,
    PHARMACY,
    TRANSPORTER,
)

# Roles that carry oversight/administrative power.  Anonymous callers may not
# self-register these; only an authenticated ADMIN can create them (the very
# first ADMIN account can bootstrap itself while no ADMIN exists).
PRIVILEGED_ROLES = (ADMIN, REGULATOR)
