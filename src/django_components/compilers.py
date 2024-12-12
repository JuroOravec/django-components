import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple, Type, Union, TYPE_CHECKING

from django.conf import settings

from django_components.util.misc import get_import_path

if TYPE_CHECKING:
    from django_components.component import Component


# - each compiler plugin receives a list of input files, and a dict of 4 paths: static html, CSS, js; and orig comp module import path,
#   and orig comp filesystem path, and comp name and comp hash.
#
# - the plugins responsibility is to:
# 1. Process the sources, and place the output html/js/CSS into corresponding path.
# 2. In case the plugin generates extra dependencies, it will return them as a dict of lists like "js: [abc.js, xyz.js]
#
# Actually, what we should do is: 
# 1. For each component, define a "meta file" in staticfiles (JSON)
#
# 2. This meta file is known in advance (component hash for name), and defines
#    the paths to the primary dependencies - the html (single), js (list), css (list)
#
# 3. As plugins go one by one, they get reference to this dict. So they can eg change
#    the path to the html file, or append more JS/CSS deps.
#    - this way, it's possible to support code splitting for CSS files,
#      which would require us to load multiple CSS file on the initial load.
#
# 4. After all the compilers are done, we save the metafiles back to the filesystem. Because, during compilation,
#    we will need to store them in memory for each component (for simplicity)
#
# 5. At runtime, for each component we look at the staticfiles and look up the meta file JSON,
#    to get all the primary sources. Done lazily - Meta file JSON is loaded only once the component
#    is needed to be loaded.
#
# 6. To check if the HTML/js/CSS is in the staticfiles, we would: 
#   1. Open the meta JSON file (cached until server resets) 
#   2. Get the path for corresponding source (html/js/CSS) - also cached until reset or until the the files are rebuilt.
#
# 7. The "primary dependencies" would be loaded same way as inlined JS/CSS - so all CSS in primaries would be inlined into HTML (as <link> tag) to avoid unstyled content flash.
# 8. JS would be handled the same way, just loaded earlier (before Media.Js)

# TODO
from dataclasses import dataclass
@dataclass
class CompilerCtx:
    html_path: Path
    css_paths: List[Path]
    js_paths: List[Path]
    component: Type["Component"]
    component_path: Path
    component_module_path: str


from typing import NamedTuple
class CompilerComponentData(NamedTuple):
    comp_cls: Type["Component"]
    files: List[Path]


class CompilerComponentEntry(NamedTuple):
    context: CompilerCtx
    file: Path


class CompilerFn(Protocol):
    def __call__(self, data: List[CompilerComponentEntry], args: Optional[Dict]) -> List[Path]: ...


def get_compiler(filepath: Path) -> Optional[Tuple[str, CompilerFn]]:
    # Find first matching compiler:
    for name, cond, compiler in compilers:
        # Case: File suffix, e.g. "js" or "css"
        if not isinstance(cond, re.Pattern):
            suffix = filepath.suffix[1:]
            if suffix == cond:
                return name, compiler
        # Case: Regex, e.g. `/\.js$/`
        else:
            match = cond.search(str(filepath))
            if match is not None:
                return name, compiler

    return None


# NOTE: We accept many files, in cases there are some compilers that need to process
# all the files of the same kind at the same time, and need the files to be given
# explicitly.
def compile_files(data: List[CompilerComponentData]) -> List[Path]:
    files_by_compilers: Dict[Tuple[str, CompilerFn], List[CompilerComponentEntry]] = {}
    contexts: Dict[Type["Component"], CompilerCtx] = {}

    def get_context(comp_cls: Type["Component"]) -> CompilerCtx:
        if comp_cls in contexts:
            return contexts[comp_cls]

        comp_rel_path = Path(comp_cls._comp_path_relative)
        ctx = CompilerCtx(
            html_path=comp_rel_path.with_suffix(".html"),
            css_paths=[comp_rel_path.with_suffix(".css")],
            js_paths=[comp_rel_path.with_suffix(".js")],
            component=comp_cls,
            component_path=comp_rel_path,
            component_module_path=get_import_path(comp_cls),
        )
        contexts[comp_cls] = ctx
        return ctx

    for comp_cls, filepaths in data:
        for filepath in filepaths:
            compiler_data = get_compiler(filepath)
            if compiler_data is None:
                continue

            entry = CompilerComponentEntry(get_context(comp_cls), filepath)

            if compiler_data not in files_by_compilers:
                files_by_compilers[compiler_data] = []
            files_by_compilers[compiler_data].append(entry)

    # TODO: PUT SOME GUARDS UP HERE -> IF WE GOT ANY ENTRIES THAT ARE NOT IN
    #       "css", "js", or "html", AND COMPILATION IS DISABLED, THEN RAISE
    #       AN ERROR THAT WE CAME ACROSS FILES THAT REQUIRES COMPILATION.
    #       AND ADVISE USER TO EITHER CHANGE TYPING FOR THE SNIPPET to `types.css` / `types.html` / `types.js`
    #       OR TO ENABLE COMPILATION.
    #       NOTE: BECAUSE OF THE ALIASES, ALLOW ALIASES FOR CSS (style / styles), `js` (script), (javascript), etc.

    out_files: List[Path] = []
    for compiler_data, entries in files_by_compilers.items():
        name, compiler = compiler_data
        args = compiler_args.get(name, None)
        curr_out_files = compiler(entries, args)
        out_files.extend(curr_out_files)

    return out_files


