#! /usr/bin/python

from __future__ import print_function
import os, sys
import shutil
import tarfile
import unittest
import tempfile
from pkg_resources import parse_version, SetuptoolsLegacyVersion

sys.path.insert(0, "src")
from render import render
from from_file import versions_from_file
from git import from_vcs, from_keywords
from subprocess_helper import run_command

pyver = "py%d.%d" % sys.version_info[:2]

GITS = ["git"]
if sys.platform == "win32":
    GITS = ["git.cmd", "git.exe"]

class ParseGitDescribe(unittest.TestCase):
    def setUp(self):
        self.fakeroot = tempfile.mkdtemp()
        self.fakegit = os.path.join(self.fakeroot, ".git")
        os.mkdir(self.fakegit)

    def test_pieces(self):
        def pv(git_describe, do_error=False, expect_pieces=False):
            def fake_run_command(exes, args, cwd=None):
                if args[0] == "describe":
                    if do_error == "describe":
                        return None
                    return git_describe+"\n"
                if args[0] == "rev-parse":
                    if do_error == "rev-parse":
                        return None
                    return "longlong\n"
                if args[0] == "rev-list":
                    return "42\n"
                self.fail("git called in weird way: %s" % (args,))
            return from_vcs.git_pieces_from_vcs(
                "v", self.fakeroot, verbose=False,
                run_command=fake_run_command)
        self.assertRaises(from_vcs.NotThisMethod,
                          pv, "ignored", do_error="describe")
        self.assertRaises(from_vcs.NotThisMethod,
                          pv, "ignored", do_error="rev-parse")
        self.assertEqual(pv("1f"),
                         {"closest-tag": None, "dirty": False, "error": None,
                          "distance": 42,
                          "long": "longlong",
                          "short": "longlon"})
        self.assertEqual(pv("1f-dirty"),
                         {"closest-tag": None, "dirty": True, "error": None,
                          "distance": 42,
                          "long": "longlong",
                          "short": "longlon"})
        self.assertEqual(pv("v1.0-0-g1f"),
                         {"closest-tag": "1.0", "dirty": False, "error": None,
                          "distance": 0,
                          "long": "longlong",
                          "short": "1f"})
        self.assertEqual(pv("v1.0-0-g1f-dirty"),
                         {"closest-tag": "1.0", "dirty": True, "error": None,
                          "distance": 0,
                          "long": "longlong",
                          "short": "1f"})
        self.assertEqual(pv("v1.0-1-g1f"),
                         {"closest-tag": "1.0", "dirty": False, "error": None,
                          "distance": 1,
                          "long": "longlong",
                          "short": "1f"})
        self.assertEqual(pv("v1.0-1-g1f-dirty"),
                         {"closest-tag": "1.0", "dirty": True, "error": None,
                          "distance": 1,
                          "long": "longlong",
                          "short": "1f"})

    def tearDown(self):
        os.rmdir(self.fakegit)
        os.rmdir(self.fakeroot)


class Keywords(unittest.TestCase):
    def parse(self, refnames, full, prefix=""):
        return from_keywords.git_versions_from_keywords(
            {"refnames": refnames, "full": full}, prefix, False)

    def test_parse(self):
        v = self.parse(" (HEAD, 2.0,master  , otherbranch ) ", " full ")
        self.assertEqual(v["version"], "2.0")
        self.assertEqual(v["full-revisionid"], "full")
        self.assertEqual(v["dirty"], False)
        self.assertEqual(v["error"], None)

    def test_prefer_short(self):
        v = self.parse(" (HEAD, 2.0rc1, 2.0, 2.0rc2) ", " full ")
        self.assertEqual(v["version"], "2.0")
        self.assertEqual(v["full-revisionid"], "full")
        self.assertEqual(v["dirty"], False)
        self.assertEqual(v["error"], None)

    def test_prefix(self):
        v = self.parse(" (HEAD, projectname-2.0) ", " full ", "projectname-")
        self.assertEqual(v["version"], "2.0")
        self.assertEqual(v["full-revisionid"], "full")
        self.assertEqual(v["dirty"], False)
        self.assertEqual(v["error"], None)

    def test_unexpanded(self):
        self.assertRaises(from_keywords.NotThisMethod,
                          self.parse, " $Format$ ", " full ", "projectname-")

    def test_no_tags(self):
        v = self.parse("(HEAD, master)", "full")
        self.assertEqual(v["version"], "0+unknown")
        self.assertEqual(v["full-revisionid"], "full")
        self.assertEqual(v["dirty"], False)
        self.assertEqual(v["error"], "no suitable tags")

    def test_no_prefix(self):
        v = self.parse("(HEAD, master, 1.23)", "full", "missingprefix-")
        self.assertEqual(v["version"], "0+unknown")
        self.assertEqual(v["full-revisionid"], "full")
        self.assertEqual(v["dirty"], False)
        self.assertEqual(v["error"], "no suitable tags")

