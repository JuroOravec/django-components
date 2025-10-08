# Vue comparison

## 1. Essentials

### 1.1 [Application](https://vuejs.org/guide/essentials/application.html)

#### 1.1.1 [Creating application](https://vuejs.org/guide/essentials/application#the-application-instance) - N/A
- Handled by Django/Alpine/HTMX
- TODO: initialize Alpine/HTMX instance for users automatically?

#### 1.1.2 [Mounting application](https://vuejs.org/guide/essentials/application#mounting-the-app) - N/A
- Handled by Django
- TODO: initialize Alpine/HTMX instance for users automatically?

#### 1.1.3 [App config](https://vuejs.org/guide/essentials/application#app-configurations) - N/A
- Handled by Django
- TODO: Pass Alpine/HTMX config to instance automatically?

#### 1.1.4 [Multiple application instances](https://vuejs.org/guide/essentials/application#multiple-application-instances) - N/A
- N/A in Django
- TODO: Check for Alpine/HTMX?

---

### 1.2 [Template syntax](https://vuejs.org/guide/essentials/template-syntax.html)

#### 1.2.1 [Text interpolation](https://vuejs.org/guide/essentials/template-syntax.html#text-interpolation) - ✅
- Done via Django Template Language (DTL) or Jinja

#### 1.2.2 [Raw HTML](https://vuejs.org/guide/essentials/template-syntax.html#raw-html) - ✅
- In DTL done via `{{ my_var|safe }}`

#### 1.2.3 [Attribute Bindings](https://vuejs.org/guide/essentials/template-syntax.html#attribute-bindings) - ✅
- Via AlpineJS
    - TODO: Could use some streamlining. Maybe tetraframework already does that?
- TODO: Is it possible via HTMX?

#### 1.2.4 [Same name shorthand](https://vuejs.org/guide/essentials/template-syntax.html#same-name-shorthand) - ❌
- Not implemented

#### 1.2.5 [Boolean attributes](https://vuejs.org/guide/essentials/template-syntax.html#boolean-attributes) - ❌
- NOTE: Needs to be implemented separately for django-components and separately for Alpine/HTML layer

#### 1.2.6 [Dynamically Binding Multiple Attributes](https://vuejs.org/guide/essentials/template-syntax.html#dynamically-binding-multiple-attributes) - ❌
- NOT supported in django-components
- TODO: Check Alpine / HTMX?

#### 1.2.7 [Using JavaScript Expressions](https://vuejs.org/guide/essentials/template-syntax.html#using-javascript-expressions) - ❌
- TODO: Allow python expressions in curly braces in Django?
- ✅ in AlpineJS
- TODO: Check HTMX

#### 1.2.8 [Calling Functions inside Expressions](https://vuejs.org/guide/essentials/template-syntax.html#calling-functions) - ✅
- ✅ in both Django and AlpineJS

#### 1.2.9 [Restricted Globals Access](https://vuejs.org/guide/essentials/template-syntax.html#restricted-globals-access) - ✅
- ✅ in Django
- N/A in Alpine

#### 1.2.10 [Directives](https://vuejs.org/guide/essentials/template-syntax.html#directives) - ❌
- N/A in Django
- TODO: Check in Alpine / HTMX?

#### 1.2.11 [Dynamic key name](https://vuejs.org/guide/essentials/template-syntax.html#dynamic-arguments) - ❌
- Not implemented in Django
- TODO: Check in Alpine / HTMX?

#### 1.2.12 [Modifiers](https://vuejs.org/guide/essentials/template-syntax.html#modifiers) - ❌
- N/A in Django
- ✅ in Alpine (events only)
- TODO: Check in HTMX?

---

### 1.3 [Reactivity Fundamentals](https://vuejs.org/guide/essentials/reactivity-fundamentals.html) - ❓❓

- N/A in Django/Jinja
- TODO: Check AlpineJS for which of these are / can be supported
- TODO: Check HTMX for which of these are / can be supported

---

### 1.4 [Computed Properties](https://vuejs.org/guide/essentials/computed.html) - ❓❓

- N/A in Django/Jinja
- TODO: Check AlpineJS for which of these are / can be supported
- TODO: Check HTMX for which of these are / can be supported

---

### 1.5 [Class and Style Bindings](https://vuejs.org/guide/essentials/class-and-style.html)

#### 1.5.1 [Binding classes to objects](https://vuejs.org/guide/essentials/class-and-style.html#binding-to-objects) - ❌
- TODO: Not implemented in Django
- TODO: Check in Alpine/HTMX?

#### 1.5.2 [Binding classes to arrays](https://vuejs.org/guide/essentials/class-and-style.html#binding-to-arrays) - ❌
- TODO: Not implemented in Django
- TODO: Check in Alpine/HTMX?

