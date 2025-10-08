---
title: Passing HTML attributes to components
weight: 1
---

**TL;DR: In some libraries like Vue or django-cotton, when you pass extra kwargs to a component,
the extra fields are assumed to be HTML attributes, and are automatically inserted into
the top-level HTML element. In django_components, use `{% html_attrs %}` to achieve the same effect.**

Imagine you have a component like so:

```python
@register("blog_post")
class BlogPost(Component):
    template = """
      <div>
        <h2> {{ title }} </h2>
      </div>
    """

    def get_context_date(self, title: str):
        return {
            "title": title,
        }
```

In django_coponents, the component accepts only a single argument `title`.
The component can be used in the template like so:

```django
{% component "blog_post" title="The Old Man and the Sea" / %}
```

But maybe you display this component in two different places, and each requires
different formatting:

```html
<!-- Page 1 -->
<div style="color: red">
  <h2> {{ title }} </h2>
</div>
```

```html
<!-- Page 2 -->
<div style="color: blue">
  <h2> {{ title }} </h2>
</div>
```

In libraries like like [Vue](https://vuejs.org/) or [django-cotton](https://github.com/wrabit/django-cotton),
you can pass extra kwargs to a component, and these extra fields are assumed to be HTML attributes
and are automatically inserted into the top-level HTML element:

```django
{% component "blog_post" title="The Old Man and the Sea" style="color: blue" / %}

{% component "blog_post" title="The Old Man and the Sea" style="color: red" / %}
```

However, django_components aims to be usable also for generating non-HTML documents,
and so the extra kwargs are not passed forward automatically.

However, you can use the [`{% html_attrs %}`](../../reference/template_tags.md#html_attrs)
tag to easy write components that allow the component users to add extra CSS classes or
other extra HTML attributes like IDs.

There's two approaches we can take:

### Pass ALL extra kwargs as HTML attributes

1. First, you set the component to any kwargs with `**attrs`, and pass it to the template:

    ```python
    @register("blog_post")
    class BlogPost(Component):
        template = """
          <div>
            <h2> {{ title }} </h2>
          </div>
        """

        def get_context_date(self, title: str, **attrs):
            return {
                "title": title,
                "attrs": attrs,
            }
    ```

2. Next, inside the component's HTML template, insert [`{% html_attrs %}`](../../reference/template_tags.md#html_attrs)
tag inside the `<div>` tag:

    ```django
    <!-- my_comp.html -->
    <div {% html_attrs attrs %}>
      <h2> {{ title }} </h2>
    </div>
    ```

And that's it! Now you can easily pass HTML attributes to your component,
and set different HTML attributes for different instances.

```django
{% component "blog_post" title="The Old Man and the Sea" style="color: blue" / %}

{% component "blog_post" title="The Old Man and the Sea" style="color: red" / %}
```

Which renders:

```html
<!-- Page 1 -->
<div style="color: red">
  <h2> The Old Man and the Sea </h2>
</div>

<!-- Page 2 -->
<div style="color: blue">
  <h2> The Old Man and the Sea </h2>
</div>
```

### Support multiple HTML attribute targets

The previous example is fine if you have only one set of HTML attributes that you want
to render.

But in more complex scenarios, you may want to pass HTML attributes to multiple tags.
What if, in our example, we wanted to allow component users to configure also the header element?

Simple! With the [`dict:key=val` syntax](../../concepts/fundamentals/template_tag_syntax.md#pass-dictonary-by-its-key-value-pairs),
we can still HTML attributes as extra kwargs, and just prefix them with the respective variables:

1. First, you set the component to accept two dictionaries under the `attrs` and `title_attrs` kwargs,
and pass them to the template:

    ```python
    @register("blog_post")
    class BlogPost(Component):
        template = """
          <div>
            <h2> {{ title }} </h2>
          </div>
        """

        def get_context_date(
            self,
            title: str,
            attrs: dict = None,
            title_attrs: dict = None,
        ):
            return {
                "title": title,
                "attrs": attrs,
                "title_attrs": title_attrs,
            }
    ```

2. Next, inside the component's HTML template, insert [`{% html_attrs %}`](../../reference/template_tags.md#html_attrs)
as before, but this time also to the `<h2>` tag:

    ```django
    <!-- my_comp.html -->
    <div {% html_attrs attrs %}>
      <h2 {% html_attrs title_attrs %}> {{ title }} </h2>
    </div>
    ```

And that's it! Now you can easily pass HTML attributes to your component,
and set different HTML attributes for different instances.

To pass the style as attribute, we make use of
the [`dict:key=val` syntax](../../concepts/fundamentals/template_tag_syntax.md#pass-dictonary-by-its-key-value-pairs):

```django
{% component "blog_post"
  title="The Old Man and the Sea"
  attrs:style="color: blue"
  title_attrs:class="pa-4"
/ %}
```

See more on using `{% html_attrs %}` in [HTML attributes](../../concepts/fundamentals/html_attributes.md).
