class DotpromptFileError(Exception):
    pass


class FrontmatterParseError(DotpromptFileError):
    pass


class VariantConflictError(DotpromptFileError):
    pass


class TemplateCompileError(DotpromptFileError):
    pass


