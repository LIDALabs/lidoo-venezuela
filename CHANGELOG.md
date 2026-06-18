# Changelog

## [Unreleased]

### Fixed
- `l10n_ve_contact_extensions`: skip address validation (street, state, ZIP) when creating a user. The validation was blocking user creation because the internally created partner lacked required address fields. Partners linked to users (`user_ids`) are now excluded from this check.
