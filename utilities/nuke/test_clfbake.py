"""Headless checks of CLFBake against the OpenDRT Nuke node, with PyOpenColorIO
as the independent reader.

    nuke -t test_clfbake.py
    CLFBAKE_PRESET=8 nuke -t test_clfbake.py   # another shaper preset

Bakes test image -> CLFShaper -> OpenDRT -> CLFGenerate and compares the files
with Nuke's render: on and off the lattice, log input, CTF, csp, linear
decodes, levels, the auto code range, Restore / Apply Params / From CLF round
trips, file names and metadata. One PASS/FAIL line per check; exits non-zero
on failure.
"""
import math
import os
import re
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
OUT = tempfile.mkdtemp(prefix='clfbake_test_')
PRESET = int(os.environ.get('CLFBAKE_PRESET', '0'))  # nuke -t eats numeric argv as a frame range
W = H = 24
LATTICE_TOL = 2e-4
IMAGE_TOL = 3e-2  # 48^3 tetrahedral interpolation of a DRT, display code values

failures = []


def check(name, err, tol):
    ok = err <= tol
    print('%s %-34s max err %.3e (tol %.0e)' % ('PASS' if ok else 'FAIL', name, err, tol))
    if not ok:
        failures.append(name)


def paste(path):
    before = set(nuke.allNodes())
    nuke.nodePaste(path)
    new = [n for n in nuke.allNodes() if n not in before]
    for n in new:
        n.setSelected(False)
    return new


def sample(node, w, h):
    out = []
    for y in range(h):
        for x in range(w):
            out.append([node.sample(c, x + 0.5, y + 0.5) for c in ('red', 'green', 'blue')])
    return out


def max_err(a, b):
    return max(abs(p - q) for pa, pb in zip(a, b) for p, q in zip(pa, pb))


def clf_core(path):
    """(LogParams attributes or None, LUT3D array rows, recorded knob values) for byte comparison."""
    root = ET.parse(path).getroot()
    lp = root.find('Log/LogParams')
    rows = [l.split() for l in root.find('LUT3D/Array').text.strip().splitlines()]
    knobs = dict((k.get('name'), k.text) for k in root.iter('Knob'))
    return (dict(lp.attrib) if lp is not None else None), rows, knobs


def apply_clf(path, pixels):
    cfg = ocio.Config.CreateRaw()
    cpu = cfg.getProcessor(ocio.FileTransform(src=path)).getDefaultCPUProcessor()
    return [cpu.applyRGB(list(p)) for p in pixels]


def lin_to_log(shaper, v):
    gs, go, ls, lo, lb, sl = [shaper[k].value() for k in ('gs', 'go', 'ls', 'lo', 'lb', 'sl')]
    logbreak = gs * math.log(ls * lb + lo, 2) + go
    if v < lb:
        return sl * v + (logbreak - sl * lb)
    return gs * math.log(ls * v + lo, 2) + go


def log_to_lin(shaper, y):
    gs, go, ls, lo, lb, sl = [shaper[k].value() for k in ('gs', 'go', 'ls', 'lo', 'lb', 'sl')]
    logbreak = gs * math.log(ls * lb + lo, 2) + go
    if y <= logbreak:
        return (y - (logbreak - sl * lb)) / sl
    return (2.0 ** ((y - go) / gs) - lo) / ls


# --- scene -----------------------------------------------------------------
nuke.addFormat('%d %d 0 0 %d %d 1 clfbake_test' % (W, H, W, H))
nuke.root()['format'].setValue('clfbake_test')

shaper, gen = paste(CLFBAKE)
if 'clfbake_shaper' not in shaper.knobs():
    shaper, gen = gen, shaper
drt = paste(OPENDRT)[0]
shaper['preset'].setValue(PRESET)
shaper['cube_size'].setValue(48)

# test image spanning the shaper's own domain: 24 stops below its top, and
# negatives down to half of what the linear toe admits
def test_image(hi, lo, name):
    img = nuke.nodes.Expression(name=name)
    img['expr0'].setValue('%r*pow(2,24*(x/width-1))' % hi)
    img['expr1'].setValue('%r*pow(2,24*(y/height-1))' % hi)
    img['expr2'].setValue('0.5*(r+g)*(0.5+0.5*sin(x*0.7+y*0.3))+%r' % (0.5 * lo))
    return img


hi, lo = log_to_lin(shaper, 1.0), log_to_lin(shaper, 0.0)
img = test_image(hi, lo, 'TestImage')
shaper.setInput(0, img)
drt.setInput(0, shaper)
gen.setInput(0, drt)
print('nuke:', nuke.NUKE_VERSION_STRING, ' ocio:', ocio.__version__,
      ' preset:', shaper['preset'].value(), ' domain: %.4g .. %.4g' % (lo, hi), ' node:', drt.name())

# a non-default OpenDRT state so Restore has something to prove
drt['tn_con'].setValue(1.6)
drt['hs_r'].setValue(0.21)
drt['brl_enable'].setValue(False)
drt['tn_Lp'].setValue(200)
drt['display_name'].setValue('clfbake test')

# --- 1. lattice exactness --------------------------------------------------
clf = os.path.join(OUT, 'test.clf')
gen['file'].setValue(clf)
gen['generate'].execute()
print('status:', gen['status'].value())
assert os.path.exists(clf), clf
assert not shaper['pattern'].value(), 'pattern mode left on'

shaper['pattern'].setValue(True)
lin = sample(shaper, W, H)       # linear lattice samples (inverse shaper output)
nuke_out = sample(gen, W, H)     # what the chain renders for them
shaper['pattern'].setValue(False)
check('lattice: CLF vs Nuke', max_err(apply_clf(clf, lin), nuke_out), LATTICE_TOL)

# --- 2. real image ----------------------------------------------------------
lin = sample(img, W, H)
nuke_out = sample(gen, W, H)
check('image: CLF vs Nuke', max_err(apply_clf(clf, lin), nuke_out), IMAGE_TOL)

# --- 3. log input -------------------------------------------------------------
clf_log = os.path.join(OUT, 'test_log.clf')
gen['file'].setValue(clf_log)
gen['log_input'].setValue(True)
gen['generate'].execute()
gen['log_input'].setValue(False)
logpix = [[lin_to_log(shaper, c) for c in p] for p in lin]
check('log input: CLF vs Nuke', max_err(apply_clf(clf_log, logpix), nuke_out), IMAGE_TOL)
txt = open(clf_log).read()
assert '<Log ' not in txt, 'log-input CLF must not embed the shaper'
assert '<Log ' in open(clf).read(), 'linear CLF must embed the shaper'

# --- 4. restore ---------------------------------------------------------------
fresh = paste(OPENDRT)[0]
knobs = drt['look_preset_knobs'].value().split() + ['tn_Lp', 'tn_Lg', 'tn_gb', 'pt_hdr', 'eotf',
                                                   'display_gamut', 'clamp', 'display_name', 'in_gamut']
differs = [k for k in knobs if drt[k].toScript() != fresh[k].toScript()]
assert differs, 'fresh node already matches, restore proves nothing'
gen['file'].setValue(clf)
for n in nuke.allNodes():
    n.setSelected(n is fresh)
gen['restore'].execute()
print('status:', gen['status'].value())
recorded = list(clf_core(clf)[2])
bad = [k for k in recorded if drt[k].toScript() != fresh[k].toScript()]
print('%s restore: %d recorded knobs compared, %d differed before, %d differ after %s'
      % ('PASS' if not bad else 'FAIL', len(recorded), len(differs), len(bad), bad))
