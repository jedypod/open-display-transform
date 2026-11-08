"""End-to-end sweep: OpenDRT look presets, display presets and module toggles
through CLFBake, checking that every CLF round-trips.

    nuke -t sweep_clfbake.py
    CLFBAKE_DOMAIN=auto nuke -t sweep_clfbake.py   # code range from the chain

For each configuration (applied through OpenDRT's own preset pulldowns, as a
user would):
  1. the CLF applied with PyOpenColorIO matches Nuke's render of the chain,
  2. Restore into a fresh OpenDRT reproduces every recorded knob,
  3. baking the restored node again reproduces LogParams and the LUT3D array
     byte for byte,
  4. the recorded Model block matches the node and the Interop output ID is
     the expected one for the display preset.
Exits non-zero on any failure.
"""
import math
import os
import sys
import tempfile
import xml.etree.ElementTree as ET

import nuke
import PyOpenColorIO as ocio

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, HERE)   # the buttons import clfbake
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
CLFBAKE = os.path.join(HERE, 'CLFBake.nk')
OPENDRT = os.path.join(ROOT, 'display-transforms', 'opendrt', 'OpenDRT.nk')
OUT = tempfile.mkdtemp(prefix='clfbake_sweep_')
DOMAIN = os.environ.get('CLFBAKE_DOMAIN', 'preset')
W = H = 20
IMAGE_TOL = 3e-2

# display preset label -> expected Interop output (modifiers filled in from the file)
EXPECT_OUT = {
    'Rec.1886 - 2.4 Power / Rec.709': 'g24_rec709_display',
    'sRGB Display - 2.2 Power / Rec.709': 'g22_rec709_display',
    'Display P3 - 2.2 Power / P3-D65': 'opendrt-v1.1:g22_p3d65_display',
    'DCI - 2.6 Power / P3-D60': 'opendrt-v1.1:g26_p3d60_display',
    'DCI - 2.6 Power / P3-DCI': 'opendrt-v1.1:g26_p3dci_display',
    "DCI - 2.6 Power / X'Y'Z'": 'g26_xyzd65_display',
    'Rec.2100 - PQ Rec.2020 (P3 Limited)': 'opendrt-v1.1:pq_rec2020_display|p3lim|dw*',
    'Rec.2100 - HLG Rec.2020 (P3 Limited)': 'opendrt-v1.1:hlg_rec2020_display|p3lim|dw*',
    'Dolby - PQ P3-D65': 'opendrt-v1.1:pq_p3d65_display|dw*',
}
TOGGLES = [
    ('all modules off', dict(tn_hcon_enable=False, tn_lcon_enable=False, pt_enable=False, ptl_enable=False,
                             ptm_enable=False, brl_enable=False, brlp_enable=False, hc_enable=False,
                             hs_rgb_enable=False, hs_cmy_enable=False)),
    ('contrast modules on', dict(tn_hcon_enable=True, tn_hcon=0.6, tn_lcon_enable=True, tn_lcon=0.5)),
    ('brilliance on, hueshift off', dict(brl_enable=True, brl=-0.5, hs_rgb_enable=False, hs_cmy_enable=False)),
    ('creative white D55, clamp off', dict(cwp='D55', clamp=False)),
    ('log input', dict()),
]

failures = []


def paste(path):
    before = set(nuke.allNodes())
    nuke.nodePaste(path)
    new = [n for n in nuke.allNodes() if n not in before]
    for n in nuke.allNodes():
        n.setSelected(False)
    return new


def sample(node):
    return [[node.sample(c, x + 0.5, y + 0.5) for c in ('red', 'green', 'blue')] for y in range(H) for x in range(W)]


def max_err(a, b):
    return max(abs(p - q) for pa, pb in zip(a, b) for p, q in zip(pa, pb))


def apply_clf(path, pixels):
    cpu = ocio.Config.CreateRaw().getProcessor(ocio.FileTransform(src=path)).getDefaultCPUProcessor()
    return [cpu.applyRGB(list(p)) for p in pixels]


def clf_core(path):
    root = ET.parse(path).getroot()
    lp = root.find('Log/LogParams')
    rows = [l.split() for l in root.find('LUT3D/Array').text.strip().splitlines()]
    knobs = dict((k.get('name'), k.text) for k in root.iter('Knob'))
    nb = root.find('Info/CLFBake')
    return (dict(lp.attrib) if lp is not None else None), rows, knobs, nb


def log_to_lin(shaper, y):
    gs, go, ls, lo, lb, sl = [shaper[k].value() for k in ('gs', 'go', 'ls', 'lo', 'lb', 'sl')]
    logbreak = gs * math.log(ls * lb + lo, 2) + go
    return (y - (logbreak - sl * lb)) / sl if y <= logbreak else (2.0 ** ((y - go) / gs) - lo) / ls


