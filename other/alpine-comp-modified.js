// MODIFIED alpine-composition

/*!
 * alpine-composition v0.1.29
 * By Juro Oravec
 * Released under the MIT License.
 */

(function (global, factory) {
  typeof exports === "object" && typeof module !== "undefined"
    ? factory(exports, require("alpine-reactivity"))
    : typeof define === "function" && define.amd
    ? define(["exports", "alpine-reactivity"], factory)
    : ((global =
        typeof globalThis !== "undefined" ? globalThis : global || self),
      factory((global.AlpineComposition = {}), global.AlpineReactivity));
})(this, function (exports, alpineReactivity) {
  "use strict";

  /******************************************************************************
    Copyright (c) Microsoft Corporation.

    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
    REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
    INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
    LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
    OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
    PERFORMANCE OF THIS SOFTWARE.
    ***************************************************************************** */
  /* global Reflect, Promise, SuppressedError, Symbol */

  var __assign = function () {
    __assign =
      Object.assign ||
      function __assign(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
          s = arguments[i];
          for (var p in s)
            if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
        }
        return t;
      };
    return __assign.apply(this, arguments);
  };
  function __spreadArray(to, from, pack) {
    if (pack || arguments.length === 2)
      for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
          if (!ar) ar = Array.prototype.slice.call(from, 0, i);
          ar[i] = from[i];
        }
      }
    return to.concat(ar || Array.prototype.slice.call(from));
  }
  typeof SuppressedError === "function"
    ? SuppressedError
    : function (error, suppressed, message) {
        var e = new Error(message);
        return (
          (e.name = "SuppressedError"),
          (e.error = error),
          (e.suppressed = suppressed),
          e
        );
      };

  // Helper functions taken from @vue/shared
  // See https://github.com/vuejs/core/blob/91112520427ff55941a1c759d7d60a0811ff4a61/packages/shared/src/general.ts#L105
  var cacheStringFunction = function (fn) {
    var cache = Object.create(null);
    return function (str) {
      var hit = cache[str];
      return hit || (cache[str] = fn(str));
    };
  };
  var capitalize = cacheStringFunction(function (str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  });
  var extend = Object.assign;
  var isArray = Array.isArray;
  var isFunction = function (val) {
    return typeof val === "function";
  };
  var isObject = function (val) {
    return val !== null && typeof val === "object";
  };
  var isPromise = function (val) {
    return (
      (isObject(val) || isFunction(val)) &&
      isFunction(val.then) &&
      isFunction(val.catch)
    );
  };
  var toHandlerKey = cacheStringFunction(function (str) {
    var s = str ? "on".concat(capitalize(str)) : "";
    return s;
  });
  var isInstanceOf = function (propTypes, value) {
    return propTypes.some(function (propType) {
      return (
        value instanceof propType ||
        // For primitives like numbers, strings, etc, when we want to check against
        // their classes (Number, String), then the primitives ARE NOT actual instances.
        // Hence we have to check by `typeof`.
        propType.name.toLowerCase() == typeof value
      );
    });
  };
  function mergeProps() {
    var args = [];
    for (var _i = 0; _i < arguments.length; _i++) {
      args[_i] = arguments[_i];
    }
    var ret = {};
    for (var i = 0; i < args.length; i++) {
      var toMerge = args[i];
      for (var key in toMerge) {
        if (key === "class") {
          if (ret.class !== toMerge.class) {
            ret.class = normalizeClass([ret.class, toMerge.class]);
          }
        } else if (key === "style") {
          ret.style = normalizeStyle([ret.style, toMerge.style]);
        } else if (isOn(key)) {
          var existing = ret[key];
          var incoming = toMerge[key];
          if (
            incoming &&
            existing !== incoming &&
            !(isArray(existing) && existing.includes(incoming))
          ) {
            ret[key] = existing ? [].concat(existing, incoming) : incoming;
          }
        } else if (key !== "") {
          ret[key] = toMerge[key];
        }
      }
    }
    return ret;
  }
  function normalizeClass(value) {
    var res = "";
    if (isString(value)) {
      res = value;
    } else if (isArray(value)) {
      for (var i = 0; i < value.length; i++) {
        var normalized = normalizeClass(value[i]);
        if (normalized) {
          res += normalized + " ";
        }
      }
    } else if (isObject(value)) {
      for (var name_1 in value) {
        if (value[name_1]) {
          res += name_1 + " ";
        }
      }
    }
    return res.trim();
  }
  function normalizeStyle(value) {
    if (isArray(value)) {
      var res = {};
      for (var i = 0; i < value.length; i++) {
        var item = value[i];
        var normalized = isString(item)
          ? parseStringStyle(item)
          : normalizeStyle(item);
        if (normalized) {
          for (var key in normalized) {
            res[key] = normalized[key];
          }
        }
      }
      return res;
    } else if (isString(value) || isObject(value)) {
      return value;
    } else {
      return undefined;
    }
  }
  var listDelimiterRE = /;(?![^(]*\))/g;
  var propertyDelimiterRE = /:([^]+)/;
  var styleCommentRE = /\/\*[^]*?\*\//g;
  function parseStringStyle(cssText) {
    var ret = {};
    cssText
      .replace(styleCommentRE, "")
      .split(listDelimiterRE)
      .forEach(function (item) {
        if (item) {
          var tmp = item.split(propertyDelimiterRE);
          tmp.length > 1 && (ret[tmp[0].trim()] = tmp[1].trim());
        }
      });
    return ret;
  }
  var isString = function (val) {
    return typeof val === "string";
  };
  var onRE = /^on[^a-z]/;
  var isOn = function (key) {
    return onRE.test(key);
  };

  function callWithErrorHandling(compName, fn, args) {
    try {
      return args ? fn.apply(void 0, args) : fn();
    } catch (err) {
      var errMsg = err.message;
      if (errMsg != null) {
        err.message = "[alpine-composition] "
          .concat(compName, ": ")
          .concat(errMsg);
      }
      logError(err);
    }
  }
  function callWithAsyncErrorHandling(compName, fn, args) {
    if (isFunction(fn)) {
      var res = callWithErrorHandling(compName, fn, args);
      if (res && isPromise(res)) {
        res.catch(function (err) {
          logError(err);
        });
      }
      return res;
    }
    if (isArray(fn)) {
      var values = [];
      for (var i = 0; i < fn.length; i++) {
        values.push(callWithAsyncErrorHandling(compName, fn[i], args));
      }
      return values;
    } else {
      console.warn(
        "[alpine-composition] "
          .concat(
            compName,
            ": Invalid value type passed to callWithAsyncErrorHandling(): "
          )
          .concat(typeof fn)
      );
    }
  }
  function logError(err) {
    // recover in prod to reduce the impact on end-user
    console.error(err);
  }

  function emit(instance, event) {
    var rawArgs = [];
    for (var _i = 2; _i < arguments.length; _i++) {
      rawArgs[_i - 2] = arguments[_i];
    }
    var name = instance.$name; // OK
    var props = instance.$props; // OK
    var emits = instance.$emitsOptions; // OK
    if (!(event in emits)) {
      if (!props || !hasEvent(props, event)) {
        console.warn(
          "[alpine-composition] "
            .concat(name, ': Component emitted event "')
            .concat(event, '" but it is neither ') +
            'declared in the emits option nor as an "'.concat(
              toHandlerKey(event),
              '" prop.'
            )
        );
      }
    } else {
      var validator = emits[event];
      if (isFunction(validator)) {
        var isValid = validator.apply(void 0, rawArgs);
        if (!isValid) {
          console.warn(
            "[alpine-composition] "
              .concat(
                name,
                ': Invalid event arguments: event validation failed for event "'
              )
              .concat(event, '".')
          );
        }
      }
    }
    var handlerName = toHandlerKey(event);
    var handler = props[handlerName];
    if (handler) {
      callWithAsyncErrorHandling(name, handler, rawArgs);
    }
    var onceHandler = props[handlerName + "Once"];
    if (onceHandler) {
      // @ts-expect-error
      var emitted = instance._emitted || (instance._emitted = {}); // OK
      if (emitted[handlerName]) {
        return;
      }
      emitted[handlerName] = true;
      callWithAsyncErrorHandling(name, onceHandler, rawArgs);
    }
  }
  function normalizeEmitsOptions(emits) {
    var normalized = {};
    if (!emits) {
      return normalized;
    }
    if (isArray(emits)) {
      emits.forEach(function (key) {
        return (normalized[key] = null);
      });
    } else {
      extend(normalized, emits);
    }
    return normalized;
  }
  // NOTE: This is for checking event handling PROPS, like `onClick`.
  // It is different from x-on https://alpinejs.dev/directives/on
  function handlerKeys(name) {
    var handlerName = toHandlerKey(name);
    return [handlerName, "".concat(handlerName, "Once")];
  }
  // NOTE: This is for checking event handling PROPS, like `onClick`.
  // It is different from x-on https://alpinejs.dev/directives/on
  function hasEvent(props, name) {
    var handlerNames = handlerKeys(name);
    return handlerNames.some(function (name) {
      return props[name];
    });
  }

  // TODO
  // TODO
  // TODO
  var createReactivityAPI = function (instance, _self) {
    var reactives = [];
    var effects = [];
    var watches = [];
    var onBeforeUpdatedCallbacks = [];
    var onUpdatedCallbacks = [];

    // TODO - This second argument is so that we can more efficiently access fields
    //        to which we already have access and which don't need to go through magics / proxies.
    if (!_self) _self = instance;

    const onReactiveChange = () => {
      // So if we got here, some values changed, so trigger the hooks
      onBeforeUpdatedCallbacks.forEach(function (cb) {
        return cb();
      });
      instance.$nextTick(function () {
        // OK
        onUpdatedCallbacks.forEach(function (cb) {
          return cb();
        });
      });
    };

    let isSettingUpPropsWatcher = true;
    const stopPropsWatcher = alpineReactivity.watchEffect(function () {
      // Touch all props
      for (
        var _a = 0, _b = Object.keys(_self.$props); // OK
        _a < _b.length;
        _a++
      ) {
        var propKey = _b[_a];
        // "touch" each variable
        _self.$props[propKey]; // OK
        /* eslint-disable-line no-unused-expressions */
      }
      if (!isSettingUpPropsWatcher) {
        // Since we touched ALL props, when this function runs next time,
        // it will be because the values actually changed.
        onReactiveChange();
      }
    });
    watches.push(stopPropsWatcher);
    isSettingUpPropsWatcher = false;

    var trackRef = function (r) {
      let isSettingUpRefWatcher = true;
      const stopRefWatcher = alpineReactivity.watchEffect(function () {
        // "touch" the reactive so it's tracked
        alpineReactivity.unref(r);
        if (!isSettingUpRefWatcher) {
          // Callback to trigger onBeforeUpdated and onUpdated when any refs change.
          onReactiveChange();
        }
      });
      isSettingUpRefWatcher = false;

      reactives.push(r);
      watches.push(stopRefWatcher);
    };

    // Cleanup
    _self.$onBeforeUnmount(function () {
      // OK
      // Wait a tick, so normal execution of AlpineJS' `destroy` hook proceeds
      // normally (assuming it's synchronous).
      setTimeout(function () {
        effects.forEach(function (eff) {
          return alpineReactivity.stop(eff);
        });
        watches.forEach(function (stopWatch) {
          return stopWatch();
        });
      });
    });

    const returnObject = {
      computed: function (getterOrOptions) {
        var onlyGetter = isFunction(getterOrOptions);
        var val = onlyGetter
          ? alpineReactivity.computed(getterOrOptions)
          : alpineReactivity.writableComputed(getterOrOptions);
        trackRef(val);
        // @ts-expect-error
        effects.push(val.effect);
        return val;
      },
      inject: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        // @ts-expect-error
        return instance.$inject.apply(instance, args); // OK (?)
      },
      // @ts-expect-error
      isRef: function (r) {
        var args = [];
        for (var _i = 1; _i < arguments.length; _i++) {
          args[_i - 1] = arguments[_i];
        }
        // @ts-expect-error
        return alpineReactivity.isRef.apply(
          void 0,
          __spreadArray([r], args, false)
        );
      },
      // NOTE: mergeProps does NOT use any reactivity API
      mergeProps: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        return mergeProps.apply(void 0, args);
      },
      nextTick: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        return instance.$nextTick.apply(instance, args); // OK
      },
      // @ts-expect-error
      provide: function (key, val) {
        return instance.$provide(key, val); // OK (?)
      },
      reactive: function (val) {
        var reactiveVal = alpineReactivity.reactive(val);
        var refs = alpineReactivity.toRefs(reactiveVal);
        Object.values(refs).forEach(function (refVal) {
          trackRef(refVal);
        });
        return reactiveVal;
      },
      readonly: function (val) {
        return alpineReactivity.readonly(val);
      },
      ref: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        var val = alpineReactivity.ref.apply(void 0, args);
        trackRef(val);
        return val;
      },
      shallowRef: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        var val = alpineReactivity.shallowRef.apply(void 0, args);
        trackRef(val);
        return val;
      },
      toRaw: function (val) {
        return alpineReactivity.toRaw(val);
      },
      toRef: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        // @ts-expect-error
        var val = alpineReactivity.toRef.apply(void 0, args);
        trackRef(val);
        return val;
      },
      toRefs: function (val) {
        var refs = alpineReactivity.toRefs(val);
        Object.values(refs).forEach(function (refVal) {
          trackRef(refVal);
        });
        return refs;
      },
      unref: function (val) {
        return alpineReactivity.unref(val);
      },
      watch: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        // @ts-expect-error
        var stopHandle = alpineReactivity.watch.apply(void 0, args);
        watches.push(stopHandle);
        return stopHandle;
      },
      watchEffect: function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        // @ts-expect-error
        var stopHandle = alpineReactivity.watchEffect.apply(void 0, args);
        watches.push(stopHandle);
        return stopHandle;
      },
      onBeforeMount: function (cb) {
        return cb();
      },
      // Run the callback immediately
      onMounted: function (cb) {
        return cb();
      },
      // Run the callback immediately
      onBeforeUnmount: _self.$onBeforeUnmount, // OK
      onUnmounted: _self.$onBeforeUnmount, // OK
      onBeforeUpdate: function (cb) {
        return onBeforeUpdatedCallbacks.push(cb);
      },
      onUpdated: function (cb) {
        return onUpdatedCallbacks.push(cb);
      },
      onActivated: function () {},
      // NOOP
      onDeactivated: function () {}, // NOOP
    };

    return returnObject;
  };

  var getPropDefault = function (prop) {
    // Only prop type is given as constructor
    if (typeof prop === "function" || Array.isArray(prop)) {
      return undefined;
    }
    if (typeof prop.default === "function") {
      return prop.default();
    } else {
      return prop.default;
    }
  };
  var isPropRequired = function (prop) {
    // Only prop type is given as constructor, which implies that a prop is optional
    if (typeof prop === "function" || Array.isArray(prop)) {
      return false;
    }
    return !!prop.required;
  };
  var getPropType = function (prop) {
    // Check if prop type is given as constructor
    var propType =
      typeof prop === "function" || Array.isArray(prop)
        ? prop
        : prop
        ? prop.type
        : null;
    if (typeof propType === "function") {
      propType = [propType];
    }
    return propType;
  };
  // TODO DELETE
  //   var loadInitState = function (instance, initKey) {
  //     var dataAttr = "data-x-".concat(initKey);
  //     var val = instance.$el.getAttribute(dataAttr);
  //     if (val == null) return;
  //     var initState = JSON.parse(val);
  //     instance.$initState = initState;
  //   };
  // TODO
  window.timeSpentInUseProps = 0;
  var useProps = function (Alpine, compName, el, propsDef, emitOptions) {
    // TODO
    const startTime = performance.now();

    // TODO CHNAGED
    var propsExpression = el.getAttribute("x-props") || "undefined";
    // NOTE: We want to use parentNode, so, inside `x-props`, we're using the data provided
    // by the PARENT alpine components.
    var getGivenProps = Alpine.evaluateLater(el.parentNode, propsExpression);  // TODO CHNAGED
    var parsedProps = alpineReactivity.reactive({});
    var propKeys = Object.keys(propsDef);
    for (var _i = 0, _a = Object.keys(emitOptions); _i < _a.length; _i++) {
      var event_1 = _a[_i];
      var eventProps = handlerKeys(event_1);
      propKeys.push.apply(propKeys, eventProps);
    }

    // TODO - CHANGED SO WE DETECT EXTRA PROPS TOO!!!
    // TODO - CHANGED SO WE DETECT EXTRA PROPS TOO!!!
    // TODO - CHANGED SO WE DETECT EXTRA PROPS TOO!!!
    alpineReactivity.watchEffect(function () {
      getGivenProps(function (givenProps) {
        if (!givenProps) {
          givenProps = {};
        }
        if (typeof givenProps !== "object") {
          throw Error(
            `[alpine-composition] ${compName}: Props must be passed as an object, got ${typeof givenProps}`
          );
        }
        Object.keys(givenProps).forEach(function (key) {
          if (!propKeys.includes(key)) {
            throw Error(
              `[alpine-composition] ${compName}: Got unexpected prop '${key}'`
            );
          }
        });

        // By now, we know that the props include only valid keys.
        propKeys.forEach(function (key) {
          // TODO
          // TODO - Moved this out of the callback
          // TODO
          var propTypes = getPropType(propsDef[key]);
          var propDef = propsDef[key];
          var isRequired = propDef ? isPropRequired(propDef) : false;
          var propDefault = propDef ? getPropDefault(propDef) : undefined;

          var propVal = givenProps[key];
          // TODO
          // TODO - Added check here so only props with `on` are event handlers
          // TODO

          // Key is an event handler if it has no definition, in which
          // case we don't do validation nor set defaults.

          // TODO
          // TODO - Do more nuanced check so that 3rd letter must be capitalized
          // TODO
          if (!propDef) {
            if (key.startsWith("on")) {
              parsedProps[key] = propVal;
              return;
            } else {
              throw Error(
                "[alpine-composition] "
                  .concat(compName, ": Got unexpected prop '")
                  .concat(key)
              );
            }
          }

          if (propVal !== undefined) {
            parsedProps[key] = propVal;
          } else {
            if (propDefault !== undefined) {
              parsedProps[key] = propDefault;
            } else if (!isRequired) {
              parsedProps[key] = undefined;
            } else {
              throw Error(
                "[alpine-composition] "
                  .concat(compName, ": Required prop '")
                  .concat(key, "' is missing")
              );
            }
          }
          // Check type if specific types given
          if (
            propTypes &&
            typeof propTypes !== "boolean" &&
            // When a prop is NOT required, `null` and `undefined` pass type checks.
            // And only when the prop is required is when we consider even null/undefined.
            // See https://stackoverflow.com/questions/59125043/
            (isRequired || (!isRequired && parsedProps[key] != undefined))
          ) {
            if (!isInstanceOf(propTypes, parsedProps[key])) {
              throw Error(
                "[alpine-composition] "
                  .concat(compName, ": Prop '")
                  .concat(key, "' is not an instance of ")
                  .concat(propTypes)
              );
            }
          }
        });
      });
    });

    // TODO
    const endTime = performance.now();
    window.timeSpentInUseProps += endTime - startTime;

    return parsedProps;
  };
  // TODO END
  var getAttributes = function (element) {
    var attributes = element.attributes;
    var result = {};
    for (
      var _i = 0, attributes_1 = attributes;
      _i < attributes_1.length;
      _i++
    ) {
      var attr = attributes_1[_i];
      // If attribute value is empty, set it to true, otherwise use the actual value
      result[attr.name] = attr.value === "" ? true : attr.value;
    }
    return result;
  };
  // TODO CHANGED!!
  var makeInstance = function (Alpine, el) {
    // TODO CHANGED - THRE IS ONLY 1 LAYER, THEN NO NEED FOR MERGE_PROXIES
    // return Alpine.mergeProxies(Alpine.closestDataStack(el));
    return Alpine.closestDataStack(el)[0];
  };
  // TODO CHANGED
  var isolateInstance = function (el) {
    if (el._x_dataStack) {
      el._x_dataStack = el._x_dataStack.slice(0, 1);
    }
  };
  // TODO START
  var applySetupContextToVm = function (Alpine, el, data) {
    // NOTE: We don't want to apply items to `instance`, because
    // that is already the result of `mergeProxies()`.
    // So if we tried to apply to `instance` then Alpine would internally
    // walk up the objects, searching for layer that has defined these.
    // And we want to apply it to the latest layer.
    // Moreover, we want to apply these through the reactive proxy.
    // Because we could simply apply the data to `vm` variable defined
    // on the outside, but that wouldn't trigger reactivity.
    const currLayer = Alpine.closestDataStack(el)[0];
    for (var attrname in data) {
      currLayer[attrname] = data[attrname];
    }
  };
  var defineComponent = function (options) {
    return options;
  };
  // TODO
  window.timeSpentIn_init = 0;
  var registerComponentFactory = function (registerFn) {
    return function (Alpine, options) {
      var name = options.name,
        propsDef = options.props,
        emitsDef = options.emits,
        setup = options.setup,
        _a = options.isolated,
        isolated = _a === void 0 ? true : _a,
        _b = options.initKey,
        initKey = _b === void 0 ? "init" : _b;
      var readonlyOptions = Object.freeze(__assign({}, options));
      var emitOptions = Object.freeze(
        normalizeEmitsOptions(
          emitsDef !== null && emitsDef !== void 0 ? emitsDef : null
        )
      );
      return registerFn(Alpine, readonlyOptions, name, function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        var onBeforeUnmountCbs = [];
        var parsedProps = {};
        // TODO ADED
        var el;
        // TODO ADED END
        var vm = {
          get $name() {
            return name;
          },
          get $props() {
            return parsedProps;
          },
          get $attrs() {
            // TODO THIS REMOVED
            // var instance = this;
            // TODO THIS WAS ADDED
            if (!el) return {};
            return getAttributes(el);
          },
          get $options() {
            return readonlyOptions;
          },
          get $emitsOptions() {
            return emitOptions;
          },
          $emit: function (name) {
            var args = [];
            for (var _i = 1; _i < arguments.length; _i++) {
              args[_i - 1] = arguments[_i];
            }
            // TODO - IS THIS SUPPOSED TO BE `vm` or `this`????
            // TODO - IS THIS SUPPOSED TO BE `vm` or `this`????
            // TODO - IS THIS SUPPOSED TO BE `vm` or `this`????
            emit.apply(void 0, __spreadArray([vm, name], args, false));
          },
          // See https://alpinejs.dev/globals/alpine-data#init-functions
          init: function () {
            var instance = this;

            // TODO
            // TODO
            // TODO
            // Access only once for better perf
            el = instance.$el;

            parsedProps = useProps(
              Alpine,
              name,  // TODO CHANGE
              el, // TODO CHANGE
              propsDef || {},
              emitOptions
            );

            if (isolated) {
              // If the component is isolated, we achieve so by modifying the AlpineJS data
              // Associated with the HTML element for this instance.
              isolateInstance(el); // TODO CHANGED // TODO CHANGED
            }

            // However, modifying AlpineJS data takes effect only for future Alpine component
            // instances that will be created from given HTML element. As for the one we have
            // currently, `instance`, we need to recreated it for the changes to take effect.
            //
            // In other words, the old `instance` still points to the additional contexts that
            // we want to isolate from.
            instance = makeInstance(Alpine, el); // TODO CHANGED // TODO CHANGED

            // TODO DELETE
            // TODO DELETE
            // TODO DELETE
            // And only once we have the (possibly isolated) instance, we can load the initial
            // state from the HTML. This must be done AFTER the above, because, Alpine contexts
            // work kinda like Django's Context, in that it's a stack/array of objects, where each
            // object represents one layer of the context. And if we introduce a new variable, it's
            // written to the LAST context. But isolating a component also makes it lose all it's
            // contexts except the FIRST one. So, effectively, throwing away all the changes applied
            // to in `loadInitState`.
            // loadInitState(instance, initKey);

            // NOTE: Pass in `vm` (the non-reactive current object)
            //       to avoid triggering reactivity.
            var reactivityAPI = createReactivityAPI(instance, vm);

            var data =
              setup === null || setup === void 0
                ? void 0
                : setup.apply(
                    void 0,
                    __spreadArray(
                      [parsedProps, instance, reactivityAPI],
                      args,
                      false
                    )
                  );

            const onData = (d) => {
              let data2 = d !== null && d !== void 0 ? d : {};
              applySetupContextToVm(Alpine, el, data2); // TODO CHANGED
              const endTime = performance.now();
              window.timeSpentIn_init += endTime - startTime;
            };

            if (isPromise(data)) {
              data.then(onData);
            } else {
              onData(data);
            }
          },
          $onBeforeUnmount: function (cb) {
            onBeforeUnmountCbs.push(cb);
          },
          // See https://alpinejs.dev/globals/alpine-data#destroy-functions
          destroy: function () {
            onBeforeUnmountCbs.forEach(function (cb) {
              return cb();
            });
          },
        };
        return vm;
      });
    };
  };
  var registerComponent = registerComponentFactory(function (
    Alpine,
    options,
    name,
    factory
  ) {
    return Alpine.data(name, factory);
  });

  // Utilities
  var createAlpineComposition = function (options) {
    var _a = options.plugins,
      plugins = _a === void 0 ? [] : _a;
    var registerComponent = registerComponentFactory(function (
      Alpine,
      options,
      name,
      factory
    ) {
      var factoryWithPlugins = function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
          args[_i] = arguments[_i];
        }
        var vm = factory.apply(void 0, args);
        var pluginCtx = {
          Alpine: Alpine,
          args: args,
          name: name,
          options: options,
          vm: vm,
        };
        for (var _a = 0, plugins_1 = plugins; _a < plugins_1.length; _a++) {
          var plugin = plugins_1[_a];
          plugin(vm, pluginCtx);
        }
        return vm;
      };
      Alpine.data(name, factoryWithPlugins);
    });
    return {
      registerComponent: registerComponent,
    };
  };

  exports.createAlpineComposition = createAlpineComposition;
  exports.createReactivityAPI = createReactivityAPI;
  exports.defineComponent = defineComponent;
  exports.hasEvent = hasEvent;
  exports.registerComponent = registerComponent;
  exports.registerComponentFactory = registerComponentFactory;
});
//# sourceMappingURL=cdn.js.map
