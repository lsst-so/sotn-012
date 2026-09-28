# See the Documenteer docs for how to customize conf.py:
# https://documenteer.lsst.io/technotes/

from documenteer.conf.technote import *  # noqa F401 F403

# Analysis notebooks and their notes/plots are not part of the technote source.
exclude_patterns = [*globals().get("exclude_patterns", []), "notebooks"]
