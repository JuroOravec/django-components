import re

# Convert `getHTTPResponseHTTPCode` to `getHTTP-ResponseHTTP-Code`
tail_uppercase_re = re.compile('(.)([A-Z][a-z]+)')
# Convert `getHTTPResponseHTTPCode` to `get-HTTPResponse-HTTPCode`
head_uppercase_re = re.compile('([a-z0-9])([A-Z])')

# Convert `getHTTPResponseHTTPCode` -> `get-http-response-http-code`
#         `getHTTPResponse_HTTPCode` -> `get-http-response-http-code`
#         `HTTPResponseCodeXYZ` -> `http-response-code-xyz`
#         `camel2-camel2-case` -> `camel2-camel2-case`
#         `camel2_camel2_case` -> `camel2-camel2-case`
# See https://stackoverflow.com/a/1176023/9788634
def to_kebab(name: str) -> str:
    name = tail_uppercase_re.sub(r'\1-\2', name)
    name = head_uppercase_re.sub(r'\1-\2', name).lower()
    name = name.replace("_", "-")
    return name

# Convert `getHTTPResponseHTTPCode` -> `get_http_response_http_code`
#         `getHTTPResponse_HTTPCode` -> `get_http_response_http_code`
#         `HTTPResponseCodeXYZ` -> `http_response_code_xyz`
#         `camel2-camel2-case` -> `camel2_camel2_case`
#         `camel2_camel2_case` -> `camel2_camel2_case`
# See https://stackoverflow.com/a/1176023/9788634
def to_snake(name: str) -> str:
    name = tail_uppercase_re.sub(r'\1_\2', name)
    name = head_uppercase_re.sub(r'\1_\2', name).lower()
    name = name.replace("-", "_")
    return name
