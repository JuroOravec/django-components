from typing import Any, Dict

from django_components import Component


class Greeting(Component):
    template_file = "greeting2.html"
    css_file = "greeting2.css"
    js_file = "greeting2.js"

    def get(self, request, *args, **kwargs):
        slots = {"message": "Hello, world!"}
        return self.render_to_response(
            slots=slots,
            kwargs={
                "name": request.GET.get("name", ""),
            },
        )

    def get_context_data(self, name, *args, **kwargs) -> Dict[str, Any]:
        return {"name": name}
