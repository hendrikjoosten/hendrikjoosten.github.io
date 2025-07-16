---
layout: default
---

data is the way

## Blog Entries

<ul>
  {% assign blogs = site.pages | where_exp: "page", "page.path contains 'pages/blog'" %}
  {% for blog in blogs %}
    <li><a href="{{ blog.url }}">{{ blog.title }}</a> - <small>{{ blog.date | date: "%B %d, %Y" }}</small></li>
  {% endfor %}
</ul>