if bad:
    failures.append('restore')
for n in nuke.allNodes():
    n.setSelected(False)   # pasted/created nodes connect to the selection

# --- 5. CTF -------------------------------------------------------------------
ctf = os.path.join(OUT, 'test.ctf')
gen['file'].setValue(ctf)
gen['generate'].execute()
check('ctf: CLF vs CTF', max_err(apply_clf(ctf, lin), apply_clf(clf, lin)), 1e-6)

# --- 6. thin buttons on OpenDRT itself (fixed T-LogE shaper) -------------------
preset_was = int(shaper['preset'].getValue())
shaper['preset'].setValue(0)
img2 = test_image(log_to_lin(shaper, 1.0), log_to_lin(shaper, 0.0), 'TestImageTLogE')
shaper['preset'].setValue(preset_was)
d2 = paste(OPENDRT)[0]
d2.setInput(0, img2)
for k in ('tn_con', 'hs_r', 'brl_enable', 'tn_Lp', 'display_name'):
    d2[k].fromScript(drt[k].toScript())
clf2 = os.path.join(OUT, 'opendrt_button.clf')
d2['clf_file'].setValue(clf2)
d2['bake_clf'].execute()
assert os.path.exists(clf2), clf2
assert d2.input(0) is img2, 'Bake CLF did not restore the input'
assert '<Log ' in open(clf2).read()
check('opendrt button: CLF vs Nuke', max_err(apply_clf(clf2, sample(img2, W, H)), sample(d2, W, H)), IMAGE_TOL)
d3 = paste(OPENDRT)[0]
d3['clf_file'].setValue(clf2)
d3['restore_clf'].execute()
bad = [k for k in knobs if d2[k].toScript() != d3[k].toScript()]
print('%s opendrt button restore: %d knobs compared, %d differ %s' % ('PASS' if not bad else 'FAIL', len(knobs), len(bad), bad))
if bad:
    failures.append('opendrt button restore')
txt2 = open(clf2).read()
assert clf2 not in txt2 and '<Knob name="clf_file">' not in txt2, 'the bake path must not be recorded'

# --- 7. domain auto: keeps a shaper that covers the chain, else extends its code range ---
shaper['preset'].setValue(len(shaper['preset'].values()) - 1)   # XLog
shaper['w0'].setValue(60000.0)
gen['file'].setValue(os.path.join(OUT, 'test_auto.clf'))
gen['domain'].setValue('auto')
gen['generate'].execute()
print('status:', gen['status'].value())
ok = 'auto: XLog covers it' in gen['status'].value() and shaper['code_max'].value() == 1.0
print('%s auto keeps a shaper that covers the chain' % ('PASS' if ok else 'FAIL'))
if not ok:
    failures.append('auto keep')
shaper['preset'].setValue(PRESET)
shaper['w0'].setValue(128.0)
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
gen['domain'].setValue('preset')
clf_ext = gen['file'].value()
print('status:', gen['status'].value())
c1 = shaper['code_max'].value()
root_x = ET.parse(clf_ext).getroot()
rng_x = root_x.find('Range')
in_x = root_x.find('Info/CLFBake/Interop').get('input')
ok = c1 > 1.0 and root_x.find('Log') is not None and rng_x is not None \
    and abs(float(rng_x.find('maxInValue').text) - c1) < 1e-9 and '|codes' not in in_x and '-to' in os.path.basename(clf_ext)
print('%s auto extends the code range: codes 0..%.4g, Range node %s, input %s\n   %s' % (
    'PASS' if ok else 'FAIL', c1, 'present' if rng_x is not None else 'MISSING', in_x, os.path.basename(clf_ext)))
if not ok:
    failures.append('auto extend')
hi_x = log_to_lin(shaper, c1)
img3 = test_image(hi_x, lo, 'TestImageExtended')
shaper.setInput(0, img3)
check('auto: CLF vs Nuke up to the extended top (%.0f)' % hi_x, max_err(apply_clf(clf_ext, sample(img3, W, H)), sample(gen, W, H)), IMAGE_TOL)
# beyond the extended top the chain must already be flat, so clamping is harmless
c = nuke.nodes.Expression(expr0=repr(hi_x * 8), expr1=repr(hi_x * 8), expr2=repr(hi_x * 8))
c.setInput(0, None)
shaper.setInput(0, c)
live = [[gen.sample(ch, 0.5, 0.5) for ch in ('red', 'green', 'blue')]]
check('auto: 3 stops above the extended top', max_err(apply_clf(clf_ext, [[hi_x * 8] * 3]), live), 5e-3)
shaper['code_min'].setValue(0.0)
shaper['code_max'].setValue(1.0)
shaper.setInput(0, img)

# --- 8. From CLF rebuilds the chain; re-baking reproduces the CLF ---------------
def rebake_matches(name, src_clf):
    for n in nuke.allNodes():
        n.setSelected(False)
    s2, g2 = paste(CLFBAKE)
    if 'clfbake_shaper' not in s2.knobs():
        s2, g2 = g2, s2
    s2.setInput(0, img)
    g2.setInput(0, s2)
    g2['file'].setValue(src_clf)
    g2['from_clf'].execute()
    print('status:', g2['status'].value())
    mid = g2.input(0)
    assert mid is not None and mid is not s2 and mid.input(0) is s2, 'From CLF did not wire the chain'
    out = os.path.join(OUT, 'rebake_%s.clf' % name.replace(' ', '_'))
    g2['file'].setValue(out)
    g2['generate'].execute()
    a, b = clf_core(src_clf), clf_core(out)
    same = a[0] == b[0] and a[1] == b[1] and a[2] == b[2]
    print('%s rebake from CLF (%s): LogParams %s, %d array rows %s, %d knobs %s'
          % ('PASS' if same else 'FAIL', name, 'same' if a[0] == b[0] else 'DIFFER',
             len(a[1]), 'identical' if a[1] == b[1] else 'DIFFER', len(a[2]), 'same' if a[2] == b[2] else 'DIFFER'))
    if not same:
        failures.append('rebake ' + name)

rebake_matches('standalone', clf)          # T-LogE 48^3, the first bake of this run
rebake_matches('opendrt button', clf2)     # the OpenDRT button's own bake

# --- 9. model / mastering / interop metadata --------------------------------------


