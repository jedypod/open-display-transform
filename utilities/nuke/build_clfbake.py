"""Build CLFBake.nk (CLFShaper + CLFGenerate) and the "CLF Helpers" knobs in
OpenDRT.nk. Run inside Nuke, which escapes the knob scripts:

    nuke -t build_clfbake.py

The buttons only call into clfbake.py, which holds all the Python.
"""
import os
import sys

import nuke

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, HERE)
from clfbake import (PRESETS, XLOG, XLOG_DEFAULTS, DISPLAYS, ODT_MARK, auto_slope, inverse_expr,  # noqa: E402
                     display_matrix, moncurve)

OPENDRT = os.path.join(HERE, '..', '..', 'display-transforms', 'opendrt', 'OpenDRT.nk')


def table_expr(col, xlog_expr):
    """Nuke expression: nested ternary over the preset index for one parameter."""
    expr = xlog_expr
    for i in range(XLOG - 1, -1, -1):
        v = PRESETS[i][col]
        if col == 7 and v is None:
            v = auto_slope(PRESETS[i])
        expr = "preset==%d?%.17g:(%s)" % (i, v, expr)
    return expr


def button(fn):
    """A button that calls clfbake.<fn>; the code lives in clfbake.py, not in the node."""
    return ("try:\n    import clfbake\nexcept ImportError:\n"
            "    nuke.message('CLFBake: put utilities/nuke (open-display-transform) on NUKE_PATH')\n"
            "else:\n    clfbake.%s(nuke.thisNode())\n" % fn)


SHAPER_KNOBCHANGED = r"""n = nuke.thisNode()
if nuke.thisKnob().name() in ('preset', 'showPanel'):
    x = n['preset'].getValue() == %d
    for k in ('w0', 'o', 'x0', 'y0', 'k'):
        n[k].setVisible(x)
""" % XLOG


ABOUT = ('<font color=#ccc><b>%s</b> | CLFBake, part of '
         '<a href=https://github.com/jedypod/open-display-transform>open-display-transform</a><br>%s<br>'
         'Docs: utilities/nuke/README.md</font>')


