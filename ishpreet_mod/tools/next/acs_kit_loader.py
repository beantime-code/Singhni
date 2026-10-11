"""Import the user's acs_kit (Duleep_Files/acs_kit) from wherever ishpreet_mod sits.

Search order: $ACS_KIT, Duleep_Files/acs_kit next to this ishpreet_mod folder, ~/mnt/Duleep_Files/acs_kit."""
import os
import sys


def load():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get('ACS_KIT'),
             os.path.join(here, '..', '..', '..', 'acs_kit'),
             os.path.expanduser('~/mnt/Duleep_Files/acs_kit')]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, 'acs_kit')):
            root = os.path.abspath(c)
            if root not in sys.path:
                sys.path.insert(0, root)
            from acs_kit import forge, paths
            return forge, paths
    raise SystemExit('acs_kit not found: set ACS_KIT to the folder that holds acs_kit/ (Duleep_Files/acs_kit)')