def lin_to_log(shaper, v):
    gs, go, ls, lo, lb, sl = [shaper[k].value() for k in ('gs', 'go', 'ls', 'lo', 'lb', 'sl')]
    logbreak = gs * math.log(ls * lb + lo, 2) + go
    return sl * v + (logbreak - sl * lb) if v < lb else gs * math.log(ls * v + lo, 2) + go


def apply_pulldown(node, knob, label):
    """Run the TCL command behind a Pulldown_Knob entry, as the UI would."""
    vals = node[knob].values()   # alternating 'Menu/Label', 'knobs this {...}'
    for i in range(0, len(vals) - 1, 2):
        if vals[i].split('/', 1)[-1] == label:
            nuke.tcl(vals[i + 1].replace('knobs this', 'knobs %s' % node.fullName()))
            return
    raise KeyError('%s has no entry %r' % (knob, label))


def pulldown_labels(node, knob):
    vals = node[knob].values()
    return [vals[i].split('/', 1)[-1] for i in range(0, len(vals) - 1, 2)]


def model_matches(nb, node):
    model = nb.find('Model')
    bad = []
    for e in model:
        for pid, val in e.attrib.items():
            if pid.endswith('_index') or pid not in node.knobs():
                continue
            k = node[pid]
            if k.Class() == 'Enumeration_Knob':
                ok = val == k.value()
            elif k.Class() == 'Boolean_Knob':
                ok = val == ('true' if k.value() else 'false')
            elif isinstance(k.value(), float):
                ok = float(val) == k.value()
            else:
                ok = val == str(k.value())
            if not ok:
                bad.append(pid)
    return bad


# --- scene: two bookend pairs, one to bake, one to restore + re-bake ---------------
nuke.addFormat('%d %d 0 0 %d %d 1 clfbake_sweep' % (W, H, W, H))
nuke.root()['format'].setValue('clfbake_sweep')
s1, g1 = paste(CLFBAKE)
if 'clfbake_shaper' not in s1.knobs():
    s1, g1 = g1, s1
drt = paste(OPENDRT)[0]
s2, g2 = paste(CLFBAKE)
if 'clfbake_shaper' not in s2.knobs():
    s2, g2 = g2, s2
hi, lo = log_to_lin(s1, 1.0), log_to_lin(s1, 0.0)
img = nuke.nodes.Expression(expr0='%r*pow(2,24*(x/width-1))' % hi, expr1='%r*pow(2,24*(y/height-1))' % hi,
                            expr2='0.5*(r+g)*(0.5+0.5*sin(x*0.7+y*0.3))+%r' % (0.5 * lo))
img.setInput(0, None)
s1.setInput(0, img); drt.setInput(0, s1); g1.setInput(0, drt)
s2.setInput(0, img); g2.setInput(0, s2)
for n in nuke.allNodes():
    n.setSelected(False)
lin = sample(img)
print('nuke:', nuke.NUKE_VERSION_STRING, ' ocio:', ocio.__version__)

looks = pulldown_labels(drt, 'look_presets')
tonescales = pulldown_labels(drt, 'tn_presets')
displays = pulldown_labels(drt, 'display_presets')
print('look presets:', looks)
print('tonescale presets:', tonescales)
print('display presets:', displays)

SDR = 'Rec.1886 - 2.4 Power / Rec.709'
configs = [('look %s' % l, ('look_presets', l), SDR, {}) for l in looks]
configs += [('tonescale %s' % t, ('tn_presets', t), SDR, {}) for t in tonescales]
configs += [('display %s' % d, ('look_presets', 'Standard'), d, {}) for d in displays]
configs += [('toggle %s' % t, ('look_presets', 'Standard'), SDR, kn) for t, kn in TOGGLES]

