---
title: v0.142.2 (2025-10-06)
url: https://jurooravec.github.io/django-components/docs/releases/v0.142.2/
description: "- Fix compatibility issue when there was multiple {% include %} blocks
  inside a component fill, while those included templates contained {% extends..."
---

# v0.142.2 (2025-10-06)

#### Fix

- Fix compatibility issue when there was multiple `{% include %}` blocks
  inside a component fill, while those included templates contained `{% extends %}` tags.
  See [#1389](https://github.com/django-components/django-components/issues/1389)