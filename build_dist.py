"""Build dist/ for Netlify: inject precomputed data into the static site template.

Run after precompute.py:  python build_dist.py
"""

import json
import os

with open("dist_data.json") as f:
    data = f.read()
json.loads(data)  # validate

template = open("site_template.html").read()
html = template.replace("__DATA__", data.replace("</", "<\\/"))

os.makedirs("dist", exist_ok=True)
with open("dist/index.html", "w") as f:
    f.write(html)
print(f"Wrote dist/index.html ({len(html) / 1024:.0f} KB)")
