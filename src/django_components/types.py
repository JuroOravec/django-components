"""Helper types for IDEs."""

from django_components.util.types import Annotated

# TODO - Use https://github.com/jurooravec/python-inline-source-2/blob/main/sourcetypes/sourcetypes.py
#        instead of defining them outselves!
css = Annotated[str, "css"]
sass = Annotated[str, "sass"]
django_html = Annotated[str, "django_html"]
js = Annotated[str, "js"]
ts = Annotated[str, "ts"]  # TODO?