# TODO
# Or...
# compilers = {
#     "path.to.js_compiler": [
#         "js",
#         "ts",
#         re.compile(r"\.js$"),
#     ],
#     # (re.compile(r"\.js$"), js_compiler),
#     ("js", js_compiler),
#     ("jsx", js_compiler),
#     ("ts", js_compiler),
#     ("tsx", js_compiler),
# }

# Default settings for Tetra  # TODO

TETRA_ESBUILD_CSS_ARGS = [
    "--bundle",
    "--minify",
    "--sourcemap",
    "--entry-names=[name]-[hash]",
    "--loader:.png=file",
    "--loader:.svg=file",
    "--loader:.gif=file",
    "--loader:.jpg=file",
    "--loader:.jpeg=file",
    "--loader:.webm=file",
    "--loader:.woff=file",
    "--loader:.woff2=file",
    "--loader:.ttf=file",
]


# TODO
# SET TETRA_ESBUILD_PATH
# if not hasattr(settings, "TETRA_ESBUILD_PATH"):
#     bin_name = "esbuild.cmd" if os.name == "nt" else "esbuild"

#     if getattr(settings, "BASE_DIR", None):
#         setattr(
#             settings,
#             "TETRA_ESBUILD_PATH",
#             Path(settings.BASE_DIR) / "node_modules" / ".bin" / bin_name,
#         )
#     else:
#         setattr(settings, "TETRA_ESBUILD_PATH", None)



# TODO - STEPS TO INSTALL ESBUILD:
#   1. `npm init` at the root (where `BASE_DIR` is)
#   2. `npm install -D esbuild tsc`
#   3. `npx tsc --init` at the root (`BASE_DIR`) to create `tsconfig.json`
#   4. `python manage.py componentcollect`
def ts_compiler(
    entries: List[CompilerComponentEntry],
    data: Optional[Dict]
) -> List[Path]:
    typecheck = (data or {}).get("typecheck", True)
    esbuild_path = (data or {}).get("esbuild_path", None)
    tsconfig_path = (data or {}).get("tsconfig_path", "tsconfig.json")

    # 1. Run type checking if TypeScript
    #    NOTE: Requires `tsc` installed
    if typecheck:
        # Prepare dummy `tsconfig.json` where we specify:
        # 1. All the TS files to check in `files`
        # 2. The ACTUAL (user-provided) `tsconfig.json` via `extends`
        # 
        # This is necessary, because TypeScript's CLI doesn't support specifying
        # both a path to `tsconfig.json` AND listing all included files in the terminal.
        # And we want to allow users to configure TS via `tsconfig.json`.
        import tempfile  # TODO
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            tsconfig = {
                "extends": os.path.abspath(tsconfig_path),
                "files": [str(entry.file.absolute()) for entry in entries],
            }
            tmp.write(json.dumps(tsconfig).encode("utf-8"))

            print(json.dumps(tsconfig).encode("utf-8")) # TODO

            # Now use the temp tsconfig.json to type-check the TS files
            # E.g. `tsc --noEmit --project tsconfig.json ./path/to/file1.ts ./path/to/file2.ts ./path/to/file3.ts`
            subprocess.run(
                # TODO: CHECK IF THIS ACTUALLY WORKS?
                [
                    "tsc",
                    "--project",
                    tmp.name,
                    "--noEmit",  # No matter what's in users's tsconfig, do NOT generate files
                    "--allowJs",
                ],
                check=True,
            )

    # 2. Compile JS / TS with esbuild
    if not esbuild_path:
        bin_name = "esbuild.cmd" if os.name == "nt" else "esbuild"
        esbuild_path = Path(settings.BASE_DIR) / "node_modules" / ".bin" / bin_name

    # To avoid overwriting files during compilation, we rename the input entrypoints
    # by suffixing `_in`, e.g. `myfile_in.js`
    in_file_paths = [
        entry.file.rename(entry.file.with_name(entry.file.stem + "_in" + entry.file.suffix))
        for entry in entries
    ]

    out_files = [entry.file.with_suffix(".js") for entry in entries]

    esbuild_cmd = [
        str(esbuild_path),
        *[
            f"{entry.file.with_suffix("")}={str(in_file_paths[index])}"
            for index, entry in enumerate(entries)
        ],
        "--bundle",
        "--minify",
        "--sourcemap",
        "--entry-names=[dir]/[name]-[hash]",
        f"--chunk-names={settings.STATIC_ROOT}/__dc__/chunks/[name]-[hash]",
        "--platform=browser",
        "--target=chrome80,firefox73,safari13,edge80",
        # THESE ARE SPECIFIC TO SPLITTING!
        # TODO - IF `format=esm` IN SETTINGS, THEN THE SCRIPTS NEED TO BE IMPORTED
        #        AS ESM, SO <script type="module" ...></script>
        "--splitting",
        "--format=esm",
        "--metafile=metafile.json"
        "--outdir=.",  # NOTE: Because the # TODO
    ]

    subprocess.run(esbuild_cmd, check=True)

    # TODO
    from pprint import pprint
    print("OOGA: ")
    pprint([
        f"{entry.file.with_suffix("")}={str(in_file_paths[index])}"
        for index, entry in enumerate(entries)
    ])

    return out_files
    