def meta_checks(name, path, node, expect_out, expect_cicp, grey_nits, in_id=None, conform=None, tail=None):
    nb = ET.parse(path).getroot().find('Info/CLFBake')
    model, mast, inter = nb.find('Model'), nb.find('Mastering'), nb.find('Interop')
    problems = []
    if callable(expect_out):
        expect_out = expect_out(nb)
    got_conform = float(inter.get('outputConform')) if inter is not None and inter.get('outputConform') else None
    if (conform is None) != (got_conform is None) or (conform is not None and abs(got_conform - conform) > 1e-9):
        problems.append('outputConform %s vs %s' % (got_conform, conform))
    if conform is not None and tail is not None:
        # the CLF must equal the node's output times the conforming scale
        lin = sample(img, W, H)
        via = [[c / conform for c in p] for p in apply_clf(path, lin)]   # compare in the node's own units
        err = max_err(via, sample(tail, W, H))
        if err > IMAGE_TOL:
            problems.append('conformed output err %.2e' % err)
    if model is None or model.get('name') != 'OpenDRT' or not model.get('version'):
        problems.append('Model element')
    else:
        ts = model.find('Tonescale')
        if ts is None or float(ts.get('tn_Lp')) != node['tn_Lp'].value() or ts.get('tn_su') != node['tn_su'].value() \
                or ts.get('tn_su_index') != str(int(node['tn_su'].getValue())):
            problems.append('Tonescale ids')
        # every model attribute is a real knob id with the same value as the node
        for e in model:
            for pid, val in e.attrib.items():
                if pid.endswith('_index'):
                    continue
                if pid not in node.knobs():
                    problems.append('unknown id %s' % pid)
                elif node[pid].Class() == 'Enumeration_Knob':
                    if val != node[pid].value():
                        problems.append('enum %s' % pid)
                elif node[pid].Class() == 'Boolean_Knob':
                    if val != ('true' if node[pid].value() else 'false'):
                        problems.append('bool %s' % pid)
                elif isinstance(node[pid].value(), float) and float(val) != node[pid].value():
                    problems.append('value %s' % pid)
    dcv = mast.find('DisplayColorVolume') if mast is not None else None
    if dcv is None or float(dcv.get('maxLuminance')) != node['tn_Lp'].value() or not dcv.get('white'):
        problems.append('DisplayColorVolume')
    lum = mast.find('Luminance') if mast is not None else None
    if lum is None or float(lum.get('greyMeasured', 0)) <= 0 or float(lum.get('diffuseWhiteMeasured', 0)) <= 0:
        problems.append('Luminance measured')
    elif grey_nits is not None and abs(float(lum.get('greyMeasured')) - grey_nits) > 0.03 * grey_nits:
        problems.append('greyMeasured %s vs nominal %.3g' % (lum.get('greyMeasured'), grey_nits))
    cicp = mast.find('CICP') if mast is not None else None
    if expect_cicp and (cicp is None or (cicp.get('primaries'), cicp.get('transfer')) != expect_cicp):
        problems.append('CICP')
    if (inter.get('output') if inter is not None else None) != expect_out:
        problems.append('Interop output')
    if (inter.get('input') if inter is not None else None) != in_id:
        problems.append('Interop input')
    print('%s metadata (%s)%s' % ('PASS' if not problems else 'FAIL', name, '' if not problems else ': ' + ', '.join(problems)))
    if problems:
        failures.append('metadata ' + name)


# SDR, default "dim" surround lifts grey above nominal, so only presence is checked;
# the default input gamut (Filmlight E-Gamut) has no published CIID -> namespaced
meta_checks('sdr rec1886', clf, drt, 'g24_rec709_display', ('1', '1'), None, in_id='opendrt-v1.1:lin_egamut_scene')
# PQ Rec.2100 1000 nit on a fresh node, with a mappable input gamut
d4 = paste(OPENDRT)[0]
d4.setInput(0, img)
d4['eotf'].setValue('PQ')
d4['display_gamut'].setValue('Rec.2020 (P3 Limited)')
d4['tn_Lp'].setValue(1000)
d4['tn_su'].setValue('dark')
d4['in_gamut'].setValue('ACEScg')
for n in nuke.allNodes():
    n.setSelected(False)
s3, g3 = paste(CLFBAKE)
if 'clfbake_shaper' not in s3.knobs():
    s3, g3 = g3, s3
s3.setInput(0, img)
d4.setInput(0, s3)
g3.setInput(0, d4)
g3['embed_script'].setValue(False)
clf_pq = os.path.join(OUT, 'test_pq.clf')
g3['file'].setValue(clf_pq)
g3['generate'].execute()
assert '<Script>' not in open(clf_pq).read(), 'embed_script off must omit the script'


def pq_expect(nb):   # P3-limited container and HDR diffuse white are modifiers on the published base
    dw = int(round(float(nb.find('Mastering/Luminance').get('diffuseWhiteMeasured'))))
    return 'opendrt-v1.1:pq_rec2020_display|p3lim|dw%d' % dw


meta_checks('pq rec2020 1000nit', clf_pq, d4, pq_expect, ('9', '16'),
            d4['tn_Lg'].value() * (1 + d4['tn_gb'].value() * math.log(10, 2)), in_id='lin_ap1_scene')
nb_pq = ET.parse(clf_pq).getroot().find('Info/CLFBake')
cond = nb_pq.find('Mastering/ViewingEnvironment').get('condition')
fb = nb_pq.find('Interop').get('outputFallback')
print('%s pq viewing condition / fallback: %s / %s' % ('PASS' if (cond, fb) == ('cinema1000', 'pq_rec2020_display') else 'FAIL', cond, fb))
if (cond, fb) != ('cinema1000', 'pq_rec2020_display'):   # dark surround = cinema, wide gamut implied
    failures.append('pq condition/fallback')

# DCDM X'Y'Z' 2.6: OpenDRT's X'Y'Z' output already carries DCDM's 48/52.37 headroom
# (its DCDM_Normalize node), so the codes are the published encoding with no conform
d4['eotf'].setValue('2.6 Power DCI')
d4['display_gamut'].setValue("X'Y'Z'")
d4['tn_Lp'].setValue(100)
clf_xyz = os.path.join(OUT, 'test_xyz.clf')
g3['file'].setValue(clf_xyz)
g3['generate'].execute()
meta_checks('dcdm xyz 2.6', clf_xyz, d4, 'g26_xyzd65_display', ('10', '17'), None, in_id='lin_ap1_scene')
# linear CIE XYZ D65 at 1000 nit peak: OCIO display interchange, 1.0 = 100 cd/m2, so scale 10,
# with OpenDRT's 48/52.37 headroom undone
d4['eotf'].setValue('Linear')
d4['tn_Lp'].setValue(1000)
clf_lx = os.path.join(OUT, 'test_linxyz.clf')
g3['file'].setValue(clf_lx)
g3['generate'].execute()
meta_checks('linear xyz 1000nit', clf_lx, d4, 'ocio:lin_ciexyzd65_display', ('10', '8'), None, in_id='lin_ap1_scene',
            conform=10.0 * 52.37 / 48.0, tail=d4)

# --- 10. automatic file name and the parameter string --------------------------------


def auto_bake(g, d, label):
    g['file'].setValue(OUT + '/')          # directory only
    g['generate'].execute()
    path = g['file'].value()
    base = os.path.basename(path)
    print('   %-28s %s' % (label, base))
    return path, base


# drt is modified (tn_con, hs_r, ...), tn_Lp 200: expect a hash, not a look name
shaper['preset'].setValue(0)   # back to T-LogE after the auto section
auto_path, base = auto_bake(gen, drt, 'modified node')
pat = r'OpenDRT-v1\.1\.0_[0-9a-f]{8}_video200__lin_egamut__to__g24_rec709__48\.clf$'
ok_mod = re.match(pat, base) is not None and os.path.exists(auto_path)
# untouched node: look name
for n in nuke.allNodes():
    n.setSelected(False)
s6, g6 = paste(CLFBAKE)
if 'clfbake_shaper' not in s6.knobs():
    s6, g6 = g6, s6
d6 = paste(OPENDRT)[0]
s6.setInput(0, img); d6.setInput(0, s6); g6.setInput(0, d6)
_, base6 = auto_bake(g6, d6, 'untouched node')
ok_std = re.match(r'OpenDRT-v1\.1\.0_Standard_video100__lin_egamut__to__g24_rec709__48\.clf$', base6) is not None
# tonescale preset applied over Standard: tonescale name + hash (look no longer matches)
vals = d6['tn_presets'].values()
for i in range(0, len(vals) - 1, 2):
    if vals[i].endswith('/Low Contrast'):
        nuke.tcl(vals[i + 1].replace('knobs this', 'knobs %s' % d6.fullName()))
