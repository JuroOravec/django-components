Here are several strategies to find organizations and users of django-components, and ways to reach out to them:

## GitHub Stargazers Analysis

**Manual approach:**
1. Go to the django-components GitHub repo's "Stargazers" tab
2. Click through profiles looking for:
   - Company affiliations in bios
   - Pinned repositories that might indicate company projects
   - Profile README files mentioning their work

**Automated approach:**
- Use GitHub's API to fetch stargazers data:
  ```bash
  curl -H "Accept: application/vnd.github+json" \
       -H "Authorization: Bearer YOUR_TOKEN" \
       https://api.github.com/repos/django-components/django-components/stargazers
  ```
- Write a script to analyze profiles for company info
- Look for patterns in usernames/organizations

## Finding Usage in the Wild

**Code search engines:**
- **GitHub Code Search**: Search for `django-components` or `django_components` in code
- **Sourcegraph**: More advanced code search across multiple platforms
- **grep.app**: Search across GitHub repositories

**Package managers:**
- Check PyPI download statistics
- Look at dependent packages on libraries.io

## Social Media & Forums

**Reddit:**
- Search r/django, r/Python for "django-components"
- Use site:reddit.com in Google: `site:reddit.com django-components`

**Twitter/X:**
- Search for "django-components" mentions
- Look for #django hashtag combinations

**Stack Overflow:**
- Search for django-components tagged questions
- Look at user profiles who ask/answer

**Django Forum:**
- Search forum.djangoproject.com for mentions

**Hacker News:**
- Use hn.algolia.com to search for submissions/comments

## Reaching Out

**Direct contact methods:**
1. **GitHub issues/discussions** - Most respectful approach
2. **LinkedIn** - Professional networking
3. **Twitter/X mentions** - Public but casual
4. **Email** - If publicly available in profiles

**Best practices:**
- Be transparent about your purpose
- Offer value (case study feature, testimonials)
- Keep initial outreach brief
- Respect privacy - don't be pushy

**Template message:**
```
Hi [Name],

I noticed you starred django-components on GitHub. I'm working on showcasing real-world usage of the library and would love to feature companies/projects using it.

Would you be open to a brief mention of how you're using django-components? Happy to keep it anonymous if preferred.

Thanks!
```

## Tools to Consider

**GitHub CLI:**
```bash
gh api repos/django-components/django-components/stargazers --paginate
```

**Python scripts using:**
- `requests` for API calls
- `beautifulsoup4` for web scraping
- `pandas` for data analysis

Would you like me to help you create a script for any of these approaches, or dive deeper into a specific strategy?









## TEMP

### Data from Github search

- `https://github.com/search?q=django-components+-repo%3Adjango-components%2Fdjango-components+-is%3Afork+created%3A<2025-06-23&type=repositories`

