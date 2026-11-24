# -*- coding: utf-8 -*-

name = 'nuke_opendrt'

version = '26.10.28.0'

description = \
    """
    OpenDRT for Nuke (Jed Smith's open-display-transform) plus CLFBake: the
    OpenDRT v1.1 node with its CLF Helpers, the CLFShaper / CLFGenerate pair
    that bakes any node chain to a CLF, CTF or csp with a parametric log
    shaper and restorable metadata, and an ODT node between
    lin_ciexyzd65_display and the CIF / OCIO 2 display colorspaces.

    Delivered as Nuke ToolSets (Nodes > ToolSets > OpenDRT); clfbake.py, which
    the buttons import, is on NUKE_PATH. The DCTLs, docs and the headless test harness ship alongside
    under {root}/display-transforms and {root}/utilities for reference;
    `rez-test nuke_opendrt` runs the harness in the resolved Nuke.
    """

authors = ['jed smith', 'zach lewis']

plugin_for = ['nuke']

requires = ['nuke-15.1+']

private_build_requires = ['python-3']

build_command = 'python {root}/build.py {install}'

tests = {
    'clfbake': {
        'command': 'nuke -t {root}/utilities/nuke/test_clfbake.py',
    },
    # every look, tonescale and display preset plus module toggles: CLF vs
    # Nuke, restore, byte-identical re-bake, model and interop metadata
    'sweep': {
        'command': 'nuke -t {root}/utilities/nuke/sweep_clfbake.py',
    },
}


def commands():
    # append: nuke setenvs NUKE_PATH and we run after it because we require it.
    env.NUKE_PATH.append('{root}/nuke')   # Nuke finds ToolSets/ beneath this
    env.NUKE_PATH.append('{root}/utilities/nuke')   # clfbake.py, which the node buttons import


help = 'file://{root}/utilities/nuke/README.md'

uuid = '3f0c2b1e-7a5d-5b64-9c1e-0d2a6b4c8e90'