import json
from django_components import types
def compile_sass(
    comp_cls: Type["Component"],
    file_paths: List[Path],
    out_dir: Path,
):
    in_file_paths = [
        f.rename(f.with_name(f.stem + "_in" + f.suffix))
        for f in file_paths
    ]

    paths_mapping = {
        filepath.with_suffix(""): str(in_file_paths[index])
        for index, filepath in enumerate(file_paths)
    }

    compiler_js_script: types.js = """
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
    """

    exec_command = f"build(JSON.parse(`{json.dumps(paths_mapping)}`), `{str(out_dir)}`)"

    compiler_js_script = compiler_js_script + "\n" + exec_command
    compiler_js_script = compiler_js_script.replace('"', '\\"')

    esbuild_ret = subprocess.run([
        "node",
        "-e",
        f'"{compiler_js_script}"',
    ])

    if esbuild_ret.returncode != 0:
        print("ERROR BUILDING JS:", get_import_path(comp_cls))
        return


# TODO - Add compiler for:
# - Sass
# - Less - https://lesscss.org/usage/#command-line-usage-options-specific-to-lessc
# - Stylus - https://devhints.io/stylus
# - Markdown
# - Pug
#
# NOTE:
# - Hot reload -> NOPE, difficult
# - Live reload -> Maybe for some? Maybe could be that I just run `componentcollect`
#                  internally when any of the files in `COMPONENTS.dirs` changes?
#                  - Also call `componentcollect` on start of runserver?
# - Markdown and Pug -> to be applied in `render` right after we render the template.
#                       It should run BEFORE the plugins' HTML_POSTPROCESS, so plugins
#                       receive already familiar HTML.
# - i18n and makemessages -> 
compilers: List[
    Tuple[str, Union[str, re.Pattern], CompilerFn],
] = [
    ("js", re.compile(r"\.(?:js|ts|jsx|tsx|mjs)$"), ts_compiler),
]

compiler_args: Dict[str, Dict] = {
    "js": { "check_ts": True },
}


# def build():
#     # TODO: check if source has changed and only build if it has
#     print(f"# Building {self.display_name}")
#     file_cache_path = os.path.join(
#         self.app.path, settings.TETRA_FILE_CACHE_DIR_NAME, self.name
#     )
#     file_out_path = os.path.join(
#         self.app.path, "static", self.app.label, "tetra", self.name
#     )
#     if os.path.exists(file_cache_path):
#         shutil.rmtree(file_cache_path)
#     os.makedirs(file_cache_path)
#     if os.path.exists(file_out_path):
#         shutil.rmtree(file_out_path)
#     os.makedirs(file_out_path)
#     self.build_js(file_cache_path, file_out_path)
#     self.build_styles(file_cache_path, file_out_path)

