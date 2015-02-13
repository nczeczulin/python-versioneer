import re # --STRIP DURING BUILD

def git_parse_vcs_describe(git_describe, tag_prefix, verbose=False):
    # TAG-NUM-gHEX[-dirty] or HEX[-dirty] . TAG might have hyphens.

    # dirty
    dirty = git_describe.endswith("-dirty")
    if dirty:
        git_describe = git_describe[:git_describe.rindex("-dirty")]
    dirty_suffix = ".dirty" if dirty else ""

    # now we have TAG-NUM-gHEX or HEX

    if "-" not in git_describe:  # just HEX
        return {"short-revisionid": git_describe,
                "closest-tag": None,
                "is-dirty": dirty}

    # just TAG-NUM-gHEX
    mo = re.search(r'^(.+)-(\d+)-g([0-9a-f]+)$', git_describe)
    if not mo:
        # unparseable. Maybe git-describe is misbehaving?
        raise ValueError

    # tag
    full_tag = mo.group(1)
    if full_tag.startswith(tag_prefix):
        tag = full_tag[len(tag_prefix):]
    else:
        if verbose:
            fmt = "tag '%s' doesn't start with prefix '%s'"
            print(fmt % (full_tag, tag_prefix))
        tag = None

    # distance: number of commits since tag
    distance = int(mo.group(2))

    # commit: short hex revision ID
    commit = mo.group(3)

    return {"is-dirty": dirty,
            "closest-tag": tag,
            "distance": distance,
            "short-revisionid": commit,
            }


def git_versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' keywords were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}  # get_versions() will try next method

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    # if there is a tag, this yields TAG-NUM-gHEX[-dirty]
    # if there are no tags, this yields HEX[-dirty] (no NUM)
    stdout = run_command(GITS, ["describe", "--tags", "--dirty",
                                "--always", "--long"],
                         cwd=root)
    # --long was added in git-1.5.5
    if stdout is None:
        return {}  # try next method
    try:
        p = git_parse_vcs_describe(stdout, tag_prefix, verbose).copy()
    except ValueError:
        return {"pep440": "0+unparseable"}

    if p["closest-tag"] is None:
        p["closest-tag-or-zero"] = "0"
    else:
        p["closest-tag-or-zero"] = p["closest-tag"]
    if "distance" in p:
        if p["distance"]:
            # non-zero
            p["dash-distance"] = "-%d" % p["distance"]
        else:
            p["dash-distance"] = ""
    if p["is-dirty"]:
        p["dash-dirty"] = "-dirty"
        p["dot-dirty"] = ".dirty"
    else:
        p["dash-dirty"] = ""
        p["dot-dirty"] = ""

    # build "full", which is FULLHEX[.dirty]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    p["full-revisionid"] = stdout.strip()

    # now build up version string, with post-release "local version
    # identifier". Our goal: TAG[+NUM.gHEX[.dirty]] . Note that if you get a
    # tagged build and then dirty it, you'll get TAG+0.gHEX.dirty . So you
    # can always test version.endswith(".dirty").

    if not p["closest-tag"]:
        pep440 = "0+untagged.g%(short-revisionid)s%(dot-dirty)s" % p
    else:
        pep440 = p["closest-tag-or-zero"]
        if p["distance"] or p["is-dirty"]:
            pep440 += "+%(distance)d.g%(short-revisionid)s%(dot-dirty)s" % p
    full = "%(full-revisionid)s%(dot-dirty)s" % p

    return {"version": pep440, "full": full}

