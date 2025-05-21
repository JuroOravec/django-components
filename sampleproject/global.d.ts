interface ComponentContext {
  $id: string;
  $name: string;
  $data: object;
  $els: HTMLElement[];
}

type ComponentCb = (ctx: ComponentContext) => void | Promise<void>;

declare var Components = {
  manager: {
    registerComponent: (compName: string, callback: ComponentCb) =>
      ({} as void),
  },
};

declare const $onLoad: ComponentCb = (...args: any[]) => {};
