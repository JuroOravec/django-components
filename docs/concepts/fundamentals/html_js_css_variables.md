<!--
- TODO - Update signature of all `get_js_data()` and `get_css_data()` methods
- TODO - Add tests for JS / CSS variables?
 -->

When a component recieves input through [`{% component %}`](../../../reference/template_tags/#component) tag,
or the [`Component.render()`](../../../reference/api/#django_components.Component.render) or [`Component.render_to_response()`](../../../reference/api/#django_components.Component.render_to_response) methods, you can define how the input is handled, and what variables will be available to the template, JavaScript and CSS.

## Overview

Django Components offers three key methods for passing variables to different parts of your component:

- [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) - Provides variables to your HTML template
- [`get_js_data()`](../../../reference/api/#django_components.Component.get_js_data) - Provides variables to your JavaScript code
- [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data) - Provides variables to your CSS styles

These methods let you pre-process inputs before they're used in rendering.

Each method handles the data independently - you can define different data for the template, JS, and CSS.

```python
class ProfileCard(Component):
    class Kwargs(NamedTuple):
        user_id: int
        show_details: bool

    class Defaults:
        show_details = True

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        user = User.objects.get(id=kwargs.user_id)
        return {
            "user": user,
            "show_details": kwargs.show_details,
        }

    def get_js_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "user_id": kwargs.user_id,
        }

    def get_css_data(self, args, kwargs: Kwargs, slots, context):
        text_color = "red" if kwargs.show_details else "blue"
        return {
            "text_color": text_color,
        }
```

## Template variables

The [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) method is the primary way to provide variables to your HTML template. It receives the component inputs and returns a dictionary of data that will be available in the template.

If [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) returns `None`, an empty dictionary will be used.

```python
class ProfileCard(Component):
    template_file = "profile_card.html"

    class Kwargs(NamedTuple):
        user_id: int
        show_details: bool

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        user = User.objects.get(id=kwargs.user_id)

        # Process and transform inputs
        return {
            "user": user,
            "show_details": kwargs.show_details,
            "user_joined_days": (timezone.now() - user.date_joined).days,
        }
```

In your template, you can then use these variables:

```django
<div class="profile-card">
    <h2>{{ user.username }}</h2>

    {% if show_details %}
        <p>Member for {{ user_joined_days }} days</p>
        <p>Email: {{ user.email }}</p>
    {% endif %}
</div>
```

### Legacy `get_context_data()`

The [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data) method is the legacy way to provide variables to your HTML template. It serves the same purpose as [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data) - it receives the component inputs and returns a dictionary of data that will be available in the template.

However, [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data) has a few drawbacks:

- It does NOT receive the `slots` and `context` parameters.
- The `args` and `kwargs` parameters are given as variadic `*args` and `**kwargs` parameters. As such, they cannot be typed.

```python
class ProfileCard(Component):
    template_file = "profile_card.html"

    def get_context_data(self, user_id, show_details=False, *args, **kwargs):
        user = User.objects.get(id=user_id)
        return {
            "user": user,
            "show_details": show_details,
        }
```

There is a slight difference between [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data) and [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data)
when rendering a component with the [`{% component %}`](../../../reference/template_tags/#component) tag.

For example if you have component that accepts kwarg `date`:

```py
class MyComponent(Component):
    def get_context_data(self, date, *args, **kwargs):
        return {
            "date": date,
        }

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs["date"],
        }
```

The difference is that:

- With [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data), you can pass `date` either as arg or kwarg:

    ```django
    ✅
    {% component "my_component" date=some_date %}
    {% component "my_component" some_date %}
    ```

- But with [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data), `date` MUST be passed as kwarg:

    ```django
    ✅
    {% component "my_component" date=some_date %}

    ❌
    {% component "my_component" some_date %}
    ```

!!! warning

    [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data)
    and [`get_context_data()`](../../../reference/api/#django_components.Component.get_context_data)
    are mutually exclusive.

    If both methods return non-empty dictionaries, an error will be raised.

!!! note

    The `get_context_data()` method will be removed in v2.

## JS variables

The [`get_js_data()`](../../../reference/api/#django_components.Component.get_js_data) method lets you pass data from your Python component to your JavaScript code defined in
[`Component.js`](../../../reference/api/#django_components.Component.js)
or [`Component.js_file`](../../../reference/api/#django_components.Component.js_file).

The returned dictionary will be serialized to a JSON object in Python, and then deserialized back in the browser (JavaScript).

If [`get_js_data()`](../../../reference/api/#django_components.Component.get_js_data) returns `None`, an empty dictionary will be used.

```python
class InteractiveMap(Component):
    template_file = "map.html"
    js_file = "map.js"

    class Kwargs(NamedTuple):
        location_id: int

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        location = Location.objects.get(id=kwargs.location_id)
        return {
            "location_name": location.name,
        }

    def get_js_data(self, args, kwargs: Kwargs, slots, context):
        location = Location.objects.get(id=kwargs.location_id)
        return {
            "lat": location.latitude,
            "lng": location.longitude,
            "zoom": 13,
            "markers": list(location.markers.values("lat", "lng", "title")),
        }
```

### Accessing JS variables

<!-- TODO FINISH!!! -->

In your JavaScript file, you can access these variables by passing a callback to a special `$onLoad()` function.

```js
$onLoad(({ lat, lng, zoom, markers }) => {
  console.log(`Initializing map for coordinates: ${lat},${lng}`);

  const map = new Map({
    center: [lat, lng],
    zoom: zoom,
  });

  markers.forEach((marker) => {
    map.addMarker(marker.lat, marker.lng, marker.title);
  });
});
```

## CSS variables

The [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data) method lets you pass data from your Python component to your CSS code defined in
[`Component.css`](../../../reference/api/#django_components.Component.css)
or [`Component.css_file`](../../../reference/api/#django_components.Component.css_file).

The returned dictionary will be converted to [CSS variables](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_cascading_variables/Using_CSS_custom_properties) where:

- Keys are names of CSS variables
- Values are serialized to string

If [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data) returns `None`, an empty dictionary will be used.

```python
class ThemeableButton(Component):
    template_file = "button.html"
    css_file = "button.css"

    class Kwargs(NamedTuple):
        label: str
        theme: str

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "label": kwargs.label,
        }

    def get_css_data(self, args, kwargs: Kwargs, slots, context):
        themes = {
            "default": {"bg": "#f0f0f0", "color": "#333", "hover_bg": "#e0e0e0"},
            "primary": {"bg": "#0275d8", "color": "#fff", "hover_bg": "#025aa5"},
            "danger": {"bg": "#d9534f", "color": "#fff", "hover_bg": "#c9302c"},
        }

        chosen_theme = themes.get(kwargs.theme, themes["default"])

        return {
            "button_bg": chosen_theme["bg"],
            "button_color": chosen_theme["color"],
            "button_hover_bg": chosen_theme["hover_bg"],
        }
```

### Accessing CSS variables

In your CSS file, you can access these variables by using the [`var()`](https://developer.mozilla.org/en-US/docs/Web/CSS/var) function.

Use the same variable names as in the dictionary returned from [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data).

```css
.themed-button {
  background-color: var(--button_bg);
  color: var(--button_color);
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
}

.themed-button:hover {
  background-color: var(--button_hover_bg);
}
```

!!! info

    **How it works?**

    When a component defines some CSS code, it will be added to the page as a separate stylesheet.
    So all instances of the same Component class reuse this same stylesheet which references the variables:

    ```css
    .themed-button:hover {
        background-color: var(--button_hover_bg);
    }
    ```

    When a component defines some CSS variables, django-components generates a stylesheet to apply
    the variables:

    ```css
    [data-djc-css-b2c3d4] {
        --button_bg: #f0f0f0;
        --button_color: #333;
        --button_hover_bg: #e0e0e0;
    }
    ```

    This stylesheet with the variables is cached on the server based on the variables' names and values.

    This stylesheet is then added to the CSS dependencies of the component (as if added to `Component.Media.css`).
    So the variables stylesheet will be loaded with the rest of the component's CSS.

    The rendered component will have a corresponding `data-djc-css-b2c3d4` HTML attribute, matching the hash.

    Thus, the CSS variables are dynamically applied to the component, and ONLY to this single instance (or
    other instances that have the same variables).

    This means that if you render the same component with different variables, each instance will use different CSS variables.

## Accessing component inputs

The component inputs are available in 3 ways:

### Function arguments

The data methods receive the inputs as parameters directly.

```python
class ProfileCard(Component):
    # Access inputs directly as parameters
    def get_template_data(self, args, kwargs, slots, context):
        return {
            "user_id": args[0],
            "show_details": kwargs["show_details"],
        }
```

!!! info

    By default, the `args` parameter is a list, while `kwargs` and `slots` are dictionaries.

    If you add typing to your component with
    [`Args`](../../../reference/api/#django_components.Component.Args),
    [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
    or [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
    the respective inputs will be given as instances of these classes.

    Learn more about [Component typing](../../fundamentals/typing_and_validation).

    ```py
    class ProfileCard(Component):
        class Args(NamedTuple):
            user_id: int

        class Kwargs(NamedTuple):
            show_details: bool

        # Access inputs directly as parameters
        def get_template_data(self, args: Args, kwargs: Kwargs, slots, context):
            return {
                "user_id": args.user_id,
                "show_details": kwargs.show_details,
            }
    ```

### `args`, `kwargs`, `slots` properties

In other methods, you can access the inputs via
[`self.args`](../../../reference/api/#django_components.Component.args),
[`self.kwargs`](../../../reference/api/#django_components.Component.kwargs),
and [`self.slots`](../../../reference/api/#django_components.Component.slots) properties:

```py
class ProfileCard(Component):
    def on_render_before(self, context: Context, template: Optional[Template]):
        # Access inputs via self.args, self.kwargs, self.slots
        self.args[0]
        self.kwargs.get("show_details", False)
        self.slots["footer"]
```

!!! info

    These properties work the same way as `args`, `kwargs`, and `slots` parameters in the data methods:

    By default, the `args` property is a list, while `kwargs` and `slots` are dictionaries.

    If you add typing to your component with
    [`Args`](../../../reference/api/#django_components.Component.Args),
    [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
    or [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
    the respective inputs will be given as instances of these classes.

    Learn more about [Component typing](../../fundamentals/typing_and_validation).

    ```py
    class ProfileCard(Component):
        class Args(NamedTuple):
            user_id: int

        class Kwargs(NamedTuple):
            show_details: bool

        def get_template_data(self, args: Args, kwargs: Kwargs, slots, context):
            return {
                "user_id": self.args.user_id,
                "show_details": self.kwargs.show_details,
            }
    ```

<!-- TODO_v1 - Remove -->

### `input` property (low-level)

!!! warning

    The `input` property is deprecated and will be removed in v1.

    Instead, use properties defined on the
    [`Component`](../../../reference/api/#django_components.Component) class
    directly like
    [`self.context`](../../../reference/api/#django_components.Component.context).

    To access the unmodified inputs, use
    [`self.raw_args`](../../../reference/api/#django_components.Component.raw_args),
    [`self.raw_kwargs`](../../../reference/api/#django_components.Component.raw_kwargs),
    and [`self.raw_slots`](../../../reference/api/#django_components.Component.raw_slots) properties.

The previous two approaches allow you to access only the most important inputs.

There are additional settings that may be passed to components.
If you need to access these, you can use [`self.input`](../../../reference/api/#django_components.Component.input) property
for a low-level access to all the inputs.

The `input` property contains all the inputs passed to the component (instance of [`ComponentInput`](../../../reference/api/#django_components.ComponentInput)).

This includes:

- [`input.args`](../../../reference/api/#django_components.ComponentInput.args) - List of positional arguments
- [`input.kwargs`](../../../reference/api/#django_components.ComponentInput.kwargs) - Dictionary of keyword arguments
- [`input.slots`](../../../reference/api/#django_components.ComponentInput.slots) - Dictionary of slots. Values are normalized to [`Slot`](../../../reference/api/#django_components.Slot) instances
- [`input.context`](../../../reference/api/#django_components.ComponentInput.context) - [`Context`](https://docs.djangoproject.com/en/5.2/ref/templates/api/#django.template.Context) object that should be used to render the component
- [`input.type`](../../../reference/api/#django_components.ComponentInput.type) - The type of the component (document, fragment)
- [`input.render_dependencies`](../../../reference/api/#django_components.ComponentInput.render_dependencies) - Whether to render dependencies (CSS, JS)

```python
class ProfileCard(Component):
    def get_template_data(self, args, kwargs, slots, context):
        # Access positional arguments
        user_id = self.input.args[0] if self.input.args else None

        # Access keyword arguments
        show_details = self.input.kwargs.get("show_details", False)

        # Render component differently depending on the type
        if self.input.type == "fragment":
            ...

        return {
            "user_id": user_id,
            "show_details": show_details,
        }
```

!!! info

    Unlike the parameters passed to the data methods, the `args`, `kwargs`, and `slots` in `self.input` property are always lists and dictionaries,
    regardless of whether you added typing classes to your component (like [`Args`](../../../reference/api/#django_components.Component.Args),
    [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
    or [`Slots`](../../../reference/api/#django_components.Component.Slots)).

## Default values

You can use [`Defaults`](../../../reference/api/#django_components.Component.Defaults) class to provide default values for your inputs.

These defaults will be applied either when:

- The input is not provided at rendering time
- The input is provided as `None`

When you then access the inputs in your data methods, the default values will be already applied.

Read more about [Component Defaults](./component_defaults.md).

```py
from django_components import Component, Default, register

@register("profile_card")
class ProfileCard(Component):
    class Kwargs(NamedTuple):
        show_details: bool

    class Defaults:
        show_details = True

    # show_details will be set to True if `None` or missing
    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "show_details": kwargs.show_details,
        }

    ...
```

!!! warning

    When typing your components with [`Args`](../../../reference/api/#django_components.Component.Args),
    [`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
    or [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
    you may be inclined to define the defaults in the classes.

    ```py
    class ProfileCard(Component):
        class Kwargs(NamedTuple):
            show_details: bool = True
    ```

    This is **NOT recommended**, because:

    - The defaults will NOT be applied to inputs when using [`self.raw_kwargs`](../../../reference/api/#django_components.Component.raw_kwargs) property.
    - The defaults will NOT be applied when a field is given but set to `None`.

    Instead, define the defaults in the [`Defaults`](../../../reference/api/#django_components.Component.Defaults) class.

## Accessing Render API

All three data methods have access to the Component's [Render API](../render_api), which includes:

- [`self.args`](../render_api/#args) - The positional arguments for the current render call
- [`self.kwargs`](../render_api/#kwargs) - The keyword arguments for the current render call
- [`self.slots`](../render_api/#slots) - The slots for the current render call
- [`self.raw_args`](../render_api/#args) - Unmodified positional arguments for the current render call
- [`self.raw_kwargs`](../render_api/#kwargs) - Unmodified keyword arguments for the current render call
- [`self.raw_slots`](../render_api/#slots) - Unmodified slots for the current render call
- [`self.context`](../render_api/#context) - The context for the current render call
- [`self.id`](../render_api/#component-id) - The unique ID for the current render call
- [`self.request`](../render_api/#request-and-context-processors) - The request object
- [`self.context_processors_data`](../render_api/#request-and-context-processors) - Data from Django's context processors
- [`self.inject()`](../render_api/#provide-inject) - Inject data into the component
- [`self.registry`](../render_api/#template-tag-metadata) - The [`ComponentRegistry`](../../../reference/api/#django_components.ComponentRegistry) instance
- [`self.registered_name`](../render_api/#template-tag-metadata) - The name under which the component was registered
- [`self.outer_context`](../render_api/#template-tag-metadata) - The context outside of the [`{% component %}`](../../../reference/template_tags#component) tag
- `self.deps_strategy` - The strategy for rendering dependencies

## Type hints

### Typing inputs

You can add type hints for the component inputs to ensure that the component logic is correct.

For this, define the [`Args`](../../../reference/api/#django_components.Component.Args),
[`Kwargs`](../../../reference/api/#django_components.Component.Kwargs),
and [`Slots`](../../../reference/api/#django_components.Component.Slots) classes,
and then add type hints to the data methods.

This will also validate the inputs at runtime, as the type classes will be instantiated with the inputs.

Read more about [Component typing](../../fundamentals/typing_and_validation).

```python
from typing import NamedTuple, Optional
from django_components import Component, SlotInput

class Button(Component):
    class Args(NamedTuple):
        name: str

    class Kwargs(NamedTuple):
        surname: str
        maybe_var: Optional[int] = None  # May be omitted

    class Slots(NamedTuple):
        my_slot: Optional[SlotInput] = None
        footer: SlotInput

    # Use the above classes to add type hints to the data method
    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        # The parameters are instances of the classes we defined
        assert isinstance(args, Button.Args)
        assert isinstance(kwargs, Button.Kwargs)
        assert isinstance(slots, Button.Slots)
```

!!! note

    To access "untyped" inputs, use [`self.raw_args`](../../../reference/api/#django_components.Component.raw_args),
    [`self.raw_kwargs`](../../../reference/api/#django_components.Component.raw_kwargs),
    and [`self.raw_slots`](../../../reference/api/#django_components.Component.raw_slots) properties.

    These are plain lists and dictionaries, even when you added typing to your component.

### Typing data

In the same fashion, you can add types and validation for the data that should be RETURNED from each data method.

For this, set the [`TemplateData`](../../../reference/api/#django_components.Component.TemplateData),
[`JsData`](../../../reference/api/#django_components.Component.JsData),
and [`CssData`](../../../reference/api/#django_components.Component.CssData) classes on the component class.

For each data method, you can either return a plain dictionary with the data, or an instance of the respective data class.

```python
from typing import NamedTuple
from django_components import Component

class Button(Component):
    class TemplateData(NamedTuple):
        data1: str
        data2: int

    class JsData(NamedTuple):
        js_data1: str
        js_data2: int

    class CssData(NamedTuple):
        css_data1: str
        css_data2: int

    def get_template_data(self, args, kwargs, slots, context):
        return Button.TemplateData(
            data1="...",
            data2=123,
        )

    def get_js_data(self, args, kwargs, slots, context):
        return Button.JsData(
            js_data1="...",
            js_data2=123,
        )

    def get_css_data(self, args, kwargs, slots, context):
        return Button.CssData(
            css_data1="...",
            css_data2=123,
        )
```

## Pass-through kwargs

It's best practice to explicitly define what args and kwargs a component accepts.

However, if you want a looser setup, you can easily write components that accept any number
of kwargs, and pass them all to the template
(similar to [django-cotton](https://github.com/wrabit/django-cotton)).

To do that, simply return the `kwargs` dictionary itself from [`get_template_data()`](../../../reference/api/#django_components.Component.get_template_data):

```py
class MyComponent(Component):
    def get_template_data(self, args, kwargs, slots, context):
        return kwargs
```

You can do the same for [`get_js_data()`](../../../reference/api/#django_components.Component.get_js_data) and [`get_css_data()`](../../../reference/api/#django_components.Component.get_css_data), if needed:

```py
class MyComponent(Component):
    def get_js_data(self, args, kwargs, slots, context):
        return kwargs

    def get_css_data(self, args, kwargs, slots, context):
        return kwargs
```

## Complete example

<!-- TODO FINISH + DONT FORGET TO UPDATE get_context_data() signature -->

Here's a comprehensive example showing all three methods working together:

```python
class ProductCard(Component):
    template_file = "product_card.html"
    js_file = "product_card.js"
    css_file = "product_card.css"

    def get_context_data(self, product_id, show_price=True, *args, **kwargs):
        product = Product.objects.get(id=product_id)
        return {
            "product": product,
            "show_price": show_price,
            "is_in_stock": product.stock_count > 0,
        }

    def get_js_data(self, product_id, *args, **kwargs):
        product = Product.objects.get(id=product_id)
        return {
            "product_id": product_id,
            "price": float(product.price),
            "api_endpoint": f"/api/products/{product_id}/",
        }

    def get_css_data(self, product_id, theme="light", *args, **kwargs):
        themes = {
            "light": {
                "card_bg": "#ffffff",
                "text_color": "#333333",
                "price_color": "#e63946",
            },
            "dark": {
                "card_bg": "#242424",
                "text_color": "#f1f1f1",
                "price_color": "#ff6b6b",
            },
        }

        return themes.get(theme, themes["light"])
```

In your template:

```django
<div class="product-card" data-product-id="{{ product.id }}">
    <img src="{{ product.image_url }}" alt="{{ product.name }}">
    <h3>{{ product.name }}</h3>

    {% if show_price %}
        <p class="price">${{ product.price }}</p>
    {% endif %}

    {% if is_in_stock %}
        <button class="add-to-cart">Add to Cart</button>
    {% else %}
        <p class="out-of-stock">Out of Stock</p>
    {% endif %}
</div>
```

JavaScript:

```javascript
document
  .querySelector(`[data-product-id="${product_id}"]`)
  .querySelector(".add-to-cart")
  .addEventListener("click", () => {
    fetch(api_endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "add_to_cart", price: price }),
    });
  });
```

CSS:

```css
.product-card {
  background-color: var(--card_bg);
  color: var(--text_color);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.price {
  color: var(--price_color);
  font-weight: bold;
}
```
