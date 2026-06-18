---
title: URLs
url: https://jurooravec.github.io/django-components/docs/reference/urls/
description: "API reference - URLs."
---

# URLs

Below are the URL patterns that `django_components.urls` adds.

Components that expose a public `View` additionally get their own endpoint (via
the view extension); retrieve it with [`get_component_url()`][get_component_url]
rather than hard-coding it.

See [Installation](../getting_started/installation.md#adding-support-for-js-and-css)
on how to add these URLs to your Django project.

Django components already prefixes all URLs with `components/`. So when you are
adding the URLs to `urlpatterns`, you can use an empty string as the first argument:


```python
from django.urls import include, path

urlpatterns = [
    ...
    path("", include("django_components.urls")),
]
```


## List of URLs

- `components/cache/<str:comp_cls_id>.<str:variables_hash>.<str:script_type>`
- `components/cache/<str:comp_cls_id>.<str:script_type>`