# TODO Vue compat

Based on [API reference](https://vuejs.org/api) based on v3.5.12.

### Progress

| <span></span>         | <span></span> |
| --------------------- | ------------- |
| Implemented (✅ / 🟠) | 0             |
| Won't implement (🚫)  | 26            |
| <b>Total:</b>         | 206           |

### Legend:
- ✅ - Implemented. Same behavior as Vue.
- 🟠 - Implemented. Differs from Vue.
- ❌ - Not implemented. Planned.
- 🚫 - Won't implement. Not compatible.

## Global API

### Application

- 🚫 createApp()
- 🚫 createSSRApp()
- 🚫 app.mount()
- 🚫 app.unmount()
- [ ] app.onUnmount()
- [ ] app.component()
- [ ] app.directive()
- [ ] app.use()
- [ ] app.mixin()
- [ ] app.provide()
- [ ] app.runWithContext()
- [ ] app.version
- [ ] app.config
- [ ] app.config.errorHandler
- [ ] app.config.warnHandler
- [ ] app.config.performance
- [ ] app.config.compilerOptions
- [ ] app.config.globalProperties
- [ ] app.config.optionMergeStrategies
- [ ] app.config.idPrefix
- [ ] app.config.throwUnhandledErrorInProduction

### General

- [ ] version
- [ ] nextTick()
- [ ] defineComponent()
- [ ] defineAsyncComponent()


## Composition API

### setup()

- [ ] Basic Usage
- [ ] Accessing Props
- [ ] Setup Context
- [ ] Usage with Render Functions

### Reactivity: Core

- [ ] ref()
- [ ] computed()
- [ ] reactive()
- [ ] readonly()
- [ ] watchEffect()
- [ ] watchPostEffect()
- [ ] watchSyncEffect()
- [ ] watch()
- [ ] onWatcherCleanup()

### Reactivity: Utilities

- [ ] isRef()
- [ ] unref()
- [ ] toRef()
- [ ] toValue()
- [ ] toRefs()
- [ ] isProxy()
- [ ] isReactive()
- [ ] isReadonly()

### Reactivity: Advanced

- [ ] shallowRef()
- [ ] triggerRef()
- [ ] customRef()
- [ ] shallowReactive()
- [ ] shallowReadonly()
- [ ] toRaw()
- [ ] markRaw()
- [ ] effectScope()
- [ ] getCurrentScope()
- [ ] onScopeDispose()

### Lifecycle Hooks

- [ ] onMounted()
- [ ] onUpdated()
- [ ] onUnmounted()
- [ ] onBeforeMount()
- [ ] onBeforeUpdate()
- [ ] onBeforeUnmount()
- [ ] onErrorCaptured()
- [ ] onRenderTracked()
- [ ] onRenderTriggered()
- [ ] onActivated()
- [ ] onDeactivated()
- [ ] onServerPrefetch()

### Dependency Injection

- [ ] provide()
- [ ] inject()
- [ ] hasInjectionContext()

### Helpers

- [ ] useAttrs()
- [ ] useSlots()
- [ ] useModel()
- [ ] useTemplateRef()
- [ ] useId()

## Options API

### Options: State

- [ ] data
- [ ] props
- [ ] computed
- [ ] methods
- [ ] watch
- [ ] emits
- [ ] expose

### Options: Rendering

- [ ] template
- [ ] render
- [ ] compilerOptions
- [ ] slots

### Options: Lifecycle

- [ ] beforeCreate
- [ ] created
- [ ] beforeMount
- [ ] mounted
- [ ] beforeUpdate
- [ ] updated
- [ ] beforeUnmount
- [ ] unmounted
- [ ] errorCaptured
- [ ] renderTracked
- [ ] renderTriggered
- [ ] activated
- [ ] deactivated
- [ ] serverPrefetch

### Options: Composition

- [ ] provide
- [ ] inject
- [ ] mixins
- [ ] extends

### Options: Misc

- [ ] name
- [ ] inheritAttrs
- [ ] components
- [ ] directives

### Component Instance

- [ ] $data
- [ ] $props
- [ ] $el
- [ ] $options
- [ ] $parent
- [ ] $root
- [ ] $slots
- [ ] $refs
- [ ] $attrs
- [ ] $watch()
- [ ] $emit()
- [ ] $forceUpdate()
- [ ] $nextTick()

## Built-ins

### Directives

- [ ] v-text
- [ ] v-html
- [ ] v-show
- [ ] v-if
- [ ] v-else
- [ ] v-else-if
- [ ] v-for
- [ ] v-on
- [ ] v-bind
- [ ] v-model
- [ ] v-slot
- [ ] v-pre
- [ ] v-once
- [ ] v-memo
- [ ] v-cloak

### Components

- [ ] `<Transition>`
- [ ] `<TransitionGroup>`
- [ ] `<KeepAlive>`
- [ ] `<Teleport>`
- [ ] `<Suspense>`

### Special Elements

- [ ] `<component>`
- [ ] `<slot>`
- [ ] `<template>`

### Special Attributes

- [ ] key
- [ ] ref
- [ ] is


## Single-File Component

### Syntax Specification

- [ ] Overview
- [ ] Language Blocks
- [ ] Automatic Name Inference
- [ ] Pre-Processors
- [ ] src Imports
- [ ] Comments

### `<script setup>`

- [ ] Basic Syntax
- [ ] Reactivity
- [ ] Using Components
- [ ] Using Custom Directives
- [ ] defineProps() & defineEmits()
- [ ] defineModel()
- [ ] defineExpose()
- [ ] defineOptions()
- [ ] defineSlots()
- [ ] useSlots() & useAttrs()
- [ ] Usage alongside normal `<script>`
- [ ] Top-level await
- [ ] Import Statements
- [ ] Generics
- [ ] Restrictions

### CSS Features

- [ ] Scoped CSS
- [ ] CSS Modules
- [ ] v-bind() in CSS


## Advanced APIs

### Custom Elements

- 🚫 [defineCustomElement()](https://vuejs.org/api/custom-elements.html#definecustomelement)
- 🚫 [useHost()](https://vuejs.org/api/custom-elements.html#usehost)
- 🚫 [useShadowRoot()](https://vuejs.org/api/custom-elements.html#useshadowroot)
- 🚫 [this.$host](https://vuejs.org/api/custom-elements.html#this-host)

### Render Function

- 🚫 [h()](https://vuejs.org/api/render-function.html#h)
- [ ] [mergeProps()](https://vuejs.org/api/render-function.html#mergeprops)
- 🚫 [cloneVNode()](https://vuejs.org/api/render-function.html#clonevnode)
- 🚫 [isVNode()](https://vuejs.org/api/render-function.html#isvnode)
- 🚫 [resolveComponent()](https://vuejs.org/api/render-function.html#resolvecomponent)
- 🚫 [resolveDirective()](https://vuejs.org/api/render-function.html#resolvedirective)
- 🚫 [withDirectives()](https://vuejs.org/api/render-function.html#withdirectives)
- 🚫 [withModifiers()](https://vuejs.org/api/render-function.html#withmodifiers)

### Server-Side Rendering

- [ ] [renderToString()](https://vuejs.org/api/ssr.html#rendertostring)
    - NOTE: Use `Component.render()` instead
- 🚫 [renderToNodeStream()](https://vuejs.org/api/ssr.html#rendertonodestream)
- 🚫 [pipeToNodeWritable()](https://vuejs.org/api/ssr.html#pipetonodewritable)
- 🚫 [renderToWebStream()](https://vuejs.org/api/ssr.html#rendertowebstream)
- 🚫 [pipeToWebWritable()](https://vuejs.org/api/ssr.html#pipetowebwritable)
- 🚫 [renderToSimpleStream()](https://vuejs.org/api/ssr.html#rendertosimplestream)
- 🚫 [seSSRContext()](https://vuejs.org/api/ssr.html#usessrcontext)
- 🚫 [data-allow-mismatch](https://vuejs.org/api/ssr.html#data-allow-mismatch)

### TypeScript Utility Types

- ❌ [`PropType<T>`](https://vuejs.org/api/utility-types.html#proptype-t)
- ❌ [`MaybeRef<T>`](https://vuejs.org/api/utility-types.html#mayberef)
- ❌ [`MaybeRefOrGetter<T>`](https://vuejs.org/api/utility-types.html#maybereforgetter)
- ❌ [`ExtractPropTypes<T>`](https://vuejs.org/api/utility-types.html#extractproptypes)
- ❌ [`ExtractPublicPropTypes<T>`](https://vuejs.org/api/utility-types.html#extractpublicproptypes)
- ❌ [`ComponentCustomProperties`](https://vuejs.org/api/utility-types.html#componentcustomproperties)
- ❌ [`ComponentCustomOptions`](https://vuejs.org/api/utility-types.html#componentcustomoptions)
- ❌ [`ComponentCustomProps`](https://vuejs.org/api/utility-types.html#componentcustomprops)
- ❌ [`CSSProperties`](https://vuejs.org/api/utility-types.html#cssproperties)

### Custom Renderer

- 🚫 [createRenderer()](https://vuejs.org/api/custom-renderer.html#createrenderer)

### Compile-Time Flags

- 🚫 [`__VUE_OPTIONS_API__`](https://vuejs.org/api/compile-time-flags.html#VUE_OPTIONS_API)
- 🚫 [`__VUE_PROD_DEVTOOLS__`](https://vuejs.org/api/compile-time-flags.html#VUE_PROD_DEVTOOLS)
- 🚫 [`__VUE_PROD_HYDRATION_MISMATCH_DETAILS__`](https://vuejs.org/api/compile-time-flags.html#VUE_PROD_HYDRATION_MISMATCH_DETAILS)
- [ ] [Configuration Guides](https://vuejs.org/api/compile-time-flags.html#configuration-guides)
