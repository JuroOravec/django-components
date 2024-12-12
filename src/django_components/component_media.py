import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Type, Union

from django.forms.widgets import Media
from django.utils.safestring import SafeData

from django_components.util.loader import get_component_dirs
from django_components.util.logger import logger

if TYPE_CHECKING:
    from django_components.component import Component


class ComponentMediaInput:
    """Defines JS and CSS media files associated with this component."""

    css: Optional[Union[str, List[str], Dict[str, str], Dict[str, List[str]]]] = None
    js: Optional[Union[str, List[str]]] = None


class ResolvedMedia(NamedTuple):
    media: Media
    extra_paths: Dict[str, Optional[str]]


# TODO - Mention that we removed the option to use `extend` attr in Media classs
class ComponentMedia:
    # TODO UPDATE DOCS
    """
    Class for handling media files for components.

    Inspired by Django's `MediaDefiningClass`, this class supports the use of `Media` attribute
    to define associated JS/CSS files, which are then available under `media`
    attribute as a instance of `Media` class.

    Unlike the original `MediaDefiningClass`, this class resolves the JS/CSS filepaths lazily.

    This subclass has following changes:

    ### 1. Support for multiple interfaces of JS/CSS

    1. As plain strings
        ```py
        class MyComponent(Component):
            class Media:
                js = "path/to/script.js"
                css = "path/to/style.css"
        ```

    2. As lists
        ```py
        class MyComponent(Component):
            class Media:
                js = ["path/to/script1.js", "path/to/script2.js"]
                css = ["path/to/style1.css", "path/to/style2.css"]
        ```

    3. [CSS ONLY] Dicts of strings
        ```py
        class MyComponent(Component):
            class Media:
                css = {
                    "all": "path/to/style1.css",
                    "print": "path/to/style2.css",
                }
        ```

    4. [CSS ONLY] Dicts of lists
        ```py
        class MyComponent(Component):
            class Media:
                css = {
                    "all": ["path/to/style1.css"],
                    "print": ["path/to/style2.css"],
                }
        ```

    ### 2. Media are first resolved relative to class definition file

    E.g. if in a directory `my_comp` you have `script.js` and `my_comp.py`,
    and `my_comp.py` looks like this:

    ```py
    class MyComponent(Component):
        class Media:
            js = "script.js"
    ```

    Then `script.js` will be resolved as `my_comp/script.js`.

    ### 3. Media can be defined as str, bytes, PathLike, SafeString, or function of thereof

    E.g.:

    ```py
    def lazy_eval_css():
        # do something
        return path

    class MyComponent(Component):
        class Media:
            js = b"script.js"
            css = lazy_eval_css
    ```

    ### 4. Subclass `Media` class with `media_class`

    Normal `MediaDefiningClass` creates an instance of `Media` class under the `media` attribute.
    This class allows to override which class will be instantiated with `media_class` attribute:

    ```py
    class MyMedia(Media):
        def render_js(self):
            ...

    class MyComponent(Component):
        media_class = MyMedia
        def get_context_data(self):
            assert isinstance(self.media, MyMedia)
    ```
    """

    def __init__(
        self,
        component: Type["Component"],
        media_input: Optional[Type[ComponentMediaInput]],
        extra_paths: Optional[Dict[str, Optional[str]]],
    ) -> None:
        js, css = _normalize_media(media_input)
        self.component: Type["Component"] = component
        self.js = js
        self.css = css
        self.extra_paths = extra_paths
        self._resolved: Optional[ResolvedMedia] = None

    @property
    def resolved(self) -> ResolvedMedia:
        if not self._resolved:
            self._resolved = self._resolve_media()
        return self._resolved

    def _resolve_media(self) -> ResolvedMedia:
        """
        Check if component's HTML, JS and CSS files refer to files in the same directory
        as the component class. If so, modify the attributes so the class Django's rendering
        will pick up these files correctly.
        """
        # The component's file path is used when working with its JS and CSS,
        # so we compute this value at the class creation.
        # comp_cls._comp_path_absolute = None  # TODO
        # comp_cls._comp_path_relative = None  # TODO

        # First check if we even need to resolve anything. If the class doesn't define any
        # JS/CSS files, just skip.
        will_resolve_files = bool(self.extra_paths or self.js or self.css)
        if not will_resolve_files:
            return

        component_name = self.component.__qualname__

        # Get the full path of the file where the component was defined
        module_name = self.component.__module__
        if module_name == "__main__" or module_name.startswith("django_components."):
            # NOTE: If a class is defined in __main__ module, it was NOT defined in a file,
            # but instead in REPL (terminal), in which case the rest of the code doesn't make sense.
            return
        module_obj = sys.modules[module_name]
        file_path = module_obj.__file__

        if not file_path:
            logger.debug(
                f"Could not resolve the path to the file for component '{component_name}'."
                " Paths for HTML, JS or CSS templates will NOT be resolved relative to the component file."
            )
            return

        # Prepare all possible directories we need to check when searching for
        # component's template and media files
        components_dirs = get_component_dirs()

        # Get the directory where the component class is defined
        try:
            comp_dir_abs, comp_dir_rel = _get_dir_path_from_component_path(file_path, components_dirs)
            # comp_cls._comp_path_absolute = file_path  # TODO
            # comp_cls._comp_path_relative = str(Path(comp_dir_rel) / Path(file_path).name)  # TODO
        except RuntimeError:
            # If no dir was found, we assume that the path is NOT relative to the component dir
            logger.debug(
                f"No component directory found for component '{component_name}' in {file_path}"
                " If this component defines HTML, JS or CSS templates relatively to the component file,"
                " then check that the component's directory is accessible from one of the paths"
                " specified in the Django's 'COMPONENTS.dirs' settings."
            )
            return

        # Check if filepath refers to a file that's in the same directory as the component class.
        # If yes, modify the path to refer to the relative file.
        # If not, don't modify anything.
        def resolve_file(filepath: Union[str, SafeData]) -> Union[str, SafeData]:
            if isinstance(filepath, str):
                filepath_abs = os.path.join(comp_dir_abs, filepath)
                # NOTE: The paths to resources need to use POSIX (forward slashes) for Django to wor
                #       See https://github.com/EmilStenstrom/django-components/issues/796
                filepath_rel_to_comp_dir = Path(os.path.join(comp_dir_rel, filepath)).as_posix()

                if os.path.isfile(filepath_abs):
                    # NOTE: It's important to use `repr`, so we don't trigger __str__ on SafeStrings
                    logger.debug(
                        f"Interpreting template '{repr(filepath)}' of component '{module_name}'"
                        " relatively to component file"
                    )

                    return filepath_rel_to_comp_dir

            # If resolved absolute path does NOT exist or filepath is NOT a string, then return as is
            logger.debug(
                f"Interpreting template '{repr(filepath)}' of component '{module_name}'"
                " relatively to components directory"
            )
            return filepath

        # Check if template / JS / CSS file names are local files or not
        resolved_extras: Dict[str, Optional[str]] = {}
        for key, val in self.extra_paths.items():
            if val:
                resolved_extras[key] = resolve_file(val)
            else:
                resolved_extras[key] = None

        js, css = _map_media_filepaths(self.js, self.css, resolve_file)
        
        media_cls = getattr(self.component, "media_class", None) or Media
        media = media_cls(js=js, css=css)

        return ResolvedMedia(media, extra_paths=resolved_extras)