rows = []
for i, (name, (pk, pl), disp, knobs) in enumerate(configs):
    apply_pulldown(drt, pk, pl)
    apply_pulldown(drt, 'display_presets', disp)
    for k, v in knobs.items():
        drt[k].setValue(v)
    log_input = name.endswith('log input')
    g1['log_input'].setValue(log_input)
    g1['domain'].setValue(DOMAIN)
    g1['file'].setValue(OUT + '/')          # directory only: automatic, explicit name
    g1['generate'].execute()
    clf = g1['file'].value()
    if DOMAIN == 'auto':   # test up to the top auto chose; the re-bake chain gets the same range
        top = log_to_lin(s1, s1['code_max'].value())
        img['expr0'].setValue('%r*pow(2,24*(x/width-1))' % top)
        img['expr1'].setValue('%r*pow(2,24*(y/height-1))' % top)
        lin = sample(img)
        for k in ('code_min', 'code_max'):
            s2[k].setValue(s1[k].value())
    live = sample(g1)
    src = [[lin_to_log(s1, c) for c in p] for p in lin] if log_input else lin
    lp, arr, kv, nb = clf_core(clf)
    conform = nb.find('Interop').get('outputConform')
    via = apply_clf(clf, src)
    if conform:
        via = [[c / float(conform) for c in p] for p in via]
    per_px = sorted(max(abs(p - q) for p, q in zip(a, b)) for a, b in zip(via, live))
    err, p99 = per_px[-1], per_px[int(len(per_px) * 0.95)]   # p95 of a deliberately extreme image
    # restore into a fresh node on the second chain, re-bake, compare
    fresh = paste(OPENDRT)[0]
    fresh.setInput(0, s2); g2.setInput(0, fresh)
    g2['file'].setValue(clf)
    fresh.setSelected(True)
    g2['restore'].execute()
    fresh.setSelected(False)
    bad_knobs = [k for k in kv if drt[k].toScript() != fresh[k].toScript()]
    g2['log_input'].setValue(log_input)
    clf2 = os.path.join(OUT, 'sweep_%02d_rebake.clf' % i)
    g2['file'].setValue(clf2)
    g2['generate'].execute()
    lp2, arr2, kv2, nb2 = clf_core(clf2)
    identical = lp == lp2 and arr == arr2
    bad_model = model_matches(nb, drt)
    out_id = nb.find('Interop').get('output')
    # expected ID: published base, plus modifiers from the node state (creative
    # white, HDR diffuse white, clamp, log input), namespaced when any apply
    exp = EXPECT_OUT[disp]
    ns, base = ('opendrt-v1.1', exp.split(':', 1)[1]) if ':' in exp else (None, exp)
    base, mods = base.split('|')[0], base.split('|')[1:]
    mods = [m for m in mods if m != 'dw*']
    if drt['cwp'].value() != 'D65':
        mods.append(drt['cwp'].value().lower() + 'sim')
    if drt['eotf'].value() in ('PQ', 'HLG'):
        mods.append('dw%d' % int(round(float(nb.find('Mastering/Luminance').get('diffuseWhiteMeasured')))))
    if not drt['clamp'].value():
        mods.append('clamp0')
    if log_input:
        mods.append('EE')
    expected = (base if ns is None and not mods else 'opendrt-v1.1:' + '|'.join([base] + mods))
    id_ok = out_id == expected
    # p95 gates interpolation quality; the max is reported and gated loosely,
    # because with purity compression off the chain is far too nonlinear for
    # the lattice outside the display gamut: a saturated blue-cyan's green
    # output swings 0.65 across one 48^3 cell (-0.31 to +0.34 unclamped), so
    # the cube interpolates the clamped corners to 0.07 where the node gives
    # 0.17. Not a clip artefact: baking unclamped with an exact Range after
    # the LUT3D measured no better (max worse, p99 -25%), and for the default
    # chain or PQ it changed nothing. Measured 3.3e-2 at 48^3, 2.4e-2 at 65^3,
    # 1.8e-2 at 97^3 for an all-modules-off bake, median error zero; up to
    # 1e-1 on a fully saturated hue sweep.
    # automatic file name: an untouched look preset names itself
    fname = os.path.basename(clf)
    look_part = '_'.join(fname.split('__')[0].split('_')[1:-1])   # OpenDRT-v.._<look>_<condition>__...
    name_ok = (look_part == pl.replace(' ', '')) if name.startswith('look ') else bool(look_part)
    ok = p99 <= IMAGE_TOL and err <= 2 * IMAGE_TOL and not bad_knobs and identical and not bad_model and id_ok and name_ok
    rows.append((ok, name, disp if not name.startswith('display') else '', err, len(kv), len(bad_knobs), identical, out_id))
    print('%s %-42s max %.2e p95 %.2e  restore %d/%d  rebake %s  model %s  out %s%s\n      %s' % (
        'PASS' if ok else 'FAIL', name, err, p99, len(kv) - len(bad_knobs), len(kv),
        'identical' if identical else 'DIFFERS', 'ok' if not bad_model else bad_model, out_id,
        '' if id_ok else '  (expected %s)' % expected, fname))
    if not ok:
        failures.append(name)
    nuke.delete(fresh)
    # back to a clean default before the next configuration
    for k, v in knobs.items():
        if k in ('cwp', 'clamp'):
            drt[k].setValue('D65' if k == 'cwp' else True)

print('outputs in', OUT)
if failures:
    print('FAILED:', failures)
    sys.exit(1)
print('ALL PASS (%d configurations)' % len(rows))