expected_renders = """
closest-tag: 1.0
distance: 0
dirty: False
pep440: 1.0
pep440-pre: 1.0
pep440-post: 1.0
pep440-old: 1.0
git-describe: 1.0
git-describe-long: 1.0-0-g250b7ca

closest-tag: 1.0
distance: 0
dirty: True
pep440: 1.0+0.g250b7ca.dirty
pep440-pre: 1.0
pep440-post: 1.0.post0.dev0+g250b7ca
pep440-old: 1.0.post0.dev0
git-describe: 1.0-dirty
git-describe-long: 1.0-0-g250b7ca-dirty

closest-tag: 1.0
distance: 1
dirty: False
pep440: 1.0+1.g250b7ca
pep440-pre: 1.0.post.dev1
pep440-post: 1.0.post1+g250b7ca
pep440-old: 1.0.post1
git-describe: 1.0-1-g250b7ca
git-describe-long: 1.0-1-g250b7ca

closest-tag: 1.0
distance: 1
dirty: True
pep440: 1.0+1.g250b7ca.dirty
pep440-pre: 1.0.post.dev1
pep440-post: 1.0.post1.dev0+g250b7ca
pep440-old: 1.0.post1.dev0
git-describe: 1.0-1-g250b7ca-dirty
git-describe-long: 1.0-1-g250b7ca-dirty


closest-tag: 1.0+plus
distance: 1
dirty: False
pep440: 1.0+plus.1.g250b7ca
pep440-pre: 1.0+plus.post.dev1
pep440-post: 1.0+plus.post1.g250b7ca
pep440-old: 1.0+plus.post1
git-describe: 1.0+plus-1-g250b7ca
git-describe-long: 1.0+plus-1-g250b7ca

closest-tag: 1.0+plus
distance: 1
dirty: True
pep440: 1.0+plus.1.g250b7ca.dirty
pep440-pre: 1.0+plus.post.dev1
pep440-post: 1.0+plus.post1.dev0.g250b7ca
pep440-old: 1.0+plus.post1.dev0
git-describe: 1.0+plus-1-g250b7ca-dirty
git-describe-long: 1.0+plus-1-g250b7ca-dirty


closest-tag: None
distance: 1
dirty: False
pep440: 0+untagged.1.g250b7ca
pep440-pre: 0.post.dev1
pep440-post: 0.post1+g250b7ca
pep440-old: 0.post1
git-describe: 250b7ca
git-describe-long: 250b7ca

closest-tag: None
distance: 1
dirty: True
pep440: 0+untagged.1.g250b7ca.dirty
pep440-pre: 0.post.dev1
pep440-post: 0.post1.dev0+g250b7ca
pep440-old: 0.post1.dev0
git-describe: 250b7ca-dirty
git-describe-long: 250b7ca-dirty

"""

class RenderPieces(unittest.TestCase):
    def do_render(self, pieces):
        out = {}
        for style in ["pep440", "pep440-pre", "pep440-post", "pep440-old",
                      "git-describe", "git-describe-long"]:
            out[style] = render(pieces, style)["version"]
        DEFAULT = "pep440"
        self.assertEqual(render(pieces, ""), render(pieces, DEFAULT))
        self.assertEqual(render(pieces, "default"), render(pieces, DEFAULT))
        return out

    def parse_expected(self):
        base_pieces = {"long": "250b7ca731388d8f016db2e06ab1d6289486424b",
                       "short": "250b7ca",
                       "error": None}
        more_pieces = {}
        expected = {}
        for line in expected_renders.splitlines():
            line = line.strip()
            if not line:
                if more_pieces and expected:
                    pieces = base_pieces.copy()
                    pieces.update(more_pieces)
                    yield (pieces, expected)
                more_pieces = {}
                expected = {}
                continue
            name, value = line.split(":")
            name = name.strip()
            value = value.strip()
            if name == "distance":
                more_pieces["distance"] = int(value)
            elif name == "dirty":
                more_pieces["dirty"] = bool(value.lower() == "true")
            elif name == "closest-tag":
                more_pieces["closest-tag"] = value
                if value == "None":
                    more_pieces["closest-tag"] = None
            else:
                expected[name] = value
        if more_pieces and expected:
            pieces = base_pieces.copy()
            pieces.update(more_pieces)
            yield (pieces, expected)

    def test_render(self):
        for (pieces, expected) in self.parse_expected():
            got = self.do_render(pieces)
            for key in expected:
                self.assertEqual(got[key], expected[key],
                                 (pieces, key, got[key], expected[key]))


VERBOSE = False

class _Common:
    def command(self, cmd, *args, **kwargs):
        workdir = kwargs.pop("workdir", self.subpath("demoapp"))
        assert not kwargs, kwargs.keys()
        print("COMMAND:", [cmd]+list(args))
        output = run_command([cmd], list(args), workdir, True)
        if output is None:
            self.fail("problem running command %s" % ([cmd]+list(args),))
        return output
    def git(self, *args, **kwargs):
        workdir = kwargs.pop("workdir", self.subpath("demoapp"))
        assert not kwargs, kwargs.keys()
        #print("git", *(args + (workdir,)))
        output = run_command(GITS, list(args), workdir, True)
        if output is None:
            self.fail("problem running git")
        return output
    def python(self, *args, **kwargs):
        workdir = kwargs.pop("workdir", self.subpath("demoapp"))
        #print("python", *(args + (workdir,)))
        exe = kwargs.pop("python", sys.executable)
        assert not kwargs, kwargs.keys()
        output = run_command([exe], list(args), workdir, True)
        if output is None:
            self.fail("problem running python")
        return output
    def subpath(self, *path):
        return os.path.join(self.testdir, *path)

