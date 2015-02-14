
def add_template_keys(p):
    # possible incoming keys: unparseable, is-dirty, closest-tag, distance,
    # short-revisionid, long-revisionid
    p = p.copy()

    if p.get("version"):
        # the source pre-computed a version for us, implying that nothing
        # else is available. Use it as-is.
        return p

    if p.get("unparseable"):
        return {"pep440": "0+unparseable"}

    if "long-revisionid" in p and "short-revisionid" not in p:
        p["short-revisionid"] = p["long-revisionid"][:7]

    if p.get("closest-tag", None) is None:
        p["closest-tag-or-zero"] = "0"
    else:
        p["closest-tag-or-zero"] = p["closest-tag"]
    if "distance" in p:
        if p["distance"]:
            # non-zero
            p["dash-distance"] = "-%d" % p["distance"]
        else:
            p["dash-distance"] = ""
    if "is-dirty" in p:
        if p["is-dirty"]:
            p["dash-dirty"] = "-dirty"
            p["dot-dirty"] = ".dirty"
        else:
            p["dash-dirty"] = ""
            p["dot-dirty"] = ""

    # now build up version string, with post-release "local version
    # identifier". Our goal: TAG[+NUM.gHEX[.dirty]] . Note that if you get a
    # tagged build and then dirty it, you'll get TAG+0.gHEX.dirty . So you
    # can always test version.endswith(".dirty").

    if p.get("closest-tag"):
        pep440 = p["closest-tag"]
        if p["distance"] or p.get("is-dirty", False):
            pep440 += "+%d" % p["distance"]
            pep440 += ".g" + p["short-revisionid"]
            if p.get("is-dirty", False):
                pep440 += ".dirty"
        p["pep440"] = pep440

        pep440pre = p["closest-tag"]
        if p["distance"]:
            pep440pre += ".post.dev%d" % p["distance"]
        p["pep440pre"] = pep440pre

        pep440post = p["closest-tag"]
        if p["distance"] or p.get("is-dirty", False):
            pep440post += ".post%d" % p["distance"]
            if p.get("is-dirty", False):
                pep440post += ".dev0"
            pep440post += "+g" + p["short-revisionid"]
        p["pep440post"] = pep440post

        git_describe = p["closest-tag"]
        if p["distance"]:
            git_describe += "-%d-g%s" % (p["distance"],
                                         p["short-revisionid"])
        if p["is-dirty"]:
            git_describe += "-dirty"
        p["git-describe"] = git_describe

    else:
        pep440 = "0+untagged"
        if "short-revisionid" in p:
            pep440 += ".g" + p["short-revisionid"]
        if p.get("is-dirty", False):
            pep440 += ".dirty"
        p["pep440"] = pep440

        git_describe = p["short-revisionid"]
        if p["is-dirty"]:
            git_describe += "-dirty"
        p["git-describe"] = git_describe

    if "long-revisionid" in p:
        full = p["long-revisionid"]
        if p.get("is-dirty", False):
            full += ".dirty"
        p["full"] = full

    p["version"] = p["pep440"]
    return p