def _normalize_media(media: Optional[type[ComponentMediaInput]]) -> Tuple[List[str], Dict[str, List[str]]]:
    js: List[str] = []
    css: Dict[str, List[str]] = {}

    if hasattr(media, "css") and media.css:
        # Allow: class Media: css = "style.css"
        if _is_media_filepath(media.css):
            css["all"] = [media.css]

        # Allow: class Media: css = ["style.css"]
        elif isinstance(media.css, (list, tuple)):
            css["all"] = media.css

        # Allow: class Media: css = {"all": "style.css"}
        #        class Media: css = {"all": ["style.css"]}
        elif isinstance(media.css, dict):
            for media_type, path_or_list in media.css.items():
                # {"all": "style.css"}
                if _is_media_filepath(path_or_list):
                    css[media_type] = [path_or_list]
                # {"all": ["style.css"]}
                else:
                    css[media_type] = path_or_list
        else:
            raise ValueError(f"Media.css must be str, list, or dict, got {type(media.css)}")

    if hasattr(media, "js") and media.js:
        # Allow: class Media: js = "script.js"
        if _is_media_filepath(media.js):
            js.extend([media.js])
        # Allow: class Media: js = ["script.js"]
        else:
            js.extend(media.js)

    # Given a predictable structure of Media class, get all the various JS/CSS paths
    # that user has defined, and normalize them too.
    #
    # Because we can accept:
    # str, bytes, PathLike, SafeData (AKA Django's "path as object") or a callable
    #
    # And we want to convert that to:
    # str and SafeData
    js, css = _map_media_filepaths(js, css, _normalize_media_filepath)

    return js, css


def _map_media_filepaths(
    js: List[str],
    css: Dict[str, List[str]],
    map_fn: Callable[[Any], Any],
) -> Tuple[List[str], Dict[str, List[str]]]:
    for media_type, path_list in css.items():
        css[media_type] = list(map(map_fn, path_list))

    js = list(map(map_fn, js))

    return js, css


def _is_media_filepath(filepath: Any) -> bool:
    if callable(filepath):
        return True

    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return True

    elif isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        return True

    if isinstance(filepath, bytes):
        return True

    if isinstance(filepath, str):
        return True

    return False


def _normalize_media_filepath(filepath: Any) -> Union[str, SafeData]:
    if callable(filepath):
        filepath = filepath()

    if isinstance(filepath, SafeData) or hasattr(filepath, "__html__"):
        return filepath

    if isinstance(filepath, (Path, os.PathLike)) or hasattr(filepath, "__fspath__"):
        # In case of Windows OS, convert to forward slashes
        filepath = Path(filepath.__fspath__()).as_posix()

    if isinstance(filepath, bytes):
        filepath = filepath.decode("utf-8")

    if isinstance(filepath, str):
        return filepath

    raise ValueError(
        "Unknown filepath. Must be str, bytes, PathLike, SafeString, or a function that returns one of the former"
    )


def _get_dir_path_from_component_path(
    abs_component_file_path: str,
    candidate_dirs: Union[List[str], List[Path]],
) -> Tuple[str, str]:
    comp_dir_path_abs = os.path.dirname(abs_component_file_path)

    # From all dirs defined in settings.COMPONENTS.dirs, find one that's the parent
    # to the component file.
    root_dir_abs = None
    for candidate_dir in candidate_dirs:
        candidate_dir_abs = os.path.abspath(candidate_dir)
        if comp_dir_path_abs.startswith(candidate_dir_abs):
            root_dir_abs = candidate_dir_abs
            break

    if root_dir_abs is None:
        raise RuntimeError(
            f"Failed to resolve template directory for component file '{abs_component_file_path}'",
        )

    # Derive the path from matched COMPONENTS.dirs to the dir where the current component file is.
    comp_dir_path_rel = os.path.relpath(comp_dir_path_abs, candidate_dir_abs)

    # Return both absolute and relative paths:
    # - Absolute path is used to check if the file exists
    # - Relative path is used for defining the import on the component class
    return comp_dir_path_abs, comp_dir_path_rel