_, base_tn = auto_bake(g6, d6, 'tonescale Low Contrast')
ok_tn = re.match(r'OpenDRT-v1\.1\.0_LowContrast-[0-9a-f]{8}_video100__lin_egamut__to__g24_rec709__48\.clf$', base_tn) is not None
# same look parameters twice -> same hash (deterministic), display change does not alter it
d6['tn_Lp'].setValue(400)
_, base_tn2 = auto_bake(g6, d6, 'same look, Lp 400')
look_of = lambda b: '_'.join(b.split('__')[0].split('_')[1:-1])   # OpenDRT-v.._<look>_<condition>
ok_det = look_of(base_tn) == look_of(base_tn2) and '_video400__' in base_tn2
print('%s auto file names: modified %s, untouched %s, tonescale %s, deterministic %s'
      % ('PASS' if all((ok_mod, ok_std, ok_tn, ok_det)) else 'FAIL', ok_mod, ok_std, ok_tn, ok_det))
if not all((ok_mod, ok_std, ok_tn, ok_det)):
    failures.append('auto file names')

# the CLF id is the parameter string; applying it to another node reproduces every recorded knob
pid = ET.parse(auto_path).getroot().get('id')
params_el = ET.parse(auto_path).getroot().find('Info/CLFBake/Params').text
ok_id = pid.startswith('opendrt1_1{') and 'clfbake{' in pid and pid.startswith(params_el)
d6['clf_params'].setValue(pid)
d6['apply_params'].execute()
recorded = list(clf_core(auto_path)[2])
bad = [k for k in recorded if drt[k].toScript() != d6[k].toScript()]
print('%s parameter string: id ok %s, applied to a fresh node %d/%d recorded knobs equal %s'
      % ('PASS' if ok_id and not bad else 'FAIL', ok_id, len(recorded) - len(bad), len(recorded), bad))
if not ok_id or bad:
    failures.append('parameter string')
print('   id:', pid[:160] + ('...' if len(pid) > 160 else ''))
# the OpenDRT button names its file the same way and fills the params field
d2['clf_file'].setValue(OUT + '/')
d2['bake_clf'].execute()
base2 = os.path.basename(d2['clf_file'].value())
ok_btn = re.match(r'OpenDRT-v1\.1\.0_[0-9a-f]{8}_video200__lin_egamut__to__g24_rec709__48\.clf$', base2) is not None \
    and d2['clf_params'].value().startswith('opendrt1_1{')
print('%s opendrt button auto name: %s' % ('PASS' if ok_btn else 'FAIL', base2))
if not ok_btn:
    failures.append('button auto name')

# --- 11. Cinespace output -----------------------------------------------------------
gen['format'].setValue('csp')
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
csp = gen['file'].value()
gen['format'].setValue('clf')
txt = open(csp).read().splitlines()
ok_csp = csp.endswith('.csp') and txt[0] == 'CSPLUTV100' and txt[1] == '3D' and txt.count('4096') == 3 \
    and any(l.startswith('id opendrt1_1{') for l in txt)
print('%s csp structure: %s' % ('PASS' if ok_csp else 'FAIL', os.path.basename(csp)))
if not ok_csp:
    failures.append('csp structure')
shaper.setInput(0, img)
live = sample(gen, W, H)
# end to end through OCIO, whose csp reader resamples the prelut into a uniform
# 65536-entry 1D LUT over its input range (coarse in the shadows for a 512 top)
check('csp: vs Nuke (OCIO reader)', max_err(apply_clf(csp, lin), live), IMAGE_TOL)
# structural: the prelut points lie exactly on the CLF's Log node, and the cube
# rows are the CLF's rows (csp red-fastest, CLF blue-fastest)
lp = clf_core(auto_path)[0]
log = ocio.LogCameraTransform(base=2.0, linSideBreak=[float(lp['linSideBreak'])] * 3,
                              logSideSlope=[float(lp['logSideSlope'])] * 3, logSideOffset=[float(lp['logSideOffset'])] * 3,
                              linSideSlope=[float(lp['linSideSlope'])] * 3, linSideOffset=[float(lp['linSideOffset'])] * 3,
                              linearSlope=[float(lp['linearSlope'])] * 3)
lcpu = ocio.Config.CreateRaw().getProcessor(log).getDefaultCPUProcessor()
i = txt.index('END METADATA') + 2
n_pre = int(txt[i]); pre_in = [float(v) for v in txt[i + 1].split()]; pre_out = [float(v) for v in txt[i + 2].split()]
pre_err = max(abs(lcpu.applyRGB([x, x, x])[0] - y) for x, y in zip(pre_in, pre_out))
check('csp: prelut points on the Log node', pre_err, 1e-5)
size_line = next(k for k, l in enumerate(txt) if l.split() == ['48', '48', '48'])
csp_rows = [[float(v) for v in l.split()] for l in txt[size_line + 1:size_line + 1 + 48 ** 3]]
N = 48
csp_bf = [csp_rows[r + N * g + N * N * b] for r in range(N) for g in range(N) for b in range(N)]
cube_err = max(abs(a - b) for ra, rb in zip(csp_bf, clf_core(auto_path)[1]) for a, b in zip(ra, [float(v) for v in rb]))
check('csp: cube vs CLF lattice', cube_err, 1e-5)
print('%s csp: %d cube rows, prelut %d points' % ('PASS' if len(csp_rows) == N ** 3 and n_pre == 4096 else 'FAIL', len(csp_rows), n_pre))
if not (len(csp_rows) == N ** 3 and n_pre == 4096):
    failures.append('csp cube rows')

# --- 12. log input with a code range beyond [0, 1] ----------------------------------
shaper['preset'].setValue(0)
shaper['code_min'].setValue(0.0)
shaper['code_max'].setValue(1.0)
gen['log_input'].setValue(True)
gen['domain'].setValue('auto')
gen['format'].setValue('clf')
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
clf_rng = gen['file'].value()
print('status:', gen['status'].value())
gen['domain'].setValue('preset')
cmax, cmin = shaper['code_max'].value(), shaper['code_min'].value()
root_r = ET.parse(clf_rng).getroot()
rng = root_r.find('Range')
in_id_r = root_r.find('Info/CLFBake/Interop').get('input')
ok_rng = cmax > 1.0 and rng is not None and abs(float(rng.find('maxInValue').text) - cmax) < 1e-9 \
    and root_r.find('Log') is None and '|codes' in in_id_r and '-codes' not in os.path.basename(clf_rng) \
    and '-to' in os.path.basename(clf_rng)
print('%s log input code range: code_max %.3f, Range node %s, input %s\n   %s' % (
    'PASS' if ok_rng else 'FAIL', cmax, 'present' if rng is not None else 'MISSING', in_id_r, os.path.basename(clf_rng)))
if not ok_rng:
    failures.append('log input code range')
