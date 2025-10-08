Action plan:

1. Write a blog post about "Making server-side Vue 10x faster"

- Explain how `.vue` files could be run on Python
- And if we could run them on Python, we could run them on Go or Rust
- Thus, speeding up the server-side rendering of Vue.js
- And that for this, developing django-components is crucial as it allows us to
  define the model of how to render Vue.js components in non-JS environments

2. Write out plans for v1:

- mention the 5 issue area that still remain to be solved:
  - get_template(), on_render(), etc.
  - JS / CSS variables and CSS scoping
  - Slot functions API
  - Template attributes parsing move to Rust

3. Set up django-components to sponsorable project.

4. Add banner to readme, mentioning the goals and asking for sponsors.

5. Check out [public repos that use django-components](https://github.com/search?q=%22django_components%22&type=repositories) and see:

- if we can help them
- if we can put them in the README
- ask them to sponsor the project

6. Reach out to podcasts / blogs / youtube channels / etc. (TODO EXPAND)


Checklist:

- Update profiles:
  - [X] Github
  - [ ] Twitter
  - [ ] Bluesky
  - [ ] Threads
  - [ ] LinkedIn
- [ ] Update JurOra.vc
- [ ] Add banner to readme, mentioning the goals and asking for sponsors.
- [ ] Reference features that need supporting
   - See https://github.com/django-components/django-components/issues/433#issuecomment-2824119625
   - Say that it is to secure funding for the next year
   - Target 5k / mo.