# # TODO REMOVE
# #      - THE PART WITH `if component.has_script():`
# #        IS THE SAME THAT WE DO PRE-PROCESSING COMPONENT'S DEPENDENCIES
# #      - MOVE THE ESBUILD OUT OF LIBRARY / ALPINE. Should be a preprocess step
# def build_js(self, file_cache_path, file_out_path):
#     main_imports = []
#     main_scripts = []
#     files_to_remove = []
#     main_path = os.path.join(file_cache_path, self.js_filename)
#     meta_filename = f"{self.js_filename}__meta.json"
#     meta_path = os.path.join(file_cache_path, meta_filename)

#     try:
#         for component_name, component in self.components.items():
#             print(f" - {component_name}")
#             if component.has_script():
#                 script = component.make_script_file()
#                 py_filename, _, _ = component.get_source_location()
#                 py_dir = os.path.dirname(py_filename)
#                 filename = f"{os.path.basename(py_filename)}__{component_name}.js"
#                 component_path = os.path.join(py_dir, filename)
#                 files_to_remove.append(component_path)
#                 with open(component_path, "w") as f:
#                     f.write(script)
#                 rel_path = os.path.relpath(component_path, file_cache_path)
#                 if os.name == "nt":
#                     rel_path = rel_path.replace(os.sep, "/")
#                 main_imports.append(f'import {component_name} from "{rel_path}";')
#                 main_scripts.append(component.make_script(component_name))
#             else:
#                 main_scripts.append(component.make_script())

#         with open(main_path, "w") as f:
#             f.write("\n".join(main_imports))
#             f.write("\n\n")
#             f.write("\n".join(main_scripts))

#         esbuild_ret = subprocess.run(
#             [settings.TETRA_ESBUILD_PATH, main_path]
#             + settings.TETRA_ESBUILD_JS_ARGS
#             + [f"--outdir={file_out_path}", f"--metafile={meta_path}"]
#         )

#         if esbuild_ret.returncode != 0:
#             print("ERROR BUILDING JS:", self.display_name)
#             return
#     finally:
#         for path in files_to_remove:
#             os.remove(path)

#     with open(meta_path) as f:
#         meta = json.load(f)
#     for path, data in meta["outputs"].items():
#         if data.get("entryPoint", None):
#             out_path = path
#             break

#     with open(f"{self.js_path}.filename", "w") as f:
#         f.write(os.path.basename(out_path))

# def build_styles(self, file_cache_path, file_out_path):
#     main_imports = []
#     files_to_remove = []
#     main_path = os.path.join(file_cache_path, self.styles_filename)
#     meta_filename = f"{self.styles_filename}__meta.json"
#     meta_path = os.path.join(file_cache_path, meta_filename)

#     try:
#         for component_name, component in self.components.items():
#             if component.has_styles():
#                 print(f" - {component_name}")
#                 styles = component.make_styles_file()
#                 py_filename, _, _ = component.get_source_location()
#                 py_dir = os.path.dirname(py_filename)
#                 filename = f"{os.path.basename(py_filename)}__{component_name}.css"
#                 component_path = os.path.join(py_dir, filename)
#                 files_to_remove.append(component_path)
#                 with open(component_path, "w") as f:
#                     f.write(styles)
#                 rel_path = os.path.relpath(component_path, file_cache_path)
#                 if os.name == "nt":
#                     rel_path = rel_path.replace(os.sep, "/")
#                 main_imports.append(f"@import '{rel_path}';")

#         with open(main_path, "w") as f:
#             f.write("\n".join(main_imports))

#         esbuild_ret = subprocess.run(
#             [settings.TETRA_ESBUILD_PATH, main_path]
#             + settings.TETRA_ESBUILD_CSS_ARGS
#             + [
#                 f"--outdir={file_out_path}",
#                 # These three lines below are a work around so that urls to images
#                 # update correctly.
#                 "--metafile=meta.json",
#                 f"--outbase={self.app.path}",
#                 f"--asset-names={os.path.relpath(self.app.path, file_out_path)}/[dir]/[name]",
#                 "--allow-overwrite",
#                 f"--metafile={meta_path}",
#             ]
#         )

#         if esbuild_ret.returncode != 0:
#             print("ERROR BUILDING CSS:", self.display_name)
#             return
#     finally:
#         for path in files_to_remove:
#             os.remove(path)

#     with open(meta_path) as f:
#         meta = json.load(f)
#     for path, data in meta["outputs"].items():
#         if data.get("entryPoint", None):
#             out_path = path
#             break

#     with open(f"{self.styles_path}.filename", "w") as f:
#         f.write(os.path.basename(out_path))