class Repo(unittest.TestCase, _Common):

    # There are three tree states we're interested in:
    #  S1: sitting on the initial commit, no tags
    #  S2: dirty tree after the initial commit
    #  S3: sitting on the 1.0 tag
    #  S4: dirtying the tree after 1.0
    #  S5: making a new commit after 1.0, clean tree
    #  S6: dirtying the tree after the post-1.0 commit
    #
    # Then we're interested in 7 kinds of trees:
    #  TA: source tree (with .git)
    #  TB: source tree without .git (should get 'unknown')
    #  TC: source tree without .git unpacked into prefixdir
    #  TD: git-archive tarball
    #  TE: unpacked sdist tarball
    #  TF: installed sdist tarball (RB only)
    #  TG: installed bdist_wheel (RB only)
    #  TH: installed egg (RB only)
    #
    # In three runtime situations:
    #  RA1: setup.py --version
    #  RA2: ...path/to/setup.py --version (from outside the source tree)
    #  RB: setup.py build;  rundemo --version
    #
    # We can only detect dirty files in real git trees, so we don't examine
    # S2/S4/S6 for TB/TC/TD/TE, or RB.

    # note that the repo being manipulated is always named "demoapp",
    # regardless of which source directory we copied it from (test/demoapp/
    # or test/demoapp-script-only/)

    def test_full(self):
        self.run_test("test/demoapp", False)

    def test_script_only(self):
        # This test looks at an application that consists entirely of a
        # script: no libraries (so its setup.py has packages=[]). This sort
        # of app cannot be run from source: you must 'setup.py build' to get
        # anything executable. So of the 3 runtime situations examined by
        # Repo.test_full above, we only care about RB. (RA1 is valid too, but
        # covered by Repo).
        self.run_test("test/demoapp-script-only", True)

    def run_test(self, demoapp_dir, script_only):
        self.testdir = tempfile.mkdtemp()
        if VERBOSE: print("testdir: %s" % (self.testdir,))
        if os.path.exists(self.testdir):
            shutil.rmtree(self.testdir)

        # create an unrelated git tree above the testdir. Some tests will run
        # from this directory, and they should use the demoapp git
        # environment instead of the deceptive parent
        os.mkdir(self.testdir)
        self.git("init", workdir=self.testdir)
        f = open(os.path.join(self.testdir, "false-repo"), "w")
        f.write("don't look at me\n")
        f.close()
        self.git("add", "false-repo", workdir=self.testdir)
        self.git("commit", "-m", "first false commit", workdir=self.testdir)
        self.git("tag", "demo-4.0", workdir=self.testdir)

        shutil.copytree(demoapp_dir, self.subpath("demoapp"))
        setup_cfg_fn = os.path.join(self.subpath("demoapp"), "setup.cfg")
        with open(setup_cfg_fn, "r") as f:
            setup_cfg = f.read()
        setup_cfg = setup_cfg.replace("@VCS@", "git")
        with open(setup_cfg_fn, "w") as f:
            f.write(setup_cfg)
        shutil.copyfile("versioneer.py", self.subpath("demoapp/versioneer.py"))
        self.git("init")
        self.git("add", "--all")
        self.git("commit", "-m", "comment")

        full = self.git("rev-parse", "HEAD")
        v = self.python("setup.py", "--version")
        self.assertEqual(v, "0+untagged.1.g%s" % full[:7])
        v = self.python(os.path.join(self.subpath("demoapp"), "setup.py"),
                        "--version", workdir=self.testdir)
        self.assertEqual(v, "0+untagged.1.g%s" % full[:7])

        out = self.python("versioneer.py", "setup").splitlines()
        self.assertEqual(out[0], "creating src/demo/_version.py")
        if script_only:
            self.assertEqual(out[1], " src/demo/__init__.py doesn't exist, ok")
        else:
            self.assertEqual(out[1], " appending to src/demo/__init__.py")
        self.assertEqual(out[2], " appending 'versioneer.py' to MANIFEST.in")
        self.assertEqual(out[3], " appending versionfile_source ('src/demo/_version.py') to MANIFEST.in")
        out = set(self.git("status", "--porcelain").splitlines())
        # Many folks have a ~/.gitignore with ignores .pyc files, but if they
        # don't, it will show up in the status here. Ignore it.
        out.discard("?? versioneer.pyc")
        out.discard("?? __pycache__/")
        expected = set(["A  .gitattributes",
                        "M  MANIFEST.in",
                        "A  src/demo/_version.py"])
        if not script_only:
            expected.add("M  src/demo/__init__.py")
        self.assertEqual(out, expected)
        if not script_only:
            f = open(self.subpath("demoapp/src/demo/__init__.py"))
            i = f.read().splitlines()
            f.close()
            self.assertEqual(i[-3], "from ._version import get_versions")
            self.assertEqual(i[-2], "__version__ = get_versions()['version']")
            self.assertEqual(i[-1], "del get_versions")
        self.git("commit", "-m", "add _version stuff")

        # "versioneer.py setup" should be idempotent
        out = self.python("versioneer.py", "setup").splitlines()
        self.assertEqual(out[0], "creating src/demo/_version.py")
        if script_only:
            self.assertEqual(out[1], " src/demo/__init__.py doesn't exist, ok")
        else:
            self.assertEqual(out[1], " src/demo/__init__.py unmodified")
        self.assertEqual(out[2], " 'versioneer.py' already in MANIFEST.in")
        self.assertEqual(out[3], " versionfile_source already in MANIFEST.in")
        out = set(self.git("status", "--porcelain").splitlines())
        out.discard("?? versioneer.pyc")
        out.discard("?? __pycache__/")
        self.assertEqual(out, set([]))

        UNABLE = "unable to compute version"
        NOTAG = "no suitable tags"

        # S1: the tree is sitting on a pre-tagged commit
        full = self.git("rev-parse", "HEAD")
        short = "0+untagged.2.g%s" % full[:7]
        self.do_checks("S1", {"TA": [short, full, False, None],
                              "TB": ["0+unknown", None, None, UNABLE],
                              "TC": [short, full, False, None],
                              "TD": ["0+unknown", full, False, NOTAG],
                              "TE": [short, full, False, None],
                              "TF": [short, full, False, None],
                              })

        # TD: expanded keywords only tell us about tags and full revisionids,
        # not how many patches we are beyond a tag. So any TD git-archive
        # tarball from a non-tagged version will give us an error. "dirty" is
        # False, since the tree from which the tarball was created is
        # necessarily clean.

        # S2: dirty the pre-tagged tree
        f = open(self.subpath("demoapp/setup.py"),"a")
        f.write("# dirty\n")
        f.close()
        full = self.git("rev-parse", "HEAD")
        short = "0+untagged.2.g%s.dirty" % full[:7]
        self.do_checks("S2", {"TA": [short, full, True, None],
                              "TB": ["0+unknown", None, None, UNABLE],
                              "TC": [short, full, True, None],
                              "TD": ["0+unknown", full, False, NOTAG],
                              "TE": [short, full, True, None],
                              "TF": [short, full, True, None],
                              })

        # S3: we commit that change, then make the first tag (1.0)
        self.git("add", "setup.py")
        self.git("commit", "-m", "dirty")
        self.git("tag", "demo-1.0")
        full = self.git("rev-parse", "HEAD")
        short = "1.0"
        if VERBOSE: print("FULL %s" % full)
        # the tree is now sitting on the 1.0 tag
        self.do_checks("S3", {"TA": [short, full, False, None],
                              "TB": ["0+unknown", None, None, UNABLE],
                              "TC": [short, full, False, None],
                              "TD": [short, full, False, None],
                              "TE": [short, full, False, None],
                              "TF": [short, full, False, None],
                              })

        # S4: now we dirty the tree
        f = open(self.subpath("demoapp/setup.py"),"a")
        f.write("# dirty\n")
        f.close()
        full = self.git("rev-parse", "HEAD")
        short = "1.0+0.g%s.dirty" % full[:7]
        self.do_checks("S4", {"TA": [short, full, True, None],
                              "TB": ["0+unknown", None, None, UNABLE],
                              "TC": [short, full, True, None],
                              "TD": ["1.0", full, False, None],
                              "TE": [short, full, True, None],
                              "TF": [short, full, True, None],
                              })

        # S5: now we make one commit past the tag
        self.git("add", "setup.py")
        self.git("commit", "-m", "dirty")
        full = self.git("rev-parse", "HEAD")
        short = "1.0+1.g%s" % full[:7]
        self.do_checks("S5", {"TA": [short, full, False, None],
                              "TB": ["0+unknown", None, None, UNABLE],
                              "TC": [short, full, False, None],
                              "TD": ["0+unknown", full, False, NOTAG],
                              "TE": [short, full, False, None],
                              "TF": [short, full, False, None],
                              })

        # S6: dirty the post-tag tree
        f = open(self.subpath("demoapp/setup.py"),"a")
        f.write("# more dirty\n")
        f.close()
        full = self.git("rev-parse", "HEAD")
        short = "1.0+1.g%s.dirty" % full[:7]
        self.do_checks("S6", {"TA": [short, full, True, None],
                              "TB": ["0+unknown", None, None, UNABLE],
                              "TC": [short, full, True, None],
                              "TD": ["0+unknown", full, False, NOTAG],
                              "TE": [short, full, True, None],
                              "TF": [short, full, True, None],
                              })


    def do_checks(self, state, exps):
        if os.path.exists(self.subpath("out")):
            shutil.rmtree(self.subpath("out"))
        # TA: source tree
        self.check_version(self.subpath("demoapp"), state, "TA", exps["TA"])

        # TB: .git-less copy of source tree
        target = self.subpath("out/demoapp-TB")
        shutil.copytree(self.subpath("demoapp"), target)
        shutil.rmtree(os.path.join(target, ".git"))
        self.check_version(target, state, "TB", exps["TB"])

        # TC: source tree in versionprefix-named parentdir
        target = self.subpath("out/demo-1.1")
        shutil.copytree(self.subpath("demoapp"), target)
        shutil.rmtree(os.path.join(target, ".git"))
        self.check_version(target, state, "TC", ["1.1", None, False, None]) # XXX

        # TD: unpacked git-archive tarball
        target = self.subpath("out/TD/demoapp-TD")
        self.git("archive", "--format=tar", "--prefix=demoapp-TD/",
                 "--output=../demo.tar", "HEAD")
        os.mkdir(self.subpath("out/TD"))
        t = tarfile.TarFile(self.subpath("demo.tar"))
        t.extractall(path=self.subpath("out/TD"))
        t.close()
        self.check_version(target, state, "TD", exps["TD"])

        # TE: unpacked setup.py sdist tarball
        if os.path.exists(self.subpath("demoapp/dist")):
            shutil.rmtree(self.subpath("demoapp/dist"))
        self.python("setup.py", "sdist", "--formats=tar")
        files = os.listdir(self.subpath("demoapp/dist"))
        self.assertTrue(len(files)==1, files)
        distfile = files[0]
        self.assertEqual(distfile, "demo-%s.tar" % exps["TE"][0])
        fn = os.path.join(self.subpath("demoapp/dist"), distfile)
        os.mkdir(self.subpath("out/TE"))
        t = tarfile.TarFile(fn)
        t.extractall(path=self.subpath("out/TE"))
        t.close()
        target = self.subpath("out/TE/demo-%s" % exps["TE"][0])
        self.assertTrue(os.path.isdir(target))
        self.check_version(target, state, "TE", exps["TE"])

        # TF: installed sdist tarball
        self.check_installed(fn, state, "TF", exps["TF"])

        # TG: installed wheel (same versions as TF)
        expected = exps["TF"]
        if os.path.exists(self.subpath("demoapp/dist")):
            shutil.rmtree(self.subpath("demoapp/dist"))
        self.python("setup.py", "bdist_wheel", "--universal")
        files = os.listdir(self.subpath("demoapp/dist"))
        self.assertTrue(len(files)==1, files)
        short_wheelfile = files[0]
        wheelfile = os.path.join(self.subpath("demoapp/dist"), short_wheelfile)
        self.assertEqual(short_wheelfile,
                         "demo-%s-py2.py3-none-any.whl" % expected[0])
        # installed wheel
        self.check_installed(wheelfile, state, "TG", expected)

        # TH: installed egg (same versions as TF)
        expected = exps["TF"]
        if os.path.exists(self.subpath("demoapp/dist")):
            shutil.rmtree(self.subpath("demoapp/dist"))
        self.python("setup.py", "bdist_egg")
        files = os.listdir(self.subpath("demoapp/dist"))
        self.assertTrue(len(files)==1, files)
        short_eggfile = files[0]
        eggfile = os.path.join(self.subpath("demoapp/dist"), short_eggfile)
        self.assertEqual(short_eggfile, "demo-%s-%s.egg" % (expected[0], pyver))
        # installed egg
        self.check_installed(eggfile, state, "TH", expected,
                             installer="easy_install")

    def check_version(self, workdir, state, tree, exps):
        exp_version, exp_full, exp_dirty, exp_error = exps
        if VERBOSE: print("== starting %s %s" % (state, tree))
        # RA: setup.py --version
        if VERBOSE:
            # setup.py version invokes cmd_version, which uses verbose=True
            # and has more boilerplate.
            print(self.python("setup.py", "version", workdir=workdir))
        # setup.py --version gives us get_version() with verbose=False.
        v = self.python("setup.py", "--version", workdir=workdir)
        self.compare(v, exp_version, state, tree, "RA1")
        self.assertPEP440(v, state, tree, "RA1")

        # and test again from outside the tree
        v = self.python(os.path.join(workdir, "setup.py"), "--version",
                        workdir=self.testdir)
        self.compare(v, exp_version, state, tree, "RA2")
        self.assertPEP440(v, state, tree, "RA2")

        # RB: setup.py build; rundemo --version
        if os.path.exists(os.path.join(workdir, "build")):
            shutil.rmtree(os.path.join(workdir, "build"))
        self.python("setup.py", "build", "--build-lib=build/lib",
                    "--build-scripts=build/lib", workdir=workdir)
        build_lib = os.path.join(workdir, "build", "lib")
        out = self.python("rundemo", "--version", workdir=build_lib)
        data = dict([line.split(":",1) for line in out.splitlines()])
        self.compare(data["__version__"], exp_version, state, tree, "RB")
        self.assertPEP440(data["__version__"], state, tree, "RB")
        self.compare(data["version"], exp_version, state, tree, "RB")
        self.compare(data["dirty"], str(exp_dirty), state, tree, "RB")
        self.compare(data["full-revisionid"], str(exp_full), state, tree, "RB")
        self.compare(data["error"], str(exp_error), state, tree, "RB")

    def check_installed(self, bdist, state, tree, exps, installer="pip"):
        exp_version, exp_full, exp_dirty, exp_error = exps
        if VERBOSE: print("== starting %s %s" % (state, tree))
        self.command("virtualenv", self.subpath("out/%s-ve" % tree))
        if installer == "pip":
            self.command(self.subpath("out/%s-ve/bin/pip" % tree), "install",
                         bdist)
        elif installer == "easy_install":
            self.command(self.subpath("out/%s-ve/bin/easy_install" % tree),
                         bdist)
            print(self.subpath("out/%s-ve" % tree))
            os._exit(0)
        else:
            assert False, "bad installer name '%s'" % installer
        demoapp = self.subpath("out/%s-ve/bin/rundemo" % tree)

        # RB: setup.py build; rundemo --version
        out = self.command(demoapp, "--version")
        data = dict([line.split(":",1) for line in out.splitlines()])
        self.compare(data["__version__"], exp_version, state, tree, "RB")
        self.assertPEP440(data["__version__"], state, tree, "RB")
        self.compare(data["version"], exp_version, state, tree, "RB")
        self.compare(data["dirty"], str(exp_dirty), state, tree, "RB")
        self.compare(data["full-revisionid"], str(exp_full), state, tree, "RB")
        self.compare(data["error"], str(exp_error), state, tree, "RB")

    def compare(self, got, expected, state, tree, runtime):
        where = "/".join([state, tree, runtime])
        self.assertEqual(got, expected, "%s: got '%s' != expected '%s'"
                         % (where, got, expected))
        if VERBOSE: print(" good %s" % where)

    def assertPEP440(self, got, state, tree, runtime):
        where = "/".join([state, tree, runtime])
        pv = parse_version(got)
        self.assertFalse(isinstance(pv, SetuptoolsLegacyVersion),
                         "%s: '%s' was not pep440-compatible"
                         % (where, got))
        self.assertEqual(str(pv), got,
                         "%s: '%s' pep440-normalized to '%s'"
                         % (where, got, str(pv)))