def build_shaper():
    g = nuke.nodes.Group(name='CLFShaper')
    g.begin()
    inp = nuke.nodes.Input(name='Input1')
    pat = nuke.nodes.CMSTestPattern(name='CMSTestPattern1')
    pat['cube_size'].setExpression('parent.cube_size')
    inv = nuke.nodes.Expression(name='InverseShaper', inputs=[pat])
    par = dict((k, 'parent.' + k) for k in ('logbreak', 'linoff', 'sl', 'go', 'gs', 'lo', 'ls'))
    for i, c in enumerate('rgb'):
        inv['expr%d' % i].setValue(inverse_expr(c, par, 'parent.code_min', 'parent.code_max'))
    # probe ramps: 8 rows x 1024 columns. Rows 0-3 exposure ramps (-20..+24
    # stops around 0.18; neutral, then chromatic), rows 4-6 single-channel
    # negative ramps, row 7 neutral 0.18 (left) and 1.0 (right) for luminance.
    nuke.addFormat('1024 8 0 0 1024 8 1 clfbake_probe')
    con = nuke.nodes.Constant(name='ProbeFormat')
    con['format'].setValue('clfbake_probe')
    ramp = nuke.nodes.Expression(name='ProbeRamp', inputs=[con])
    ramp['temp_name0'].setValue('t'); ramp['temp_expr0'].setValue('0.18*pow(2,-20+44*x/width)')
    ramp['temp_name1'].setValue('n'); ramp['temp_expr1'].setValue('0.18*pow(2,-20+26*x/width)')
    ramp['temp_name2'].setValue('v'); ramp['temp_expr2'].setValue('floor(y/height*8)')
    gw = 'v==7?(x<width/2?0.18:1):0.18'
    ramp['expr0'].setValue('v==0?t:v==1?t:v==2?0.2*t:v==3?0.2*t:v==4?-n:' + gw)
    ramp['expr1'].setValue('v==0?t:v==1?0.2*t:v==2?t:v==3?0.2*t:v==5?-n:' + gw)
    ramp['expr2'].setValue('v==0?t:v==1?0.2*t:v==2?0.2*t:v==3?t:v==6?-n:' + gw)
    sw = nuke.nodes.Switch(name='Switch1', inputs=[inp, inv, ramp])
    sw['which'].setExpression('parent.pattern?1:(parent.probe?2:0)')
    nuke.nodes.Output(name='Output1', inputs=[sw])
    g.end()

    g.addKnob(nuke.Tab_Knob('CLFShaper'))
    k = nuke.Enumeration_Knob('preset', 'shaper', [p[0] for p in PRESETS])
    k.setTooltip('Log encoding for the lattice, written to the CLF as an exact Log node. '
                 'T-LogE is what the released OpenDRT OCIO config uses.')
    g.addKnob(k)
    for (name, val), (lo, hi, tip) in zip(XLOG_DEFAULTS, (
            (10, 256, 'XLog: linear value that maps to 1.0'),
            (0, 12, 'XLog: log asymptote offset, as 2^-o'),
            (0, 0.5, 'XLog: lower intersection constraint x'),
            (0, 0.5, 'XLog: lower intersection constraint y'),
            (0, 0.2, 'XLog: slope of the linear extension'))):
        d = nuke.Double_Knob(name, name)
        d.setRange(lo, hi)
        d.setValue(val)
        d.setTooltip(tip)
        g.addKnob(d)
    k = nuke.Int_Knob('cube_size', 'cube size')
    k.setValue(48)
    k.setTooltip('Lattice size. 48 as in the released OpenDRT config; 65 halves the error.')
    g.addKnob(k)
    for name, label, val in (('code_min', 'code range', 0.0), ('code_max', '', 1.0)):
        d = nuke.Double_Knob(name, label)
        d.setRange(-0.5, 2.0)
        d.setValue(val)
        d.setTooltip('Shaper codes the lattice spans. T-LogE code 1 is scene 512; raise the top for brighter '
                     'content. CLFGenerate\'s auto sets it.')
        if name == 'code_max':
            d.clearFlag(nuke.STARTLINE)
        g.addKnob(d)
    k = nuke.Boolean_Knob('pattern', 'show pattern')
    k.setFlag(nuke.STARTLINE)
    k.setTooltip('Show the shaped test pattern instead of the input.')
    g.addKnob(k)

    g.addKnob(nuke.Tab_Knob('Params'))
    # XLog derivation, verbatim from Jed's XLog.nk
    for name, expr, tip in (
            ('o0', '-(2**-o)', 'x offset: the y asymptote of the log curve'),
            ('s0', '(1-y0)/log((w0-o0)/(x0-o0))', 's0 = scale factor to satisfy intersection constraint at (x0, y0)'),
            ('o1', '1-s0*log(w0-o0)', 'y offset to satisfy intersection constraint at (w0, 1)'),
            ('x1', 's0*log(k*s0*exp(o1/s0))', 'x1 is x coordinate of linear extension intercept'),
            ('y1', 'exp((x1-o1)/s0)+o0', 'y1 is y coordinate of linear extension intercept')):
        d = nuke.Double_Knob(name, name)
        d.setExpression(expr)
        d.setTooltip(tip)
        d.setFlag(nuke.DISABLED)
        g.addKnob(d)
    g.addKnob(nuke.Text_Knob('div1', ''))
    # OCIO LogCameraTransform parameters (base 2) selected by preset
    for name, label, expr, tip in (
            ('gs', 'logSideSlope', table_expr(2, 's0*log(2)'), 'OCIO LogCameraTransform logSideSlope (base 2)'),
            ('go', 'logSideOffset', table_expr(3, 'o1'), 'OCIO LogCameraTransform logSideOffset'),
            ('ls', 'linSideSlope', table_expr(4, '1'), 'OCIO LogCameraTransform linSideSlope'),
            ('lo', 'linSideOffset', table_expr(5, '-o0'), 'OCIO LogCameraTransform linSideOffset'),
            ('lb', 'linSideBreak', table_expr(6, 'y1'), 'OCIO LogCameraTransform linSideBreak'),
            ('sl', 'linearSlope', table_expr(7, '1/k'), 'OCIO LogCameraTransform linearSlope'),
            ('logbreak', 'log break', 'gs*log(ls*lb+lo)/log(2)+go', 'log-side value at the break'),
            ('linoff', 'linear offset', 'logbreak-sl*lb', 'offset of the linear segment')):
        d = nuke.Double_Knob(name, label)
        d.setExpression(expr)
        d.setTooltip(tip)
        d.setFlag(nuke.DISABLED)
        g.addKnob(d)
    k = nuke.String_Knob('clfbake_shaper', '', '1')
    k.setFlag(nuke.INVISIBLE)
    g.addKnob(k)
    k = nuke.Boolean_Knob('probe', 'probe')
    k.setFlag(nuke.INVISIBLE)
    g.addKnob(k)
    g.addKnob(nuke.Tab_Knob('About'))
    g.addKnob(nuke.Text_Knob('about', ' ', ABOUT % ('CLFShaper',
        'Head of the chain to bake; CLFGenerate goes at the tail.')))
    g['knobChanged'].setValue(SHAPER_KNOBCHANGED)
    g['preset'].setValue(0)
    g['label'].setValue('[value preset]')
    g['tile_color'].setValue(0x4a3a7aff)
    for name, _ in XLOG_DEFAULTS:
        g[name].setVisible(False)
    return g


