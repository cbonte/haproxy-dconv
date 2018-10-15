"""
Methods to get the version tag of a git directory.
Really nothing's fancy here
"""

import os
import sys
import subprocess
import re

def get_git_version_from_cwd():
    """
    Fetch the last known version of the HAProxy current repository
    """
    return get_git_version_in_path(os.getcwd())


def get_git_version_in_path(path):
    """
    Fetch the last known version of the git repository given as an argument
    """
    if not path or not os.path.isdir(os.path.join(path,".git")):
        print("This does not appear to be a Git repository.", file=sys.stderr)
        return

    try:
        p = subprocess.Popen(["git", "describe", "--tags", "--match", "v*"],
                             cwd=path,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except EnvironmentError:
        return False
    version = p.communicate()[0]

    if p.returncode != 0:
        return False

    if len(version) < 2:
        return False

    version = version.decode().lstrip('v').rstrip()  # remove the 'v' tag and the EOL char
    version = re.sub(r'-g.*', '', version)
    return version