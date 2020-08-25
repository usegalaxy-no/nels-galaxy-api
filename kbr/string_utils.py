
email_match = '([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})'
email_regex = r"^{}$".format(email_match)

domain_match = '([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})'

def comma_sep(elements:[]) -> str:
    return ", ".join( map(str, elements))