class Invocations(unittest.TestCase, _Common):
    def setUp(self):
        self.testdir = os.path.abspath("t")
        if os.path.exists(self.testdir):
            return
        os.mkdir(self.testdir)
        #self.testdir = tempfile.mkdtemp()
        os.mkdir(self.subpath("cache"))
        os.mkdir(self.subpath("cache", "distutils"))
        os.mkdir(self.subpath("cache", "setuptools"))

    def make_venv(self, mode):
        if not os.path.exists(self.subpath("venvs")):
            os.mkdir(self.subpath("venvs"))
        venv = self.subpath("venvs/%s" % mode)
        self.command("virtualenv", venv, workdir=self.subpath("venvs"))
        return venv

    def run_in_venv(self, venv, workdir, command, *args):
        bins = {"python": os.path.join(venv, "bin", "python"),
                "pip": os.path.join(venv, "bin", "pip"),
                "rundemo": os.path.join(venv, "bin", "rundemo")}
        return self.command(bins[command], *args, workdir=workdir)

    def check_in_venv(self, venv):
        out = self.run_in_venv(venv, venv, "rundemo")
        v = dict([line.split(":", 1) for line in out.splitlines()])
        self.assertEqual(v["version"], "2.0")
        return v

    def check_in_venv_withlib(self, venv):
        v = self.check_in_venv(venv)
        self.assertEqual(v["demolib"], "1.0")

    # "demolib" has a version of 1.0 and is built with distutils
    # "demoapp2-distutils" is v2.0, uses distutils, and has no deps
    # "demoapp2-setuptools" is v2.0, uses setuptools, and depends on demolib

    def make_demolib_sdist(self):
        # create an sdist of demolib-1.0 . for the *lib*, we only use the
        # tarball, never the repo.
        demolib_sdist = self.subpath("cache", "demolib-1.0.tar.gz")
        if os.path.exists(demolib_sdist):
            return demolib_sdist
        libdir = self.subpath("build-demolib")
        shutil.copytree("test/demolib", libdir)
        shutil.copy("versioneer.py", libdir)
        self.git("init", workdir=libdir)
        self.python("versioneer.py", "setup", workdir=libdir)
        self.git("add", "--all", workdir=libdir)
        self.git("commit", "-m", "commemt", workdir=libdir)
        self.git("tag", "demolib-1.0", workdir=libdir)
        self.python("setup.py", "sdist", "--format=gztar", workdir=libdir)
        created = os.path.join(libdir, "dist", "demolib-1.0.tar.gz")
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demolib_sdist)
        return demolib_sdist

    def make_linkdir(self):
        # create/populate a fake pypi directory for use with --find-links
        linkdir = self.subpath("linkdir")
        if os.path.exists(linkdir):
            return linkdir
        os.mkdir(linkdir)
        demolib_sdist = self.make_demolib_sdist()
        shutil.copy(demolib_sdist, linkdir)
        return linkdir

    def make_distutils_repo(self):
        # create a clean repo of demoapp2-distutils at 2.0
        repodir = self.subpath("demoapp2-distutils-repo")
        if os.path.exists(repodir):
            shutil.rmtree(repodir)
        shutil.copytree("test/demoapp2-distutils", repodir)
        shutil.copy("versioneer.py", repodir)
        self.git("init", workdir=repodir)
        self.python("versioneer.py", "setup", workdir=repodir)
        self.git("add", "--all", workdir=repodir)
        self.git("commit", "-m", "commemt", workdir=repodir)
        self.git("tag", "demoapp2-2.0", workdir=repodir)
        return repodir

    def make_distutils_wheel_with_pip(self):
        # create an wheel of demoapp2-distutils at 2.0
        wheelname = "demoapp2-2.0-py2.py3-none-any.whl"
        demoapp2_distutils_wheel = self.subpath("cache", "distutils",
                                                 wheelname)
        if os.path.exists(demoapp2_distutils_wheel):
            return demoapp2_distutils_wheel
        repodir = self.make_distutils_repo()
        venv = self.make_venv("make-distutils-wheel-with-pip")
        self.run_in_venv(venv, repodir,
                         "pip", "--isolated", "wheel",
                         "--no-index",# "--find-links", linkdir,
                         # we need --universal to get a consistent wheel
                         # name, but the --build-option= causes a UserWarning
                         # that's hard to squash
                         "--build-option=--universal",
                         ".")
        created = os.path.join(repodir, "wheelhouse", wheelname)
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demoapp2_distutils_wheel)
        return demoapp2_distutils_wheel

    def make_distutils_sdist(self):
        # create an sdist tarball of demoapp2-distutils at 2.0
        demoapp2_distutils_sdist = self.subpath("cache", "distutils",
                                                "demoapp2-2.0.tar.gz")
        if os.path.exists(demoapp2_distutils_sdist):
            return demoapp2_distutils_sdist
        repodir = self.make_distutils_repo()
        self.python("setup.py", "sdist", "--format=gztar", workdir=repodir)
        created = os.path.join(repodir, "dist", "demoapp2-2.0.tar.gz")
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demoapp2_distutils_sdist)
        return demoapp2_distutils_sdist

    def make_distutils_unpacked(self):
        sdist = self.make_distutils_sdist()
        unpack_into = self.subpath("demoapp2-distutils-unpacked")
        os.mkdir(unpack_into)
        self.command("tar", "xf", sdist, workdir=unpack_into)
        unpacked = os.path.join(unpack_into, "demoapp2-2.0")
        self.assertTrue(os.path.exists(unpacked))
        return unpacked

    def make_setuptools_repo(self):
        # create a clean repo of demoapp2-setuptools at 2.0
        repodir = self.subpath("demoapp2-setuptools-repo")
        if os.path.exists(repodir):
            shutil.rmtree(repodir)
        shutil.copytree("test/demoapp2-setuptools", repodir)
        shutil.copy("versioneer.py", repodir)
        self.git("init", workdir=repodir)
        self.python("versioneer.py", "setup", workdir=repodir)
        self.git("add", "--all", workdir=repodir)
        self.git("commit", "-m", "commemt", workdir=repodir)
        self.git("tag", "demoapp2-2.0", workdir=repodir)
        return repodir

    def make_setuptools_sdist(self):
        # create an sdist tarball of demoapp2-setuptools at 2.0
        demoapp2_setuptools_sdist = self.subpath("cache", "setuptools",
                                                 "demoapp2-2.0.tar.gz")
        if os.path.exists(demoapp2_setuptools_sdist):
            return demoapp2_setuptools_sdist
        repodir = self.make_setuptools_repo()
        self.python("setup.py", "sdist", "--format=gztar", workdir=repodir)
        created = os.path.join(repodir, "dist", "demoapp2-2.0.tar.gz")
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demoapp2_setuptools_sdist)
        return demoapp2_setuptools_sdist

    def make_setuptools_unpacked(self):
        sdist = self.make_setuptools_sdist()
        unpack_into = self.subpath("demoapp2-setuptools-unpacked")
        os.mkdir(unpack_into)
        self.command("tar", "xf", sdist, workdir=unpack_into)
        unpacked = os.path.join(unpack_into, "demoapp2-2.0")
        self.assertTrue(os.path.exists(unpacked))
        return unpacked

    def make_setuptools_egg(self):
        # create an egg of demoapp2-setuptools at 2.0
        demoapp2_setuptools_egg = self.subpath("cache", "setuptools",
                                               "demoapp2-2.0-%s.egg" % pyver)
        if os.path.exists(demoapp2_setuptools_egg):
            return demoapp2_setuptools_egg
        repodir = self.make_setuptools_repo()
        self.python("setup.py", "bdist_egg", workdir=repodir)
        created = os.path.join(repodir, "dist", "demoapp2-2.0-%s.egg" % pyver)
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demoapp2_setuptools_egg)
        return demoapp2_setuptools_egg

    def make_setuptools_wheel_with_setup_py(self):
        # create an wheel of demoapp2-setuptools at 2.0
        wheelname = "demoapp2-2.0-py2.py3-none-any.whl"
        demoapp2_setuptools_wheel = self.subpath("cache", "setuptools",
                                                 wheelname)  #XXX
        if os.path.exists(demoapp2_setuptools_wheel):
            return demoapp2_setuptools_wheel
        repodir = self.make_setuptools_repo()
        self.python("setup.py", "bdist_wheel", "--universal", workdir=repodir)
        created = os.path.join(repodir, "dist", wheelname)
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demoapp2_setuptools_wheel)
        return demoapp2_setuptools_wheel

    def make_setuptools_wheel_with_pip(self):
        # create an wheel of demoapp2-setuptools at 2.0
        wheelname = "demoapp2-2.0-py2.py3-none-any.whl"
        demoapp2_setuptools_wheel = self.subpath("cache", "setuptools",
                                                 wheelname) #XXX
        if os.path.exists(demoapp2_setuptools_wheel):
            return demoapp2_setuptools_wheel
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_repo()
        venv = self.make_venv("make-setuptools-wheel-with-pip")
        self.run_in_venv(venv, repodir,
                         "pip", "--isolated", "wheel",
                         "--no-index", "--find-links", linkdir,
                         # we need --universal to get a consistent wheel
                         # name, but the --build-option= causes a UserWarning
                         # that's hard to squash
                         "--build-option=--universal",
                         ".")
        created = os.path.join(repodir, "wheelhouse", wheelname)
        self.assertTrue(os.path.exists(created))
        shutil.copyfile(created, demoapp2_setuptools_wheel)
        return demoapp2_setuptools_wheel


    def test_distutils_repo_build(self):
        repodir = self.make_distutils_repo()
        self.python("setup.py", "build", workdir=repodir)
        # test that the built _version.py is correct. Ideally we'd actually
        # run PYTHONPATH=.../build/lib build/scripts-PYVER/rundemo and check
        # the output, but that's more fragile than I want to deal with today
        fn = os.path.join(repodir, "build", "lib", "demo", "_version.py")
        data = versions_from_file(fn)
        self.assertEqual(data["version"], "2.0")

    def test_distutils_repo_install(self):
        repodir = self.make_distutils_repo()
        venv = self.make_venv("distutils-repo-install")
        self.run_in_venv(venv, repodir, "python", "setup.py", "install")
        self.check_in_venv(venv)

    def test_distutils_repo_pip_wheel(self):
        self.make_distutils_wheel_with_pip()
        # asserts version as a side-effect

    def test_distutils_repo_sdist(self):
        self.make_distutils_sdist() # asserts version as a side-effect


    def test_setuptools_repo_install(self):
        repodir = self.make_setuptools_repo()
        demolib = self.make_demolib_sdist()
        venv = self.make_venv("setuptools-repo-install")
        # "setup.py install" doesn't take --no-index or --find-links, so we
        # pre-install the dependency
        self.run_in_venv(venv, venv, "pip", "install", demolib)
        self.run_in_venv(venv, repodir, "python", "setup.py", "install")
        self.check_in_venv_withlib(venv)

    def test_setuptools_repo_develop(self):
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_repo()
        demolib = self.make_demolib_sdist()
        venv = self.make_venv("setuptools-repo-develop")
        self.run_in_venv(venv, venv, "pip", "install", demolib)
        self.run_in_venv(venv, repodir,
                         "python", "setup.py", "develop",
                         "--no-index", "--find-links", linkdir,
                         )
        self.check_in_venv_withlib(venv)

    def test_setuptools_repo_egg(self):
        self.make_setuptools_egg() # asserts version as a side-effect

    def test_setuptools_repo_pip_wheel(self):
        self.make_setuptools_wheel_with_pip()
        # asserts version as a side-effect

    def test_setuptools_repo_bdist_wheel(self):
        self.make_setuptools_wheel_with_setup_py()
        # asserts version as a side-effect

    def test_setuptools_repo_sdist(self):
        self.make_setuptools_sdist() # asserts version as a side-effect

    def test_distutils_repo_pip_install(self):
        repodir = self.make_distutils_repo()
        venv = self.make_venv("distutils-repo-pip-install")
        self.run_in_venv(venv, repodir, "pip", "install", ".")
        self.check_in_venv(venv)

    def test_setuptools_repo_pip_install(self):
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_repo()
        venv = self.make_venv("setuptools-repo-pip-install")
        self.run_in_venv(venv, repodir, "pip", "install", ".",
                         "--no-index", "--find-links", linkdir)
        self.check_in_venv_withlib(venv)

    def test_distutils_repo_pip_install_from_afar(self):
        repodir = self.make_distutils_repo()
        venv = self.make_venv("distutils-repo-pip-install-from-afar")
        self.run_in_venv(venv, venv, "pip", "install", repodir)
        self.check_in_venv(venv)

    def test_setuptools_repo_pip_install_from_afar(self):
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_repo()
        venv = self.make_venv("setuptools-repo-pip-install-from-afar")
        self.run_in_venv(venv, venv, "pip", "install", repodir,
                         "--no-index", "--find-links", linkdir)
        self.check_in_venv_withlib(venv)

    def test_distutils_repo_pip_install_editable(self):
        repodir = self.make_distutils_repo()
        venv = self.make_venv("distutils-repo-pip-install-editable")
        self.run_in_venv(venv, repodir, "pip", "install", "--editable", ".")
        self.check_in_venv(venv)

    def test_setuptools_repo_pip_install_editable(self):
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_repo()
        venv = self.make_venv("setuptools-repo-pip-install-editable")
        self.run_in_venv(venv, repodir, "pip", "install", "--editable", ".",
                         "--no-index", "--find-links", linkdir)
        self.check_in_venv_withlib(venv)

    def test_distutils_sdist_pip_install(self):
        sdist = self.make_distutils_sdist()
        venv = self.make_venv("distutils-sdist-pip-install")
        self.run_in_venv(venv, venv,
                         "pip", "install",
                         sdist)
        self.check_in_venv(venv)

    def test_setuptools_sdist_pip_install(self):
        linkdir = self.make_linkdir()
        sdist = self.make_setuptools_sdist()
        venv = self.make_venv("setuptools-sdist-pip-install")
        self.run_in_venv(venv, venv,
                         "pip", "install",
                         "--no-index", "--find-links", linkdir,
                         sdist)
        self.check_in_venv_withlib(venv)

    def test_setuptools_wheel_pip_install(self):
        linkdir = self.make_linkdir()
        wheel = self.make_setuptools_wheel_with_setup_py()
        venv = self.make_venv("setuptools-wheel-pip-install")
        self.run_in_venv(venv, venv,
                         "pip", "install",
                         "--no-index", "--find-links", linkdir,
                         wheel)
        self.check_in_venv_withlib(venv)

    def test_distutils_unpacked_build(self):
        unpacked = self.make_distutils_unpacked()
        self.python("setup.py", "build", workdir=unpacked)
        # test that the built _version.py is correct. Ideally we'd actually
        # run PYTHONPATH=.../build/lib build/scripts-PYVER/rundemo and check
        # the output, but that's more fragile than I want to deal with today
        fn = os.path.join(unpacked, "build", "lib", "demo", "_version.py")
        data = versions_from_file(fn)
        self.assertEqual(data["version"], "2.0")

    def test_distutils_unpacked_install(self):
        unpacked = self.make_distutils_unpacked()
        # XXX: make sure all venv names are unique
        venv = self.make_venv("distutils-unpacked-install")
        self.run_in_venv(venv, unpacked, "python", "setup.py", "install")
        self.check_in_venv(venv)

    def test_distutils_unpacked_pip_wheel(self):
        unpacked = self.make_distutils_unpacked()
        wheelname = "demoapp2-2.0-py2.py3-none-any.whl"
        venv = self.make_venv("distutils-unpacked-pip-wheel")
        self.run_in_venv(venv, unpacked,
                         "pip", "--isolated", "wheel",
                         "--no-index",# "--find-links", linkdir,
                         # we need --universal to get a consistent wheel
                         # name, but the --build-option= causes a UserWarning
                         # that's hard to squash
                         "--build-option=--universal",
                         ".")
        created = os.path.join(unpacked, "wheelhouse", wheelname)
        self.assertTrue(os.path.exists(created))

    def test_setuptools_unpacked_install(self):
        unpacked = self.make_setuptools_unpacked()
        demolib = self.make_demolib_sdist()
        venv = self.make_venv("setuptools-unpacked-install")
        # "setup.py install" doesn't take --no-index or --find-links, so we
        # pre-install the dependency
        self.run_in_venv(venv, venv, "pip", "install", demolib)
        self.run_in_venv(venv, unpacked,
                         "python", "setup.py", "install")
        self.check_in_venv_withlib(venv)

    def test_setuptools_unpacked_wheel(self):
        unpacked = self.make_setuptools_unpacked()
        self.python("setup.py", "bdist_wheel", "--universal",
                    workdir=unpacked)
        wheelname = "demoapp2-2.0-py2.py3-none-any.whl"
        wheel = os.path.join(unpacked, "dist", wheelname)
        self.assertTrue(os.path.exists(wheel))

    def test_setuptools_unpacked_pip_wheel(self):
        unpacked = self.make_setuptools_unpacked()
        linkdir = self.make_linkdir()
        wheelname = "demoapp2-2.0-py2.py3-none-any.whl"
        venv = self.make_venv("setuptools-unpacked-pip-wheel")
        self.run_in_venv(venv, unpacked,
                         "pip", "--isolated", "wheel",
                         "--no-index", "--find-links", linkdir,
                         # we need --universal to get a consistent wheel
                         # name, but the --build-option= causes a UserWarning
                         # that's hard to squash
                         "--build-option=--universal",
                         ".")
        created = os.path.join(unpacked, "wheelhouse", wheelname)
        self.assertTrue(os.path.exists(created))

    def test_distutils_unpacked_pip_install(self):
        repodir = self.make_distutils_unpacked()
        venv = self.make_venv("distutils-unpacked-pip-install")
        self.run_in_venv(venv, repodir, "pip", "install", ".")
        self.check_in_venv(venv)

    def test_setuptools_unpacked_pip_install(self):
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_unpacked()
        venv = self.make_venv("setuptools-unpacked-pip-install")
        self.run_in_venv(venv, repodir, "pip", "install", ".",
                         "--no-index", "--find-links", linkdir)
        self.check_in_venv_withlib(venv)

    def test_distutils_unpacked_pip_install_from_afar(self):
        repodir = self.make_distutils_unpacked()
        venv = self.make_venv("distutils-unpacked-pip-install-from-afar")
        self.run_in_venv(venv, venv, "pip", "install", repodir)
        self.check_in_venv(venv)

    def test_setuptools_unpacked_pip_install_from_afar(self):
        linkdir = self.make_linkdir()
        repodir = self.make_setuptools_unpacked()
        venv = self.make_venv("setuptools-unpacked-pip-install-from-afar")
        self.run_in_venv(venv, venv, "pip", "install", repodir,
                         "--no-index", "--find-links", linkdir)
        self.check_in_venv_withlib(venv)


if __name__ == '__main__':
    ver = run_command(GITS, ["--version"], ".", True)
    print("git --version: %s" % ver.strip())
    unittest.main()
