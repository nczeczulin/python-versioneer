
def get_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[0]))


def vcs_function(vcs, suffix):
    return getattr(sys.modules[__name__], '%s_%s' % (vcs, suffix), None)


def get_versions(default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    assert versionfile_source is not None, \
        "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, \
        "please set versioneer.parentdir_prefix"
    assert VCS is not None, "please set versioneer.VCS"

    # I am in versioneer.py, which must live at the top of the source tree,
    # which we use to compute the root directory. py2exe/bbfreeze/non-CPython
    # don't have __file__, in which case we fall back to sys.argv[0] (which
    # ought to be the setup.py script). We prefer __file__ since that's more
    # robust in cases where setup.py was invoked in some weird way (e.g. pip)
    root = get_root()
    versionfile_abs = os.path.join(root, versionfile_source)

    data = {}
    data_from = ""

    # extract version data from the first successful method of this list:
    #  * _version.py
    #  * VCS command (e.g. 'git describe')
    #  * parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature or the equivalent in other VCSes.

    get_keywords_f = vcs_function(VCS, "get_keywords")
    versions_from_keywords_f = vcs_function(VCS, "versions_from_keywords")
    versions_from_vcs_f = vcs_function(VCS, "versions_from_vcs")

    if not data and get_keywords_f and versions_from_keywords_f:
        keywords = get_keywords_f(versionfile_abs)
        data = versions_from_keywords_f(keywords, tag_prefix)
        data_from = "expanded keywords"

    if not data:
        data = versions_from_file(versionfile_abs)
        data_from = "file %s" % versionfile_abs

    if not data and versions_from_vcs_f:
        data = versions_from_vcs_f(tag_prefix, root, verbose)
        data_from = "VCS"

    if not data:
        data = versions_from_parentdir(parentdir_prefix, root, verbose)
        data_from = "parentdir"

    if not data:
        data = DEFAULT
        data_from = "default"

    if verbose:
        print("got version from %s: %s" % (data_from, data))

    return add_template_keys(data)


def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]