# apply to log-encoded pixels of an image that reaches above code 1.0
img_r = test_image(log_to_lin(shaper, cmax), log_to_lin(shaper, cmin), 'TestImageRange')
shaper.setInput(0, img_r)
lin_r = sample(img_r, W, H)
logpix = [[lin_to_log(shaper, c) for c in p] for p in lin_r]
assert max(max(p) for p in logpix) > 1.0, 'range image must exceed code 1.0'
check('log input range: CLF vs Nuke', max_err(apply_clf(clf_rng, logpix), sample(gen, W, H)), IMAGE_TOL)
# the same bake as csp: the code range as a two-point prelut, no shaper curve
gen['format'].setValue('csp')
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
csp_r = gen['file'].value()
gen['format'].setValue('clf')
check('log input range csp: vs Nuke', max_err(apply_clf(csp_r, logpix), sample(gen, W, H)), IMAGE_TOL)
gen['log_input'].setValue(False)
shaper['code_min'].setValue(0.0)
shaper['code_max'].setValue(1.0)
shaper.setInput(0, img)

# --- 13. levels: legal in / legal out as removable unclamped Range nodes --------------
LO, HI = 64.0 / 1023.0, 940.0 / 1023.0
to_legal = lambda v: LO + v * (HI - LO)
gen['log_input'].setValue(True)
gen['levels'].setValue('legal in and out')
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
clf_ll = gen['file'].value()
root_ll = ET.parse(clf_ll).getroot()
nodes_ll = [e for e in root_ll if e.tag in ('Range', 'Log', 'LUT3D', 'Matrix')]
ok_struct = nodes_ll[0].tag == 'Range' and nodes_ll[0].get('style') == 'noClamp' and nodes_ll[-1].tag == 'Range' \
    and nodes_ll[-1].get('style') == 'noClamp' and "levels{'LL'}" in root_ll.get('id') and '-LL__' in os.path.basename(clf_ll) \
    and root_ll.find('Info/CLFBake/Mastering/CICP').get('fullRange') == 'false'
print('%s levels LL structure: %s' % ('PASS' if ok_struct else 'FAIL', os.path.basename(clf_ll)))
if not ok_struct:
    failures.append('levels structure')
logpix = [[lin_to_log(shaper, c) for c in p] for p in lin]
live = sample(gen, W, H)
legal_in_px = [[to_legal(c) for c in p] for p in logpix]
legal_live = [[to_legal(c) for c in p] for p in live]
check('levels LL: legal codes in -> legal out', max_err(apply_clf(clf_ll, legal_in_px), legal_live), IMAGE_TOL)
# delete the first Range -> full in, legal out; delete the last -> legal in, full out
for drop, name, src_px, ref in ((0, 'EL (first Range removed)', logpix, legal_live),
                                (-1, 'LE (last Range removed)', legal_in_px, live)):
    r = ET.parse(clf_ll).getroot()
    r.remove([e for e in r if e.tag == 'Range' and e.get('style') == 'noClamp'][drop])
    p = os.path.join(OUT, 'levels_%s.clf' % name[:2])
    ET.ElementTree(r).write(p, encoding='UTF-8', xml_declaration=True)
    check('levels %s' % name, max_err(apply_clf(p, src_px), ref), IMAGE_TOL)
gen['format'].setValue('csp')
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
check('levels LL csp: legal in -> legal out', max_err(apply_clf(gen['file'].value(), legal_in_px), legal_live), IMAGE_TOL)
gen['format'].setValue('clf')
gen['levels'].setValue('full')
gen['log_input'].setValue(False)

# --- 14. linear outputs: code-value cube + exact decode nodes --------------------------
def node_tags(path):
    return [e.tag + ('[' + e.get('style') + ']' if e.get('style') else '') + ('[half]' if e.get('halfDomain') else '')
            for e in ET.parse(path).getroot() if e.tag in ('Log', 'Range', 'LUT3D', 'Matrix', 'Exponent', 'FixedFunction', 'LUT1D')]


def t_npm(r, g, b, w):   # RGB -> XYZ from chromaticities (independent copy for the test)
    cols = [(x / y, 1.0, (1.0 - x - y) / y) for x, y in (r, g, b)]
    m = [[cols[j][i] for j in range(3)] for i in range(3)]
    wx = (w[0] / w[1], 1.0, (1.0 - w[0] - w[1]) / w[1])
    inv = t_inv(m)
    s = [sum(inv[i][k] * wx[k] for k in range(3)) for i in range(3)]
    return [[m[i][j] * s[j] for j in range(3)] for i in range(3)]


