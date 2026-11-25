"""Public framework identity and the revision used for cache binding."""

FRAMEWORK_VERSION = 'BaseIntent'
MODULE_REVISION = 'intent-modules-v1'


def framework_version_for_profile(profile):
    return FRAMEWORK_VERSION if profile in ('legacy', 'intent-evidence-v35') else 'BaseIntent-legacy-v34'
