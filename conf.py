# See the Documenteer docs for how to customize conf.py:
# https://documenteer.lsst.io/technotes/

from documenteer.conf.technote import *  # noqa F401 F403

# Analysis notebooks and their notes/plots are not part of the technote source.
exclude_patterns = [*globals().get("exclude_patterns", []), "notebooks"]

# Standalone interactive (Bokeh) figures, copied as-is to the site root and
# embedded in index.md with <iframe>.
html_extra_path = ["_extra"]

# Widen the body column (see _static/technote-overrides.css). Appending keeps
# documenteer's own static paths and stylesheets; ours is listed last so it
# loads after the theme's and wins.
html_static_path = [*globals().get("html_static_path", []), "_static"]
html_css_files = [*globals().get("html_css_files", []), "technote-overrides.css"]