- `https://github.com/search?q="django_components"+-repo%3Adjango-components%2Fdjango-components+-is%3Afork+created%3A<2025-06-23&type=repositories`

    - NOTE: To search for repos created since the search above, use:
        - `https://github.com/search?q=django-components+-repo%3Adjango-components%2Fdjango-components&type=code+created%3A>2025-06-22&type=repositories`

    - Projects:
        - #TODOS
            - Reach out to them about creating new templates with my help
            - In landing page group usage, e.g. "management tools", "science projects"
        - [cjoakim/data](https://github.com/cjoakim/data/blob/061db6271ce10c52de23d832244cc7e02f19d62b/datasets/python_libs/pip/django-components.txt#L5)
        - [hylarucoder/playbase](https://github.com/hylarucoder/playbase/blob/7763ab1909d1e3f356a8c83ae7ab3ad9f85d6b91/pyproject.toml#L25)
        - [minvws/nl-kat-coordination](https://github.com/minvws/nl-kat-coordination/blob/a923a7faa9655097390a6fb318a435e2ecd86f52/rocky/requirements.txt#L259)
        - [om-proptech/livecomponents](https://github.com/om-proptech/livecomponents/blob/ae862c19b659ece74a9c81d361ed6c58829b732e/docs/templates.md?plain=1#L3)
        - [JuroOravec/djc-heroicons](https://github.com/JuroOravec/djc-heroicons/blob/40871d0449a37cc7e7c3b223a0787a29cebda0c0/CHANGELOG.md?plain=1#L7)
        - [XBastille/DeepFX-Studio](https://github.com/XBastille/DeepFX-Studio/blob/f02fdb8ea6a7a010140cda62afc9fd009f4732fe/deepfx_studio/settings.py#L115)
        - [ibm-luq95/beachwoodfinancial](https://github.com/ibm-luq95/beachwoodfinancial/blob/4e5123ae2f4bde4a50e59c17633b46205f6a7d1d/requirements/_base.txt#L7)
        - [openlibhums/hourglass](https://github.com/openlibhums/hourglass/blob/387ced9404297b04d28605325c7e405d42c9516e/tailwind.config.js#L18)
        - [jwpconsulting/projectify](https://github.com/jwpconsulting/projectify/blob/f24b6f6a224214b510d3d2466c1523b63bc6a13d/docs/remove-fe-worklog.md?plain=1#L203) - Post mortem why they didn't use django-components
        - [urfu-online/lrr2](https://github.com/urfu-online/lrr2/blob/b0856e2711b9fc1bf8af06c87044e0dba9962938/backend/requirements/base.txt#L32)
        - [Helien-Dev/Honey-Bun-Django](https://github.com/Helien-Dev/Honey-Bun-Django/blob/738afdb3d4e14834e38cc8e8d125ed19a7b99f00/Dockerfile#L14)
        - [diefenbach/djello](https://github.com/diefenbach/djello/blob/f2ae2539194f3925b88e895b15a68bb7647c73ae/requirements.txt#L3)
        - [wodoame/expense-tracking-application](https://github.com/wodoame/expense-tracking-application/blob/2cabdc5a953b1e196f18f17ba5328e38309b82c4/docs/UI/basics/creating-a-component.md?plain=1#L14)
        - [WCutePy/Cell-Viewer](https://github.com/WCutePy/Cell-Viewer/blob/a0d41bdaad287067d91438ab1ad0929cc54d34ee/docs/.main_docs.md?plain=1#L66)
        - [PetrSebik/online-shopping-list](https://github.com/PetrSebik/online-shopping-list/blob/1eb1f012708338d15eeceae6a20db7bfd2448369/Pipfile#L11)
        - [kudah99/finhub](https://github.com/kudah99/finhub/blob/1d05ed21eea0511f5ff8bc6545fcaf6ad7704295/Pipfile#L21)

    - Plugins:
        - [fbinz/django-components-preprocessor](https://github.com/fbinz/django-components-preprocessor)
        - [burakyilmaz321/django-components-storybook](https://github.com/burakyilmaz321/django-components-storybook)

    - Project starters
        - #TODOS
            - Reach out to them about creating new templates with my help
            - Create an "official" template for Django-components + Tailwind + AlpineJS
                - See https://github.com/KapStorm/django-components-poc
                - See https://github.com/Pourbaix/django-components-test
                - See https://github.com/LucasGrugru/django-components-todo
                - See https://github.com/aymericderbois/django-components-examples
                - See https://github.com/nax3t/django-alpine-popover-component/blob/main/main/components/popover/popover.py
        - [kodexArg/dj-apprunner-template](https://github.com/kodexArg/dj-apprunner-template)
        - [gone/django-hydra](https://github.com/gone/django-hydra/blob/f743935a4d75030ebaa3f422ec8d953fc5b6439c/template/uv.lock#L316)
        - [burakyilmaz321/django_parcel_boilerplate](https://github.com/burakyilmaz321/django_parcel_boilerplate/blob/761c68805b0bd9ab13d31480c862f53164f1a52c/config/loaders.py#L4)
        - [GreenDeploy-io/example-django-using-hypercomponents](https://github.com/GreenDeploy-io/example-django-using-hypercomponents/blob/90f5cc2991b4de434da337b21bec0df09cac8d25/requirements/base.in#L43)
        - [zft9xgy/todux](https://github.com/zft9xgy/todux/blob/659eeb4c489772380792359473c42d0c8968f613/templates/footer.html#L12)
        - [bingual/django-5.0](https://github.com/bingual/django-5.0/blob/48436d603ca0334459b85dcf7a1953e1e9a6f4d5/base/settings.py#L119)
        - [amanksdotdev/dhat-stack](https://github.com/amanksdotdev/dhat-stack/blob/004ce4766010a341afc98946a59fc5e7fdce7918/uv.lock#L20)
        - [daryabsb/hud](https://github.com/daryabsb/hud/blob/e668ae9533c2be7bfceb03eb4cd34b3e7795289c/src/requirements/requirements.in#L11)
        - [KapStorm/django-components-poc](https://github.com/KapStorm/django-components-poc/blob/1b1e444c09bcca937fe4c2b3a50e912aa75c581e/theme/static_src/tailwind.config.js#L44)
        - [pyhub-kr/course-django-complete-guide-v3](https://github.com/pyhub-kr/course-django-complete-guide-v3)
        - [jwalgran/dhc-base](https://github.com/jwalgran/dhc-base/blob/cda1587d0e9c981fe53c8a76ed411e3fad45a672/src/django/dhc/settings.py#L41)

    - Blog posts:
        - [benbacardi/benbacardi.github.io](https://github.com/benbacardi/benbacardi.github.io/blob/c83e871bfd4f25cd606b015f8f39e0f8b2c4c302/content/2025-03-24-birds-angles-django-components.md?plain=1#L9)
        - [pyvideo/data](https://github.com/pyvideo/data/blob/0a8a16ebf4e0931b1dddfa78e3252fbc5dc50cbb/djangocon-us-2024/videos/django-ui-components-for-perfectionists-with-deadlines.json#L2)
        - [dylanjcastillo/blog](https://github.com/dylanjcastillo/blog/blob/f49be925d18aa50ea67206f39aa44254eea17214/posts/2024-personal-snapshot.qmd#L33)
        - [KatherineMichel/portfolio](https://github.com/KatherineMichel/portfolio/blob/823f1c80d0743fd498ef1205ba92f8c2aedfc76e/doc/djangocon-us-2024-recap.md?plain=1#L301)

    - Component examples:
        - [iwanalabs/django-htmx-components](https://github.com/iwanalabs/django-htmx-components/blob/c613a55a74842bd2f1e2ec56c57d1281f1140ab8/src/templates/index.html#L47)
        - https://github.com/Westly93/django-components/tree/main
        - https://github.com/nax3t/django-alpine-popover-component/blob/main/main/components/popover/popover.py

    - Indices:
        - [pyhub-kr/django-pyhub-ai](https://github.com/pyhub-kr/django-pyhub-ai/blob/32d7602d7f8a0708dfe19337358e0a419b1c0fa6/docs/django/components/django-components/index.rst#L2)
        - [torchbox/django-pattern-library](https://github.com/torchbox/django-pattern-library/blob/018251208024dba4f0ca3878258cca69788364e9/docs/community/related-projects.md?plain=1#L9)
        - [trackawesomelist/trackawesomelist](https://github.com/trackawesomelist/trackawesomelist/blob/ab878fec5a5c306039c4f4e3a951ae5ccf4d2e3b/content/2025/03/16/README.md?plain=1#L116)
        - [fkromer/best-of-django](https://github.com/fkromer/best-of-django/blob/3f6fe9c76dbd4fc910db6ae14f80a9f245ba28d7/history/2025-05-22_changes.md?plain=1#L26)

    - Sponsors:
        - [om-proptech](https://github.com/om-proptech)
    - Potential sponsors:
        - [GreenDeploy-io](https://github.com/GreenDeploy-io)
        - [ibm-luq95/beachwoodfinancial](https://github.com/ibm-luq95/beachwoodfinancial/blob/4e5123ae2f4bde4a50e59c17633b46205f6a7d1d/requirements/_base.txt#L7) - https://beechwoodfs.co.uk/
        - [jwpconsulting/projectify](https://github.com/jwpconsulting/projectify/blob/f24b6f6a224214b510d3d2466c1523b63bc6a13d/docs/remove-fe-worklog.md?plain=1#L60) - https://www.projectifyapp.com/
        - https://github.com/django-cms
        - https://wagtail.org/ - https://github.com/tbrlpld/laces/discussions/35

    - Potential collaborators:
        - https://github.com/diefenbach - Author of diefenbach/djello
        - https://github.com/selimb - See https://github.com/selimb/cookie-odyssey/issues/10
        - https://github.com/kudah99
        - github.com/fbinz - Author of fbinz/django-components-preprocessor


### Data from grep.app

- `https://grep.app/search?q=django_components`
    - [barnslig/geheimvz](https://github.com/barnslig/geheimvz)
    - [TreyWW/MyFinances](https://github.com/TreyWW/MyFinances)
