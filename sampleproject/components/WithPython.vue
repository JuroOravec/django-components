<server lang="py">
from django_vue.component import VueComponent

class WithPython(VueComponent):
    def get_context_data(self):
        return {"classes": "abc"}

    def get(self, request, *args, **kwargs):
        context = {"name": request.GET.get("name", "")}
        return self.render_to_response(context=context)

</server>

<script lang="ts">
// TODO
const defineComponent = (options) => options;

// TODO
console.log("INSIDE WITH_PYTHON");

export default defineComponent({
  name: "WithPython",
  props: {
    classes: {
      type: String,
      default: ''
    }
  },
  setup() {
    const onClick = () => {
      debugger;
      this.$emit('click');
    }
    return { onClick };
  },
  // TODO: Support Options syntax
  // methods: {
  //   onClick() {
  //       this.$emit('click');
  //   }
  // },
});
</script>

<!-- TODO: Support PUG -->
<!-- TODO: Support MARKDOWN -->
<template>
  <button @click="onClick" :class="classes">
    <slot />
  </button>
</template>

<!-- TODO: Support other languages -->
<!-- TODO: Support SCOPED CSS -->
<!-- TODO: Support CSS module (CSS-in-JS) -->
<style lang="css">
button {
  background-color: #4CAF50;
  border: none;
  color: white;
  padding: 15px 32px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 16px;
  margin: 4px 2px;
  cursor: pointer;
}
</style>
