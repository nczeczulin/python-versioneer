
def compute_root():
    try:
        root = os.path.realpath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in versionfile_source.split('/'):
            root = os.path.dirname(root)
    except NameError:
        return None
    return root


def get_versions(default={"version": "0+unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded keywords.

    keywords = {"refnames": git_refnames, "full": git_full}
    data = git_versions_from_keywords(keywords, tag_prefix, verbose)

    if not data:
        root = compute_root()
        if not root:
            data = default

    if not data:
        data = git_versions_from_vcs(tag_prefix, root, verbose)
    if not data:
        data = versions_from_parentdir(parentdir_prefix, root, verbose)
    if not data:
        data = default
    return add_template_keys(data)
