<!-- TODO - Support TS -->
<!-- TODO - `script setup` will NOT be supported -->
<script lang="ts">
export default defineComponent({
  props: {
    classes: {
      type: String,
      default: ''
    }
  },
  methods: {
    onClick() {
        this.$emit('click');
    }
  },
  setup() {
      return {}
  },
});
</script>

<!-- TODO: Support PUG and MARKDOWN -->
<template>
  <button @click="onClick" :class="classes">
    <slot></slot>
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