#### 1.5.3 [Merging classes](https://vuejs.org/guide/essentials/class-and-style.html#with-components) - ✅
- Implemented in Django via `html_attrs` tag
- TODO: Check in Alpine/HTMX?

#### 1.5.4 [Binding style to objects](https://vuejs.org/guide/essentials/class-and-style.html#binding-to-objects-1) - ❌
- TODO: Not implemented in Django
- TODO: Check in Alpine/HTMX?

#### 1.5.5 [Binding style to arrays](https://vuejs.org/guide/essentials/class-and-style.html#binding-to-arrays) - ❌
- TODO: Not implemented in Django
- TODO: Check in Alpine/HTMX?

#### 1.5.6 [Auto-adding vendos CSS prefixes](https://vuejs.org/guide/essentials/class-and-style.html#auto-prefixing) - ❌
- TODO: Not implemented in Django
- TODO: Check in Alpine/HTMX?

#### 1.5.7 [Multiple values to CSS auto-selects the supported one](https://vuejs.org/guide/essentials/class-and-style.html#multiple-values) - ❌
- TODO: Not implemented in Django
- TODO: Check in Alpine/HTMX?

---

### 1.6 [Conditional Rendering](https://vuejs.org/guide/essentials/conditional.html)

#### 1.6.1 [v-if, v-else-if, v-else](https://vuejs.org/guide/essentials/conditional.html#v-if) - ✅
- Implemented via Django/Jinja
- Implemented in Alpine
- TODO: Check in HTMX?

#### 1.6.2 [v-if with `<template>`](https://vuejs.org/guide/essentials/conditional.html#v-if-on-template) - N/A
- Django doesn't need that, as `if` tag is defined standalone

#### 1.6.3 [v-show](https://vuejs.org/guide/essentials/conditional.html#v-show) - ✅
- N/A for Django/Jinja
- Implemented in Alpine
- TODO: Check in HTMX?

---

### 1.7 [List Rendering](https://vuejs.org/guide/essentials/list.html)

#### 1.7.1 [v-for](https://vuejs.org/guide/essentials/list.html#v-for) - ✅
- Implemented via Django/Jinja
- Implemented in Alpine
- TODO: Check in HTMX?

#### 1.7.2 [Loop index with v-for](https://vuejs.org/guide/essentials/list.html#v-for) - ❌
- TODO: Check in Django/Jinja, Alpine, HTMX?

#### 1.7.3 [Nested with v-for](https://vuejs.org/guide/essentials/list.html#v-for) - ✅
- Implemented via Django/Jinja
- TODO: Check in Alpine, HTMX?

#### 1.7.4 [v-for with an Object](https://vuejs.org/guide/essentials/list.html#v-for) - ❌
- TODO: Check in Django/Jinja, Alpine, HTMX?

#### 1.7.5 [Loop index with v-for with an Object](https://vuejs.org/guide/essentials/list.html#v-for) - ❌
- TODO: Check in Django/Jinja, Alpine, HTMX?

#### 1.7.6 [v-for with a Range](https://vuejs.org/guide/essentials/list.html#v-for) - ❌
- TODO: Check in Django/Jinja, Alpine, HTMX?

#### 1.7.7 [v-for on `<template>`](https://vuejs.org/guide/essentials/list.html#v-for-on-template) - N/A
- Django doesn't need that, as `for` tag is defined standalone

#### 1.7.8 [Maintaining State with `:key`](https://vuejs.org/guide/essentials/list.html#maintaining-state-with-key) - ❌
- N/A in Django/Jinja
- TODO: Check in Alpine, HTMX?

#### 1.7.8 [v-for with a Component](https://vuejs.org/guide/essentials/list.html#v-for-with-a-component) - N/A
- N/A in Django/Jinja
- TODO: Check in Alpine, HTMX?

#### 1.7.9 [Array Change Detection](https://vuejs.org/guide/essentials/list.html#array-change-detection) - N/A
- N/A in Django/Jinja
- TODO: Check in Alpine, HTMX?

---

### 1.8 [Event Handling](https://vuejs.org/guide/essentials/event-handling.html) - ❓❓

- N/A in Django/Jinja
- TODO: Check AlpineJS for which of these are / can be supported
- TODO: Check HTMX for which of these are / can be supported

- TODO - Look into triggering server python endpoints on HTML events?
    - Or compiling python to Webassembly to run client-side python on events?

---

### 1.9 [Form Input Bindings](https://vuejs.org/guide/essentials/forms.html) - ❓❓

- N/A in Django/Jinja
- TODO: Check AlpineJS for which of these are / can be supported
- TODO: Check HTMX for which of these are / can be supported

- TODO - Look into triggering server python endpoints on HTML events?
    - Or compiling python to Webassembly to run client-side python on events?

