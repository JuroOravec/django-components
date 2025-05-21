# COMPILERS

- each compiler plugin receives a list of input files, and a dict of 4 paths: static html, CSS, js; and orig comp module import path, and orig comp filesystem path, and comp name and comp hash.
- the plugins responsibility is to

1. Process the sources, and place the output html/js/CSS into corresponding path.
2. In case the plugin generates extra dependencies, it will return them as a dict of lists like "js: [abc.js, xyz.js]

Actually, what we should do is:

1. For each component, define a "meta file" in staticfiles (JSON)
2. This meta file is known in advance (component hash for name), and defines the paths to the primary dependencies - the html (single), js (list), css (list)
3. As plugins go one by one, they get reference to this dict. So they can eg change the path to the html file, or append more JS/CSS deps.

- this way, it's possible to support code splitting for CSS files, which would require us to load multiple CSS file on the initial load.

4. After all the compilers are done, we save the metafiles back to the filesystem. Because, during compilation, we will need to store them in memory for each component (for simplicity)
5. At runtime, for each component we look at the staticfiles and look up the meta file JSON, to get all the primary sources.
   You sent
6. To check if the HTML/js/CSS is in the staticfiles, we would:
7. Open the meta JSON file (cached until server resets)
8. Get the path for corresponding source (html/js/CSS) - also cached until reset or until the the files are rebuilt.
   You sent
9. The "primary dependencies" would be loaded same way as inlined JS/CSS - so all CSS in primaries would be inlined into HTML (as <link> tag) to avoid unstyled content flash.
10. JS would be handled the same way, just loaded earlier (before Media.Js)
