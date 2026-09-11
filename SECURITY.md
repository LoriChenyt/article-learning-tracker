# Security Policy

## Sensitive files

HAR files frequently contain authentication material. HAR files are therefore
excluded from public issues, pull requests, releases, and repository commits.

Generated data should be verified to contain only the intended article
metadata before publication. This project removes a conservative list of common session
parameters, but no automated filter can guarantee that every site uses the
same parameter names.

## Reporting a problem

When sensitive data reaches a generated CSV, the affected file should remain
private. A private security report can describe the field name and provide a
synthetic example.