---

### 1.10 [Watchers](https://vuejs.org/guide/essentials/watchers.html) - ❓❓

- N/A in Django/Jinja
- TODO: Check AlpineJS/HTMX

---

### 1.11 [Template Refs](https://vuejs.org/guide/essentials/template-refs.html) - ❓❓

- N/A in Django/Jinja
- TODO: Check AlpineJS/HTMX

---

### 1.12 [Components Basics](https://vuejs.org/guide/essentials/component-basics.html)

#### 1.12.1 [Defining a Component](https://vuejs.org/guide/essentials/component-basics.html) - ✅
- Implemented in Django/Jinja
- Implemented in Alpine
- TODO: Check in HTMX?

- TODO: Automatically create Alpine components, so Alpine shares event boundary with Django?

#### 1.12.2 [Importing and registering Components](https://vuejs.org/guide/essentials/component-basics.html#using-a-component) - ✅
- Implemented in Django/Jinja

#### 1.12.3 [Passing Props](https://vuejs.org/guide/essentials/component-basics.html#passing-props) - ✅
- Implemented in Django/Jinja
- TODO: Check in Alpine/HTMX?

#### 1.12.4 [Typing props](https://vuejs.org/guide/typescript/composition-api.html#typing-component-props) - ❌
- NOT implemented in Django
- TODO: Check in Alpine/HTMX?

#### 1.12.5 [Listening to Events](https://vuejs.org/guide/essentials/component-basics.html#listening-to-events) - ✅
- Similar approach possible with `{% component "my_comp" attrs:@click="..." %}`

#### 1.12.6 [Typing events](https://vuejs.org/api/sfc-script-setup.html#defineprops-defineemits) - ❌
- N/A for Django
- TODO: Check in Alpine/HTMX?

#### 1.12.7 [Content Distribution with Slots](https://vuejs.org/guide/essentials/component-basics.html#content-distribution-with-slots) - ✅
- Implemented with our slots in Django
- N/A for Alpine/HTMX?

#### 1.12.8 [Dynamic Components](https://vuejs.org/guide/essentials/component-basics.html#dynamic-components) - ✅
- Possible in Django by specifying component name as variable
- TODO: Check for Alpine/HTMX?

#### 1.12.9 [Self Closing Tags](https://vuejs.org/guide/essentials/component-basics.html#dynamic-components) - ❌
- Possible for Django with "inlined" components
- TODO: Implement for HTML tags?

#### 1.12.10 [Element Placement Restrictions](https://vuejs.org/guide/essentials/component-basics.html#element-placement-restrictions) - ❓❓
- TODO: Don't know if applicable

---

## 2. Components In-Depth

# TODO CONTINUE HERE - https://vuejs.org/guide/components/registration.html

# TODO2 - Write a post on growni, searching for someone to manage fundraising for this project
    - break down:
        - What has been done so far / Why:
            - Compat with Vue
            - Unify community - django-components has feature parity with:
                - django-slippers
                - django-web-components
                - jinjax
                - tetra-framework
                - unicorn
            - Works with Django, but also standalone (#TODO)
            - 1000 github stars and 250k monthly downloads
                - NOTE: Comparison with Vue
                    - Vue - 18.3M monthly downloads (4.77M weekly) and 45k stars
                    - DC - 0.25M monthly downloads and 0.95k stars
                    - So currently DC ~2% (1/50th) of size of Vue
                    - ---
                    - [JS vs Python (65% vs 45%)](https://survey.stackoverflow.co/2023/#programming-scripting-and-markup-languages)
                    - [Vue vs Django (17% vs 11%)](https://survey.stackoverflow.co/2023/#web-frameworks-and-technologies)
                    - ---
                    - [Vue represents ~22% of Vue/React/Angular userbase](https://survey.stackoverflow.co/2023/#web-frameworks-and-technologies)
                    - [Django ~15.2M monthly downloads](https://pypistats.org/packages/django)
                    - Hence, DC could represent ~22% of Django userbase, which is 3.3M monthly downloads.
                    - Hence, DC could grow to about 13.4 times, or 3.3M monthly downloads and 12.7k stars
        - What we want funding for:
            - "Vuetify" components library
                - Sort them in order of priority, possibly
                - Claim that to an average company, it would save hundreds of hours!
                    - Estimate this number somehow, e.h. by counting the high-use componenents
                        and then using some multiplier, like 30 hrs per component.
            - We believe the DC community could grow over 13x
            - Features to improve the parity with Vue
        - Estimate time required for developing the "vuetify" library
            - E.g. 30 hrs / component, plus other unifying features, like "theme", etc.
            - Include roadmap
        - Estimate feature milestones, and the financial requirements for them, based on the above
