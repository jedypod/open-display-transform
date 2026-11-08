"""rez build for nuke_opendrt: copy the relevant parts of the checkout into the
install path. Run by rez (`rez-build -i` here); the repo root is three levels up.

Layout installed:
  nuke/ToolSets/OpenDRT/OpenDRT.nk, CLFBake.nk, ODT.nk   what Nuke's ToolSets menu shows
  display-transforms/opendrt/                     OpenDRT.nk, .dctl, README, docs
  utilities/nuke/                                 CLFBake.nk, builder, test harness, README
  utilities/*.dctl, LICENSE, README.md
The test harness resolves OpenDRT.nk relative to itself, so the two subtrees
keep their repo-relative layout.
"""
import os
import shutil
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(SRC, '..', '..', '..'))
BUILD = os.environ['REZ_BUILD_PATH']
INSTALL = os.environ['REZ_BUILD_INSTALL_PATH']

COPY = [
    ('display-transforms/opendrt', 'display-transforms/opendrt'),
    ('utilities/nuke', 'utilities/nuke'),
    ('LICENSE', 'LICENSE'),
    ('README.md', 'README.md'),
]
TOOLSETS = {
    'nuke/ToolSets/OpenDRT/OpenDRT.nk': 'display-transforms/opendrt/OpenDRT.nk',
    'nuke/ToolSets/OpenDRT/CLFBake.nk': 'utilities/nuke/CLFBake.nk',
    'nuke/ToolSets/OpenDRT/ODT.nk': 'utilities/nuke/ODT.nk',
}


def stage(dst_root):
    if os.path.isdir(dst_root):
        shutil.rmtree(dst_root)
    for src, dst in COPY:
        s, d = os.path.join(REPO, src), os.path.join(dst_root, dst)
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=shutil.ignore_patterns('.DS_Store', '__pycache__', '*.pyc'))
        else:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
    for dctl in os.listdir(os.path.join(REPO, 'utilities')):
        if dctl.endswith('.dctl'):
            os.makedirs(os.path.join(dst_root, 'utilities'), exist_ok=True)
            shutil.copy2(os.path.join(REPO, 'utilities', dctl), os.path.join(dst_root, 'utilities', dctl))
    for dst, src in TOOLSETS.items():
        d = os.path.join(dst_root, dst)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(REPO, src), d)


def main():
    staged = os.path.join(BUILD, 'staged')
    stage(staged)
    print('staged', staged)
    if 'install' in sys.argv[1:]:
        for name in os.listdir(staged):
            s, d = os.path.join(staged, name), os.path.join(INSTALL, name)
            if os.path.isdir(d):
                shutil.rmtree(d)
            elif os.path.exists(d):
                os.remove(d)
            (shutil.copytree if os.path.isdir(s) else shutil.copy2)(s, d)
        print('installed', INSTALL)


if __name__ == '__main__':
    main()
