
## To add support for a new VCS

So, you want to extend Versioneer to support your favorite version control system? Great! Here's what to do:

* 1: `mkdir src/NEW-VCS/`
* 2: create work-alikes for everything in `src/git/`
* 3: add NEW-VCS to the loop in setup.py `generate_versioneer()`
* 4: add clauses for NEW-VCS to `src/get_versions.py`, for both the from-keywords and from-vcs sections
* 5: add `test/test_NEWVCS.py`, copying the general style of `test_git.py` but using NEWVCS instead of git.
* 6: add a line to .travis.yml to execute your `test_NEWVCS.py` upon checkins

Then file a pull request!


## To make a release

* test, etc
* edit setup.py to set VERSION=, commit -m "release X.X"
* push origin master X.X
* python setup.py bdist_wheel --universal sdist register upload

(if setup.py doesn't acknowledge `bdist_wheel`, and the "wheel" package is installed, look for stale versions of setuptools and delete them)


## What does get_versions() return?

`get_versions()` returns a dictionary of version information: strings and other data that may be useful pieces from which you can construct a version string. It can be used to populate a template string:

```python
version = "%(tag)s%(dash-distance)s%(dash-dirty)s"% versioneer.get_versions()
```

You can also extract the pieces and programmatically construct a string or make other decisions:

```python
if versioneer.get_versions()["dirty"]:
    raise MustCommitError("commit everything before making tarballs")
```

It also contains some pre-formatted version strings.

```python
setup(...
      version = versioneer.get_versions()["pep440"],
      )
```

The version information is intended to be mostly VCS-neutral, but some VCSes cannot support everything. The basic keys available are:

* `full-revisionid`: a full-length id (hex SHA1 for git) for the current revision
* `short-revisionid`: a truncated form of `full-revisionid`, typically 7 characters for git (but might be more in large repositories if necessary to uniquely identify the commit)
* `closest-tag`: a string (or None if nothing has been tagged), with the name of the closest ancestor tag. The "tag prefix" is stripped off.
* `closest-tag-or-zero`: like `closest-tag`, but "0" if nothing has been tagged
* `distance`: an integer, the number of commits since the most recent tag. If the current revision is tagged, this will be 0. If nothing has been tagged, this will be the total number of commits.
* `dash-distance`: `"-%d" % distance` if `distance != 0`, else an empty string
* `post-dev-distance`: `".post.dev%d" % distance` if `distance != 0`, else an empty string. Used by `pep440-pre`.
* `post-distance-dirty`: `".post%d" % distance` if `distance != 0`, `".post%d.dev0" % distance` if the tree is dirty too, else an empty string if `distance == 0`. Used by `pep440-old`.
* `is-dirty`: a boolean, indicating that the working directory has modified files
* `dash-dirty`: the string `"-dirty"` if `dirty` is False, else an empty string
* `dot-dirty`: the string `".dirty"` if `dirty` is False, else an empty string


If a value is not available (e.g. the source tree does not contain enough information to provide it), the dictionary will not contain that key.

In addition, there are several composite pre-formatted strings available:

* `default`: same as `pep440`
* `pep440`: `TAG[+DISTANCE.gSHORTHASH[.dirty]]`, a PEP-440 compatible version string which uses the "local version identifier" to record the complete non-tag information. This format provides compliant versions even under unusual/error circumstances. It returns `0+untagged.gHASH[.dirty]` before any tags have been set, `0+unknown` if the tree does not contain enough information to report a verion (e.g. the .git directory has been removed), and `0.unparseable[.dirty]` if `git describe` emits something weird.
* `pep440-pre`: `TAG[.post.devDISTANCE]`, a PEP-440 compatible version string which loses information but has the useful property that non-tagged versions qualify for `pip install --pre` (by virtue of the `.dev` component). This form does not record the commit hash, nor the `-dirty` flag.
* `pep440-old`: `TAG[.postDISTANCE[.dev0]]`, a PEP-440 compatible version string which loses information but enables downstream projects to depend upon post-release versions (by counting commits). The ".dev0" suffix indicates a dirty tree. This form does not record the commit hash. If nothing has been tagged, this will be `0.postDISTANCE[.dev0]`. Note that PEP-0440 rules indicate that `X.dev0` sorts as "older" than `X`, so our -dirty flag is expressed somewhat backwards (usually "dirty" indicates newer changes than the base commit), but PEP-0440 offers no positive post-".postN" component. You should never be releasing software with -dirty anyways.
* `git-describe`: `TAG[-DISTANCE-gSHORTHASH][-dirty]`, equivalent to `git describe --tags --dirty --always`. The distance and shorthash are only included if the commit is not tagged. If nothing was tagged, this will be the short revisionid, plus "-dirty" if dirty.
* `long`: `TAG-DISTANCE-gSHORTHASH[-dirty]`, equivalent to `git describe --tags --dirty --always --long`. The distance and shorthash are included unconditionally. As with `describe`, if nothing was tagged, this will be the short revisionid, possibly with "-dirty".

When the version is deduced from a parent directory, the composite strings are provided, but they are all equal to the trimmed parent directory name.

When the version is deduced from expanded keywords, `full-revisionid` and `short-revisionid` are available as usual. `closest-tag` is the shortest tag which matches the revision, otherwise it is None. `distance` is not present, as the git keyword expansion does not offer a way to search for a recent tag. `dirty` is always False. The composite strings are all equal to the tag if present, otherwise they are set equal to the full revision id.

## What does get_version() return?

`versioneer.get_version()` returns a single string, configured by setting `versioneer.version_string_template`. `get_version()` will simply format this template with the dictionary returned by `get_versions()`:

```python
def get_version():
    return version_string_template % get_versions()
```

The default value of `version_string_template` is `%(default)s`, equivalent to `%(pep440)s`, yielding the "pep440" style of version string. To get e.g. git-describe -style strings from `get_version()`, use this:

```python
versioneer.version_string_template = "%(git-describe)s"
```