def t_inv(m):
    a, b, c = m[0]; d, e, f = m[1]; g, h, i = m[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
            [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
            [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]


def t_mul(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def t_mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def t_bradford(src, dst):
    B = [[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]]
    def cones(xy):
        X, Y, Z = xy[0] / xy[1], 1.0, (1.0 - xy[0] - xy[1]) / xy[1]
        return t_mul(B, [X, Y, Z])
    s, d = cones(src), cones(dst)
    return t_mm(t_inv(B), t_mm([[d[i] / s[i] if i == j else 0.0 for j in range(3)] for i in range(3)], B))


XYT = {'Rec.709': ((0.64, 0.33), (0.30, 0.60), (0.15, 0.06), (0.3127, 0.3290)),
       'P3-D65': ((0.680, 0.320), (0.265, 0.690), (0.150, 0.060), (0.3127, 0.3290)),
       'Rec.2020 (P3 Limited)': ((0.708, 0.292), (0.170, 0.797), (0.131, 0.046), (0.3127, 0.3290)),
       'P3-D60': ((0.680, 0.320), (0.265, 0.690), (0.150, 0.060), (0.32168, 0.33767))}


def pq_dec100(c):
    m1, m2, c1, c2, c3 = 2610 / 16384., 2523 / 32., 107 / 128., 2413 / 128., 2392 / 128.
    v = min(max(c, 0.0), 1.0) ** (1.0 / m2)
    return 100.0 * (max(v - c1, 0.0) / (c2 - c3 * v)) ** (1.0 / m1)


def expected_linear(codes, eotf, gamut, lp, target):
    """What the decode nodes must produce from the node's codes: CIF display scale
    (code 1.0 = 1.0 for the power EOTFs, 1.0 = 100 cd/m2 for PQ)."""
    out = []
    to_xyz = XYT[gamut] and t_npm(*XYT[gamut])
    white = XYT[gamut][3]
    cat = t_bradford(white, (0.3127, 0.3290)) if abs(white[0] - 0.3127) > 1e-6 else None
    tgt = {'lin_rec709_display': 'Rec.709', 'lin_p3d65_display': 'P3-D65'}.get(target)
    back = t_inv(t_npm(*XYT[tgt])) if tgt else None
    for p in codes:
        if eotf == 'PQ':
            lin = [pq_dec100(c) for c in p]
        else:
            gamma = {'2.4 Power - Rec.1886': 2.4, '2.6 Power DCI': 2.6, '2.2 Power - sRGB Display': 2.2}[eotf]
            lin = [max(c, 0.0) ** gamma for c in p]
        xyz = t_mul(to_xyz, lin)
        if cat:
            xyz = t_mul(cat, xyz)
        out.append(t_mul(back, xyz) if back else xyz)
    return out


def rel_err(a, b, scale):
    return max(abs(p - q) for pa, pb in zip(a, b) for p, q in zip(pa, pb)) / scale


# (a) SDR 2.4 Rec.709 at 200 nits -> lin_rec709_display: Exponent + Matrix, exact decode
gen['output'].setValue('lin_rec709_display')
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
clf_lin = gen['file'].value()
print('status:', gen['status'].value())
tags = node_tags(clf_lin)
r = ET.parse(clf_lin).getroot()
ok_a = tags == ['Log[cameraLinToLog]', 'LUT3D', 'Exponent[basicFwd]'] \
    and r.find('Info/CLFBake/Interop').get('output') == 'lin_rec709_display' \
    and r.find('Info/CLFBake/Interop').get('decoded') == 'true' and "output{'lin_rec709_display'}" in r.get('id') \
    and '__to__lin_rec709__' in os.path.basename(clf_lin)
print('%s decode SDR -> lin_rec709 structure: %s %s' % ('PASS' if ok_a else 'FAIL', tags, os.path.basename(clf_lin)))
if not ok_a:
    failures.append('decode SDR structure')
for n in (img, shaper, drt, gen):
    n.sample('red', 0.5, 0.5)
live = sample(gen, W, H)                      # the node's codes
exp = expected_linear(live, drt['eotf'].value(), 'Rec.709', drt['tn_Lp'].value(), 'lin_rec709_display')
check('decode SDR: CLF vs decoded Nuke codes (rel to 2.0)', rel_err(apply_clf(clf_lin, lin), exp, 2.0), IMAGE_TOL)
shaper['pattern'].setValue(True)
lin_l, live_l = sample(shaper, W, H), sample(gen, W, H)
shaper['pattern'].setValue(False)
exp_l = expected_linear(live_l, drt['eotf'].value(), 'Rec.709', drt['tn_Lp'].value(), 'lin_rec709_display')
check('decode SDR: lattice exact (rel)', rel_err(apply_clf(clf_lin, lin_l), exp_l, 2.0), 1e-4)
# (b) PQ Rec.2020 (P3 limited) 1000 nit -> lin_ciexyzd65_display, half-domain decode, CLF
d4['eotf'].setValue('PQ'); d4['display_gamut'].setValue('Rec.2020 (P3 Limited)'); d4['tn_Lp'].setValue(1000); d4['clamp'].setValue(True)
g3['output'].setValue('lin_ciexyzd65_display'); g3['format'].setValue('clf'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
clf_pql = g3['file'].value()
tags = node_tags(clf_pql)
ok_b = tags == ['Log[cameraLinToLog]', 'LUT3D', 'LUT1D[half]', 'Matrix'] and '__to__lin_ciexyzd65' in os.path.basename(clf_pql)
print('%s decode PQ -> lin_ciexyzd65 structure: %s' % ('PASS' if ok_b else 'FAIL', tags))
if not ok_b:
    failures.append('decode PQ structure')
for n in (img, s3, d4, g3):
    n.sample('red', 0.5, 0.5)
live4 = sample(g3, W, H)
exp4 = expected_linear(live4, 'PQ', 'Rec.2020 (P3 Limited)', 1000, 'lin_ciexyzd65_display')
check('decode PQ: CLF vs decoded Nuke codes (rel to 10)', rel_err(apply_clf(clf_pql, lin), exp4, 10.0), IMAGE_TOL)
# (c) same as CTF 2.4: PQ_TO_Lin
g3['format'].setValue('ctf'); g3['ocio'].setValue('2.4'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
ctf_pql = g3['file'].value()
r = ET.parse(ctf_pql).getroot()
tags = node_tags(ctf_pql)
ok_c = r.get('version') == '2.4' and tags == ['Log[cameraLinToLog]', 'LUT3D', 'FixedFunction[PQ_TO_Lin]', 'Matrix']
print('%s decode PQ CTF 2.4 structure: version %s %s' % ('PASS' if ok_c else 'FAIL', r.get('version'), tags))
if not ok_c:
    failures.append('decode PQ CTF structure')
g3['format'].setValue('clf'); g3['ocio'].setValue('2.1')
# (d) P3-D60 2.6 container -> lin_p3d65_display: decoded with the P3-D65 matrix (as
#     OpenDRT encodes it) and Bradford-adapted from the measured render white to D65,
#     so a neutral input is D65, equal RGB, in the linear target
d4['eotf'].setValue('2.6 Power DCI'); d4['display_gamut'].setValue('P3-D60'); d4['tn_Lp'].setValue(100)
g3['output'].setValue('lin_p3d65_display'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
clf_d60 = g3['file'].value()
r = ET.parse(clf_d60).getroot()
adapt = r.find('Info/CLFBake/Interop').get('adaptation') or ''
ok_d = node_tags(clf_d60) == ['Log[cameraLinToLog]', 'LUT3D', 'Exponent[basicFwd]', 'Matrix'] and adapt.startswith('Bradford render white')
print('%s decode P3-D60 -> lin_p3d65: adaptation "%s"' % ('PASS' if ok_d else 'FAIL', adapt))
if not ok_d:
    failures.append('decode P3-D60 structure')
neutral = [[v] * 3 for v in [0.18 * 2 ** (s / 2.0) for s in range(-12, 11)] + [1e3, 1e4, 1e6]]


def neutral_spread(path):
    # OpenDRT mixes container and creative white in by intensity (cwp_lm), so only a
    # white is promised D65: check the whites above the shaper's top (the LUT's white
    # corner, which the adaptation neutralises by construction), report the whole ramp
    out_n = apply_clf(path, neutral)
    peak = max(max(p) for p in out_n)
    whites = [p for n_in, p in zip(neutral, out_n) if n_in[0] >= 1e3]
    return (max(max(p) - min(p) for p in whites) / peak,
            max(max(p) - min(p) for p in out_n if max(p) > 1e-3) / peak)


spread_w, spread_all = neutral_spread(clf_d60)
check('decode P3-D60: white -> D65 equal RGB (rel)', spread_w, 1e-4)
print('   full-ramp neutral spread %.2e (OpenDRT\'s creative white limit mixes by intensity)' % spread_all)
# the same with a D60 creative white in a Rec.709 container: the sim is adapted away downstream
d4['display_gamut'].setValue('Rec.709'); d4['eotf'].setValue('2.4 Power - Rec.1886'); d4['cwp'].setValue('D60')
g3['output'].setValue('lin_rec709_display'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
spread_w, spread_all = neutral_spread(g3['file'].value())
check('decode cwp D60 / Rec.709: white -> D65 equal RGB (rel)', spread_w, 1e-4)
print('   full-ramp neutral spread %.2e' % spread_all)
print('   ', os.path.basename(g3['file'].value()))
d4['cwp'].setValue('D65')

# (f) DCDM X'Y'Z' 2.6 at 48 cd/m2 -> lin_ciexyzd65_display: the CIF g26_xyzd65_display decode,
#     a 2.6 power then 52.37/48, which undoes the headroom OpenDRT's X'Y'Z' output carries, so
#     reference white (48 cd/m2) is Y = 1.0
d4['eotf'].setValue('2.6 Power DCI'); d4['display_gamut'].setValue("X'Y'Z'"); d4['tn_Lp'].setValue(48)
g3['output'].setValue('lin_ciexyzd65_display'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
clf_dcdm = g3['file'].value()
tags = node_tags(clf_dcdm)
adapt_f = ET.parse(clf_dcdm).getroot().find('Info/CLFBake/Interop').get('adaptation')
ok_f = tags == ['Log[cameraLinToLog]', 'LUT3D', 'Exponent[basicFwd]', 'Matrix'] \
    and '__to__lin_ciexyzd65__' in os.path.basename(clf_dcdm)
print('%s decode DCDM X\'Y\'Z\' 48 nit -> lin_ciexyzd65 structure: %s adaptation: %s' % ('PASS' if ok_f else 'FAIL', tags, adapt_f))
if not ok_f:
    failures.append('decode DCDM structure')
for n in (img, shaper, d4, g3):
    n.sample('red', 0.5, 0.5)
live_f = sample(g3, W, H)
exp_f = [[max(c, 0.0) ** 2.6 * 52.37 / 48 for c in p] for p in live_f]   # XYZ, 1.0 = 48 cd/m2 reference white
check('decode DCDM: CLF vs codes^2.6 x 52.37/48 (rel to 1.1)', rel_err(apply_clf(clf_dcdm, lin), exp_f, 1.1), IMAGE_TOL)
white_f = apply_clf(clf_dcdm, [[1e6] * 3])[0]
check('decode DCDM: peak white is Y = 1 (48 cd/m2)', abs(white_f[1] - 1.0), 1e-2)

# (e) HLG cannot be decoded: falls back to codes with a note
d4['eotf'].setValue('HLG'); d4['display_gamut'].setValue('Rec.2020 (P3 Limited)'); d4['tn_Lp'].setValue(1000)
g3['output'].setValue('lin_ciexyzd65_display'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
ok_e = 'HLG cannot be decoded' in g3['status'].value() and node_tags(g3['file'].value()) == ['Log[cameraLinToLog]', 'LUT3D'] \
    and 'hlg_rec2020' in os.path.basename(g3['file'].value())
print('%s decode HLG falls back to codes: %s' % ('PASS' if ok_e else 'FAIL', os.path.basename(g3['file'].value())))
if not ok_e:
    failures.append('decode HLG fallback')
gen['output'].setValue('display codes'); g3['output'].setValue('display codes')


# --- 15. ODT node: lin_ciexyzd65_display <-> the CIF display colorspaces --------------
# (a) the node against OCIO, display by display: the CIF config's transforms rebuilt
#     from OCIO operators with independently computed matrices (OCIO 2.2/2.3 lack the
#     HLG OETF builtin, so that last step is BT.2100 of E/3, as OCIO 2.4 defines it)
import clfbake
XYT['Rec.2020'] = XYT['Rec.2020 (P3 Limited)']
XYT['AdobeRGB'] = ((0.64, 0.33), (0.21, 0.71), (0.15, 0.06), (0.3127, 0.3290))
I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def hlg_oetf3(x):
    a = 0.17883277
    b, c = 1 - 4 * a, 0.5 - a * math.log(4 * a)
    e = abs(x) / 3.0
    return math.copysign(math.sqrt(3 * e) if e <= 1 / 12. else a * math.log(12 * e - b) + c, x)


def cif_forward(d):
    m = t_inv(t_npm(*XYT[d[2]])) if d[2] else I3
    m = [[v * d[5] for v in row] for row in m]
    ts = [ocio.MatrixTransform([m[0][0], m[0][1], m[0][2], 0, m[1][0], m[1][1], m[1][2], 0,
                                m[2][0], m[2][1], m[2][2], 0, 0, 0, 0, 1])]
    if d[3] == 'gamma':
        ts.append(ocio.ExponentTransform([d[4]] * 3 + [1.0], negativeStyle=ocio.NEGATIVE_MIRROR,
                                         direction=ocio.TRANSFORM_DIR_INVERSE))
    elif d[3] == 'srgb':
        ts.append(ocio.ExponentWithLinearTransform([2.4] * 3 + [1.0], [0.055] * 3 + [0.0], negativeStyle=ocio.NEGATIVE_MIRROR,
                                                   direction=ocio.TRANSFORM_DIR_INVERSE))
    elif d[3] == 'pq':
        ts.append(ocio.BuiltinTransform('CURVE - LINEAR_to_ST-2084'))
    elif d[3] == 'hlg':
        ts.append(ocio.FixedFunctionTransform(ocio.FIXED_FUNCTION_REC2100_SURROUND, [1 / 1.2]))
    if d[3] == 'pq':   # OCIO < 2.4 clamps negatives in this builtin; the CIF config (2.4+) mirrors
        pq = ocio.Config.CreateRaw().getProcessor(ts.pop()).getOptimizedCPUProcessor(ocio.OPTIMIZATION_NONE)
    cpu = ocio.Config.CreateRaw().getProcessor(ocio.GroupTransform(ts)).getOptimizedCPUProcessor(ocio.OPTIMIZATION_NONE)
    if d[3] == 'hlg':
        return lambda p: [hlg_oetf3(v) for v in cpu.applyRGB(list(p))]
    if d[3] == 'pq':
        return lambda p: [math.copysign(pq.applyRGB([abs(v)] * 3)[0], v) for v in cpu.applyRGB(list(p))]
    return lambda p: cpu.applyRGB(list(p))


probes = []
for y in (0.0001, 0.01, 0.18, 1.0, 2.03, 10.0, 100.0):            # 1.0 = 100 cd/m2
    probes += [[0.9505 * y, y, 1.089 * y], [0.4124 * y, 0.2126 * y, 0.0193 * y], [0.3 * y, 0.5 * y, 0.9 * y]]
probes.append([-0.05, 0.02, 0.01])
NP = len(probes)
nuke.addFormat('%d 1 0 0 %d 1 1 clfbake_odt_probe' % (NP, NP))
pc = nuke.nodes.Constant()
pc['format'].setValue('clfbake_odt_probe')
psrc = nuke.nodes.Expression(inputs=[pc])
o1 = paste(os.path.join(HERE, 'ODT.nk'))[0]
o1.setInput(0, psrc)


def run_odt(values):
    for c in range(3):
        psrc['expr%d' % c].setValue('+'.join('(x>=%d&&x<%d?%r:0)' % (i, i + 1, v[c]) for i, v in enumerate(values)))
    o1.sample('red', 0.5, 0.5)
    return [[o1.sample(ch, i + 0.5, 0.5) for ch in ('red', 'green', 'blue')] for i in range(NP)]


def rel_floor(a, b):
    return max(abs(x - y) / max(abs(y), 1e-3) for pa, pb in zip(a, b) for x, y in zip(pa, pb))


worst = (0.0, '')
for i, d in enumerate(clfbake.DISPLAYS):
    ref = cif_forward(d)
    enc = [ref(p) for p in probes]
    o1['display'].setValue(i)
    o1['direction'].setValue('forward')
    e_f = rel_floor(run_odt(probes), enc)
    o1['direction'].setValue('inverse')
    e_i = rel_floor(run_odt(enc), probes)
    worst = max(worst, (max(e_f, e_i), d[0]))
    if max(e_f, e_i) > 2e-4:
        print('FAIL odt %s: forward %.2e inverse %.2e' % (d[0], e_f, e_i))
        failures.append('odt ' + d[0])
print('%s odt node vs OCIO, %d displays forward and inverse: worst %.2e (%s) (tol 2e-4)' % (
    'PASS' if worst[0] <= 2e-4 else 'FAIL', len(clfbake.DISPLAYS), worst[0], worst[1]))

# (b) ODT nodes at the end of a chain are written as exact process nodes. OpenDRT
#     Rec.1886 -> ODT inverse -> ODT forward lin_rec709 equals the output menu's lin_rec709
ix = dict((d[0].split(':')[-1], i) for i, d in enumerate(clfbake.DISPLAYS))
o2 = paste(os.path.join(HERE, 'ODT.nk'))[0]
o1['display'].setValue(ix['g24_rec709_display']); o1['direction'].setValue('inverse')
o2['display'].setValue(ix['lin_rec709_display']); o2['direction'].setValue('forward')
o1.setInput(0, drt); o2.setInput(0, o1); gen.setInput(0, o2)
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
clf_o = gen['file'].value()
r = ET.parse(clf_o).getroot()
tags = node_tags(clf_o)
ok = tags == ['Log[cameraLinToLog]', 'LUT3D', 'Exponent[basicMirrorFwd]'] \
    and r.find('Info/CLFBake/Interop').get('output') == 'lin_rec709_display' \
    and not o1['disable'].value() and not o2['disable'].value() and '__to__lin_rec709__' in os.path.basename(clf_o)
print('%s odt tail -> exact ops: %s %s' % ('PASS' if ok else 'FAIL', tags, os.path.basename(clf_o)))
if not ok:
    failures.append('odt tail structure')
for n in (img, shaper, drt, o1, o2, gen):
    n.sample('red', 0.5, 0.5)
check('odt tail: CLF vs Nuke (rel to 2.0)', rel_err(apply_clf(clf_o, lin), sample(gen, W, H), 2.0), IMAGE_TOL)
check('odt tail = output menu lin_rec709 (rel to 2.0)', rel_err(apply_clf(clf_o, lin), apply_clf(clf_lin, lin), 2.0), 1e-6)
# (c) HDR: PQ Rec.2020 -> ODT inverse -> ODT forward sRGB, as CLF and as CTF 2.4
d4['eotf'].setValue('PQ'); d4['display_gamut'].setValue('Rec.2020 (P3 Limited)'); d4['tn_Lp'].setValue(1000)
o1['display'].setValue(ix['pq_rec2020_display']); o1['direction'].setValue('inverse')
o2['display'].setValue(ix['srgb_rec709_display']); o2['direction'].setValue('forward')
o1.setInput(0, d4); g3.setInput(0, o2)
g3['file'].setValue(OUT + '/')
g3['generate'].execute()
clf_h = g3['file'].value()
tags = node_tags(clf_h)
ok = tags == ['Log[cameraLinToLog]', 'LUT3D', 'LUT1D[half]', 'Matrix', 'Exponent[monCurveMirrorRev]']
print('%s odt tail HDR -> sRGB: %s' % ('PASS' if ok else 'FAIL', tags))
if not ok:
    failures.append('odt tail HDR structure')
for n in (img, s3, d4, o1, o2, g3):
    n.sample('red', 0.5, 0.5)
check('odt tail HDR: CLF vs Nuke (rel to 3.0)', rel_err(apply_clf(clf_h, lin), sample(g3, W, H), 3.0), IMAGE_TOL)
g3['format'].setValue('ctf'); g3['ocio'].setValue('2.4'); g3['file'].setValue(OUT + '/')
g3['generate'].execute()
tags = node_tags(g3['file'].value())
ok = tags == ['Log[cameraLinToLog]', 'LUT3D', 'FixedFunction[PQ_TO_Lin]', 'Matrix', 'Exponent[monCurveMirrorRev]'] \
    and ET.parse(g3['file'].value()).getroot().get('version') == '2.4'
print('%s odt tail HDR as CTF 2.4: %s' % ('PASS' if ok else 'FAIL', tags))
if not ok:
    failures.append('odt tail CTF 2.4')
g3['format'].setValue('clf'); g3['ocio'].setValue('2.1')
# (d) an HLG ODT has no CLF operator: it is baked, and still names the output
o2['display'].setValue(ix['hlg_rec2020_display'])
g3['file'].setValue(OUT + '/')
g3['generate'].execute()
r = ET.parse(g3['file'].value()).getroot()
cicp = r.find('Info/CLFBake/Mastering/CICP')
ok = node_tags(g3['file'].value()) == ['Log[cameraLinToLog]', 'LUT3D'] \
    and r.find('Info/CLFBake/Interop').get('output').split(':')[-1].startswith('hlg_rec2020_display') \
    and cicp is not None and (cicp.get('primaries'), cicp.get('transfer')) == ('9', '18')
print('%s odt HLG is baked and names the output: %s' % ('PASS' if ok else 'FAIL', os.path.basename(g3['file'].value())))
if not ok:
    failures.append('odt HLG')
# (e) the ODT agrees with OpenDRT's own encoders on neutrals: OpenDRT to a display (clamp
#     off) equals OpenDRT to linear X'Y'Z' at the same peak, then ODT forward. Only neutrals:
#     OpenDRT compresses purity toward the display gamut it renders for, so saturated colours
#     rendered to X'Y'Z' and re-encoded differ from a render to that display, by design.
#     And an ODT to gamma 2.2 P3-D65, not a published CIF display, gets OpenDRT's ID for it
nramp = nuke.nodes.Expression(inputs=[img], expr0='0.18*pow(2,18*(x/width-0.6))', expr1='0.18*pow(2,18*(x/width-0.6))',
                              expr2='0.18*pow(2,18*(x/width-0.6))')   # an input: sourceless images sample black on 15.1
o1['direction'].setValue('forward')
worst, extra = 0.0, []
for eotf, gamut, lp, disp in (('2.2 Power - sRGB Display', 'P3-D65', 100, 'g22_p3d65_display'),
                              ('2.4 Power - Rec.1886', 'Rec.709', 100, 'g24_rec709_display'),
                              ('2.6 Power DCI', 'P3-D65', 48, 'g26_p3d65_display')):
    # fresh nodes, knobs set before their first sample: in nuke -t 15.1 an OpenDRT node
    # sampled straight after a knob change reads black
    pair = []
    for e, g in ((eotf, gamut), ('Linear', "X'Y'Z'")):
        n = paste(OPENDRT)[0]
        n['clamp'].setValue(False); n['tn_Lp'].setValue(lp); n['eotf'].setValue(e); n['display_gamut'].setValue(g)
        n.setInput(0, nramp)
        pair.append(n)
    undo = nuke.nodes.Multiply(inputs=[pair[1]], value=52.37 / 48)   # OpenDRT's X'Y'Z' headroom
    o1.setInput(0, undo)
    o1['display'].setValue(ix[disp])
    worst = max(worst, rel_floor(sample(o1, W, H), sample(pair[0], W, H)))
    extra += pair + [undo]
# 2e-3: OpenDRT's X'Y'Z' white sits about 2e-4 off D65 in xy
check('odt forward = OpenDRT\'s own encoders on neutrals (g22 P3-D65, g24 Rec.709, g26 P3-D65)', worst, 2e-3)
o2['display'].setValue(ix['g22_p3d65_display']); o2['direction'].setValue('forward')
o1['display'].setValue(ix['g24_rec709_display']); o1['direction'].setValue('inverse')
o1.setInput(0, drt); gen.setInput(0, o2)
gen['file'].setValue(OUT + '/')
gen['generate'].execute()
r = ET.parse(gen['file'].value()).getroot()
out_o = r.find('Info/CLFBake/Interop').get('output')
cicp = r.find('Info/CLFBake/Mastering/CICP')
ok = out_o == 'opendrt-v1.1:g22_p3d65_display' and node_tags(gen['file'].value()) == \
    ['Log[cameraLinToLog]', 'LUT3D', 'Exponent[basicMirrorFwd]', 'Matrix', 'Exponent[basicMirrorRev]'] \
    and (cicp.get('primaries'), cicp.get('transfer')) == ('12', '4')
print('%s odt to gamma 2.2 P3-D65: output %s, %s' % ('PASS' if ok else 'FAIL', out_o, node_tags(gen['file'].value())))
if not ok:
    failures.append('odt g22 p3d65')
gen.setInput(0, drt); g3.setInput(0, d4)
for n in [o1, o2, psrc, pc, nramp] + extra:
    nuke.delete(n)


print('outputs in', OUT)
if failures:
    print('FAILED:', failures)
    sys.exit(1)
print('ALL PASS')
