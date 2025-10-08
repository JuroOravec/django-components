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