def build_generate():
    g = nuke.nodes.Group(name='CLFGenerate')
    g.begin()
    inp = nuke.nodes.Input(name='Input1')
    lut = nuke.nodes.GenerateLUT(name='GenerateLUT1', inputs=[inp])
    lut['file_type'].setValue('.cube')
    nuke.nodes.Output(name='Output1', inputs=[inp])
    g.end()

    g.addKnob(nuke.Tab_Knob('CLFGenerate'))
    k = nuke.File_Knob('file', 'file')
    k.setTooltip('Output path, or a directory (empty: the script\'s) to name the file automatically.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('format', 'format', ['clf', 'ctf', 'csp'])
    k.setTooltip('File format. csp carries the shaper as a 4096-point prelut, for hosts without CLF.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('interpolation', 'interpolation', ['tetrahedral', 'trilinear'])
    k.setTooltip('Interpolation recorded in the LUT3D.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('output', 'output', ['display codes', 'lin_ciexyzd65_display', 'lin_rec709_display',
                                                   'lin_p3d65_display'])
    k.setTooltip('display codes: the node\'s output. lin_*: exact decode nodes after the same cube, to a '
                 'linear display target with a D65 white. Needs an OpenDRT node; not for HLG.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('ocio', 'ctf target', ['2.1', '2.4'])
    k.setTooltip('2.4: PQ decodes use the PQ_TO_Lin FixedFunction. 2.1: a half-domain LUT1D that OCIO 2.2 reads.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('levels', 'levels', ['full', 'legal in', 'legal out', 'legal in and out'])
    k.setTooltip('legal: 64-940 as unclamped Range nodes first and/or last; delete one to convert. '
                 'legal in needs log input.')
    g.addKnob(k)
    k = nuke.Boolean_Knob('log_input', 'log input')
    k.setTooltip('Leave out the Log node: the file takes the shaper\'s log codes, as the released config does.')
    g.addKnob(k)
    k = nuke.Boolean_Knob('embed_script', 'embed node script')
    k.setValue(True)
    k.setTooltip('Store the baked nodes in the file so From CLF can rebuild them.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('domain', 'domain', ['preset', 'auto'])
    k.setTooltip('preset: CLFShaper as set. auto: if the chain still responds above the shaper\'s top, '
                 'extend the code range to cover it.')
    g.addKnob(k)
    k = nuke.PyScript_Knob('generate', 'Generate', button('generate'))
    k.setFlag(nuke.STARTLINE)
    k.setTooltip('Bake the chain between CLFShaper and this node.')
    g.addKnob(k)
    k = nuke.PyScript_Knob('restore', 'Restore', button('restore'))
    k.setTooltip('Apply the file\'s recorded knob values to the selected nodes, or the upstream chain.')
    g.addKnob(k)
    k = nuke.PyScript_Knob('from_clf', 'From CLF', button('from_clf'))
    k.setTooltip('Rebuild the baked nodes from the file, between the upstream CLFShaper and this node.')
    g.addKnob(k)
    g.addKnob(nuke.Text_Knob('status', ' ', ''))
    g.addKnob(nuke.Tab_Knob('About'))
    g.addKnob(nuke.Text_Knob('about', ' ', ABOUT % ('CLFGenerate',
        'Bakes everything between the upstream CLFShaper and this node.')))
    g['tile_color'].setValue(0x4a3a7aff)
    return g


def opendrt_knob_lines():
    """Knob definitions for the CLF Helpers group, escaped by Nuke."""
    g = nuke.nodes.Group(name='clfhelpers_tmp')
    g.addKnob(nuke.Tab_Knob('clf_grp', 'CLF Helpers', nuke.TABBEGINCLOSEDGROUP))
    k = nuke.File_Knob('clf_file', 'file')
    k.setTooltip('Output path, or a directory (empty: the script\'s) to name the file automatically.')
    g.addKnob(k)
    k = nuke.PyScript_Knob('bake_clf', 'Bake CLF', button('opendrt_bake'))
    k.setTooltip('Bake this node to a CLF (T-LogE, 48^3) with its parameters. Needs utilities/nuke on NUKE_PATH; '
                 'CLFBake.nk does other shapers, sizes and chains.')
    g.addKnob(k)
    k = nuke.PyScript_Knob('restore_clf', 'Restore CLF', button('opendrt_restore'))
    k.setTooltip('Apply the file\'s recorded parameters to this node.')
    g.addKnob(k)
    k = nuke.String_Knob('clf_params', 'params')
    k.setTooltip("Every parameter as one string, opendrt1_1{...} (the CLF's id). Bake CLF fills it in.")
    g.addKnob(k)
    k = nuke.PyScript_Knob('apply_params', 'Apply Params', button('opendrt_apply'))
    k.setTooltip('Set this node from the parameter string above.')
    g.addKnob(k)
    g.addKnob(nuke.Tab_Knob('endGroup_clf', '', nuke.TABENDGROUP))
    for n in nuke.allNodes():
        n.setSelected(n is g)
    tmp = os.path.join(HERE, '.clfhelpers_tmp.nk')
    nuke.nodeCopy(tmp)
    lines = open(tmp).read().splitlines()
    os.remove(tmp)
    nuke.delete(g)
    start = next(i for i, l in enumerate(lines) if 'addUserKnob {20 clf_grp' in l)
    end = next(i for i, l in enumerate(lines) if 'addUserKnob {20 endGroup_clf' in l)
    return lines[start:end + 1]


def splice_opendrt(path, new):
    lines = open(path).read().splitlines()
    starts = [i for i, l in enumerate(lines) if 'addUserKnob {20 clf_grp' in l]
    if starts:
        end = next(i for i, l in enumerate(lines) if 'addUserKnob {20 endGroup_clf' in l)
        lines[starts[0]:end + 1] = new
    else:
        anchor = next(i for i, l in enumerate(lines) if 'addUserKnob {20 endGroup_1' in l)
        lines[anchor + 1:anchor + 1] = new
    open(path, 'w').write('\n'.join(lines) + '\n')


# --- ODT: lin_ciexyzd65_display <-> the CIF / OCIO 2 display colorspaces ------------
ENC = ('linear', 'gamma', 'srgb', 'pq', 'hlg')
M1, M2, C1, C2, C3 = 2610 / 16384., 2523 / 32., 107 / 128., 2413 / 128., 2392 / 128.
HA = 0.17883277
HB, HC = 1 - 4 * HA, 0.5 - HA * __import__('math').log(4 * HA)
BRK, SLOPE = moncurve(2.4, 0.055)


def pick(values):
    """Nested ternary over the display menu."""
    expr = '%.17g' % values[-1]
    for i in range(len(values) - 2, -1, -1):
        expr = 'display==%d?%.17g:(%s)' % (i, values[i], expr)
    return expr


def coding(x, decode):
    """Per-channel encode (forward) or decode (inverse) expression; HLG's surround is separate."""
    if decode:
        cases = (x, 'sign(%s)*pow(fabs(%s),parent.gm)' % (x, x),
                 'sign(%s)*(fabs(%s)>=%r?pow((fabs(%s)+0.055)/1.055,2.4):fabs(%s)*%r)' % (x, x, BRK, x, x, SLOPE),
                 'sign(%s)*100*pow(max(pow(fabs(%s),%r)-%r,0)/(%r-%r*pow(fabs(%s),%r)),%r)' % (
                     x, x, 1 / M2, C1, C2, C3, x, 1 / M2, 1 / M1),
                 'sign(%s)*(fabs(%s)<=0.5?%s*%s:(exp((fabs(%s)-%r)/%r)+%r)/4)' % (x, x, x, x, x, HC, HA, HB))
    else:
        h = '(%s*pow(Y,1/1.2-1)/3)' % x
        cases = (x, 'sign(%s)*pow(fabs(%s),1/parent.gm)' % (x, x),
                 'sign(%s)*(fabs(%s)>=%r?1.055*pow(fabs(%s),1/2.4)-0.055:fabs(%s)/%r)' % (x, x, BRK * SLOPE, x, x, SLOPE),
                 'sign(%s)*pow((%r+%r*pow(fabs(%s)*0.01,%r))/(1+%r*pow(fabs(%s)*0.01,%r)),%r)' % (
                     x, C1, C2, x, M1, C3, x, M1, M2),
                 'sign(%s)*(fabs(%s)<=1/12.?sqrt(3*fabs(%s)):%r*log(12*fabs(%s)-%r)+%r)' % (h, h, h, HA, h, HB, HC))
    return ''.join('parent.enc==%d?(%s):' % (i, c) for i, c in enumerate(cases[:-1])) + '(%s)' % cases[-1]


def build_odt():
    g = nuke.nodes.Group(name='ODT')
    g.begin()
    inp = nuke.nodes.Input(name='Input1')
    to_rgb = nuke.nodes.ColorMatrix(name='ToDisplayRGB', inputs=[inp])
    enc = nuke.nodes.Expression(name='Encode', inputs=[to_rgb])
    dec = nuke.nodes.Expression(name='Decode', inputs=[inp])
    sur = nuke.nodes.Expression(name='HLGSurroundInverse', inputs=[dec])
    from_rgb = nuke.nodes.ColorMatrix(name='FromDisplayRGB', inputs=[sur])
    from_rgb['invert'].setValue(True)
    for cm in (to_rgb, from_rgb):
        for k in range(9):
            cm['matrix'].setExpression('parent.m%d' % k, k)
    # HLG: Rec.2100 surround with the 1000 cd/m2 nominal display (gamma 1.2), luminance
    # clamped at 1e-4 in magnitude as OCIO does, then the OETF of E/3; the inverse
    # clamps where that forward clamp lands, 1e-4^(1/1.2)
    y = 'max(fabs(0.2627*r+0.6780*g+0.0593*b),%r)'
    enc['temp_name0'].setValue('Y')
    enc['temp_expr0'].setValue(y % 1e-4)
    sur['temp_name0'].setValue('Y')
    sur['temp_expr0'].setValue(y % (1e-4 ** (1 / 1.2)))   # the forward clamp, carried through
    for i, c in enumerate('rgb'):
        enc['expr%d' % i].setValue(coding(c, False))
        dec['expr%d' % i].setValue(coding(c, True))
        sur['expr%d' % i].setValue('parent.enc==4?%s*pow(Y,0.2):%s' % (c, c))
    sw = nuke.nodes.Switch(name='Direction', inputs=[enc, from_rgb])
    sw['which'].setExpression('parent.direction')
    nuke.nodes.Output(name='Output1', inputs=[sw])
    g.end()

    g.addKnob(nuke.Tab_Knob('ODT'))
    k = nuke.Enumeration_Knob('display', 'display', [d[1] for d in DISPLAYS])
    k.setTooltip('Display colorspace, as defined by the Color Interop Forum display config (OCIO 2): ' +
                 ', '.join(d[0] for d in DISPLAYS) + '.')
    g.addKnob(k)
    k = nuke.Enumeration_Knob('direction', 'direction', ['forward', 'inverse'])
    k.setTooltip('forward: lin_ciexyzd65_display (1.0 = 100 cd/m2) to the display. inverse: the display back to '
                 'lin_ciexyzd65_display. CLFGenerate writes ODT nodes at the end of a chain as exact CLF ops.')
    g.addKnob(k)
    g.addKnob(nuke.Tab_Knob('Params'))
    ms = [display_matrix(d) for d in DISPLAYS]
    for k in range(9):
        d = nuke.Double_Knob('m%d' % k, 'm%d' % k)
        d.setExpression(pick([m[k // 3][k % 3] for m in ms]))
        d.setFlag(nuke.DISABLED)
        g.addKnob(d)
    for name, vals in (('enc', [ENC.index(d[3]) for d in DISPLAYS]), ('gm', [d[4] or 1.0 for d in DISPLAYS])):
        d = nuke.Double_Knob(name, name)
        d.setExpression(pick(vals))
        d.setFlag(nuke.DISABLED)
        g.addKnob(d)
    k = nuke.String_Knob(ODT_MARK, '', '1')
    k.setFlag(nuke.INVISIBLE)
    g.addKnob(k)
    g.addKnob(nuke.Tab_Knob('About'))
    g.addKnob(nuke.Text_Knob('about', ' ', ABOUT % ('ODT',
        'lin_ciexyzd65_display to and from the CIF display colorspaces, as in OCIO 2.')))
    g['label'].setValue('[value direction] [value display]')
    g['tile_color'].setValue(0x4a3a7aff)
    return g


def write_nk(path, nodes):
    for n in nuke.allNodes():
        n.setSelected(n in nodes)
    nuke.nodeCopy(path)
    lines = [l for l in open(path).read().splitlines()
             if not l.startswith('version ') and l.strip() != 'selected true']
    open(path, 'w').write('\n'.join(lines) + '\n')
    print('wrote', path)


def main():
    out = os.path.join(HERE, 'CLFBake.nk')
    s = build_shaper()
    g = build_generate()
    g.setInput(0, s)
    s.setXYpos(0, 0)
    g.setXYpos(0, 200)
    write_nk(out, (s, g))
    write_nk(os.path.join(HERE, 'ODT.nk'), (build_odt(),))
    splice_opendrt(os.path.normpath(OPENDRT), opendrt_knob_lines())
    print('spliced CLF Helpers into', os.path.normpath(OPENDRT))


if __name__ == '__main__':
    main()
