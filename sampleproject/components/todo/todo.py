from typing import Any, TypedDict

from django_components import Component, register, types


class TodoKwargs(TypedDict):
    pass


class TodoData(TypedDict):
    one: str
    self: "TodoComp"


TodoComp = Component[Any, TodoKwargs, Any, TodoData, Any, Any]

counter = 0
colors = ["blue", "green"]


@register("todo")
class Todo(TodoComp):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    template_file = "todo/todo.html"

    def get_context_data(self, *args: Any, **kwargs: Any) -> TodoData:
        return {
            "one": "abc ",
            "self": self,
        }

    def js_data(self):
        return {"1": "2"}

    def css_data(self):
        # self.input.kwargs['one']
        # self.input.kwargs['self'].input.kwargs["self"].input.kwargs
        # self.input.kwargs['self'].input

        global counter
        counter += 1
        return {"color": colors[counter % 2]}

    # js_lang = "ts"
    js: types.ts = """
        import { hi, whatsApp } from "./rando/rando";

        // const x: string = "123";

        // import { abc } from "def";
        // Comment
        // import { xyz } from "zzz-shimimi";

        console.log({ $id, $data, $name, $els });

        // Define instance variables
        const items = [];

        // Set up event listeners for child events
        $on("addItem", (item) => {
            hi("abc");
            whatsApp("Joe!");
          items.push(item);
        });

        const displayText = () => {
          for (const el of $els) {
            const summaryEl = el.querySelector('.summary');
            if (!summaryEl) continue;

            summaryEl.textContent = `${items.length} items!`;
          }
        };

        // Run init code
        // TODO
        for (const el of $els) {
          const itemEls = el.querySelectorAll('.my-item');
          for (const itemEl of [...itemEls]) {
            itemEl.textContent;
          }
        }
    """

    css_scoped = True
    css: types.sass = """
        /* .todo-item {
            background: var(--color);
        } */
        me {
            background: var(--color);
        }
    """


@register("my_child")
class MyChild(Component):
    js: types.js = """
        // Emit event to the parent
        const itemsCount = $data.items.length;
        $emit('updateItemsCount', itemsCount);
        
        // Could pass multiple args
        $emit('updateItemsCount', itemsCount, $els, 123);
    """


@register("my_parent")
class MyParent(Component):
    html: types.django_html = """
        <div>
          {# In parent component, we'd listen to the event with @eventName. #}
          {# The right-hand side is the name of the handler for this event #}
          {% component "my_comp" @updateItemsCount="handleItemsCount" / %}
        </div>
    """

    js: types.js = """
        let count = 0; // Initial count

        // We'd register the handlers with $on.
        const stopOn = $on("handleItemsCount", (newCount) => {
            count = newCount
        });

        // Multiple handlers would be possible
        $on("handleItemsCount", (newCount) => {
            count = newCount
        });

        // Listeners return functions that stop the listening when called
        stopOn();
    """


@register("workround_child")
class WorkaroundChild(Component):
    js: types.js = """
        let parentData = null;

        const updateParentData = (newData) => {
            parentData = newData;
        }

        // Emit event with the callback to the parent
        $emit('requestData', updateParentData);
    """


@register("workaround_parent")
class WorkaroundParent(Component):
    html: types.django_html = """
        <div>
          {# In parent component, we'd listen to the event with @eventName. #}
          {# The right-hand side is the name of the handler for this event #}
          {% component "my_comp" @requestData="handleRequestData" / %}
        </div>
    """

    js: types.js = """
        let count = 0; // Initial count

        // Send the data to the child component
        const stopOn = $on("handleRequestData", (sendData) => {
            sendData(count);
        });
    """


@register("todo2")
class Todo2(TodoComp):
    template_name = "todo/todo.html"
    js_file = "todo.js"


@register("todo3")
class Todo3(TodoComp):
    # Templates inside `[your apps]/components` dir and `[project root]/components` dir
    # will be automatically found.
    template_name = "todo/todo.html"

    def get_context_data(self, *args: Any, **kwargs: Any) -> TodoData:
        return {
            "one": "abc ",
            "self": self,
        }

    def js_data(self):
        return {"1": "2"}

    def css_data(self):
        # self.input.kwargs['one']
        # self.input.kwargs['self'].input.kwargs["self"].input.kwargs
        # self.input.kwargs['self'].input

        global counter
        counter += 1
        return {"color": colors[counter % 2]}

    js: types.js = """
        import { hi, whatsApp } from "./rando/rando";

        $on("addItem222", (item) => {
            hi("abc222");
            whatsApp("Joe!222");
          items.push(item);
        });

        console.log({ $id, $data, $name, $els });

        // Define instance variables
        const items = [];

        // Set up event listeners for events coming from child components
        $on("addItem", (item) => {
          items.push(item);
        });

        const displayText = () => {
          for (const el of $els) {
            const summaryEl = el.querySelector('.summary');
            if (!summaryEl) continue;

            summaryEl.textContent = `${items.length} items!`;
          }
        };

        // Run init code
        for (const el of $els) {
          const itemEls = el.querySelectorAll('.my-item');
          for (const itemEl of itemEls) {
            itemEl.addEventListener("click", (ev) => {
                const newItem = { id: ev.target.id };
                items.push(newItem);
            });
          } 
        }

        return {
            abc: "abc",
        };
    """
    css_scoped = True
    css: types.css = """
        /* .todo-item {
            background: var(--color);
        } */
        me {
            background: var(--color);
        }
    """
