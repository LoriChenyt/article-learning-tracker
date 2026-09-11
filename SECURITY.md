# Security Policy

## Sensitive files

HAR files frequently contain authentication material. Never attach a HAR to a
public issue, pull request, release, or repository commit.

Before publishing generated data, verify that it contains only the intended
article metadata. This project removes a conservative list of common session
parameters, but no automated filter can guarantee that every site uses the
same parameter names.

## Reporting a problem

If you find a case where sensitive data reaches the generated CSV, do not post
the affected file publicly. Describe the field name and a synthetic example in
a private security report.
