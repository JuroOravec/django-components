const build = (entryPoints, outdir) => {
  // build.js
  const esbuild = require("esbuild");
  const { sassPlugin } = require("esbuild-sass-plugin");

  esbuild
    .build({
      entryPoints,
      outdir,
      bundle: true,
      // NOTE: Splitting doesn't work for CSS?
      // format: "esm",
      // splitting: true,
      minify: true,
      loader: {
        ".scss": "css",
        ".sass": "css",
        ".css": "css",
      },
      plugins: [
        sassPlugin({
          type: "css", // Output CSS files
        }),
      ],
    })
    .catch(() => process.exit(1));
};
build({
    "staticfiles/todo/todo-Todo_7877e9____": "staticfiles/todo/todo-Todo_7877e9.scss",
    "staticfiles/todo/todo____": "staticfiles/todo/todo-0.scss",
}, "dist");
