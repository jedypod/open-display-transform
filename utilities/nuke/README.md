# CLFBake

Bake OpenDRT, or any chain of Nuke nodes, to a CLF, CTF or Cinespace file with
a parametric log shaper and metadata that can restore the settings or rebuild
the nodes. Nuke 15.1 or later.

**Install:** put this directory on `NUKE_PATH`. The node buttons call
`clfbake.py`; the nodes themselves carry no code, so scripts stay small and
render without it. `CLFBake.nk`, `ODT.nk` and OpenDRT.nk paste as they are, or
ship as ToolSets.

## Using it

Paste `CLFBake.nk` and put the chain between its two nodes:

```
image -> CLFShaper -> [ OpenDRT, looks, anything ] -> CLFGenerate
```

**CLFShaper**

| Knob | |
|---|---|
| shaper | Log encoding for the lattice: **T-LogE** (default, as in the released OpenDRT OCIO config), T-Log, ACEScct, LogC3, LogC4, S-Log3, Log3G10, DaVinci Intermediate, or Jed's XLog. Written to the CLF as an exact `Log` node. |
| cube size | 48 (default) as in the released config; 65 halves the error at 2.5x the size. |
| code range | Shaper codes the lattice spans, `[0, 1]` by default. T-LogE tops out at scene 512; raise the top for brighter content. |

**CLFGenerate**

| Knob | |
|---|---|
| file | Path, or a directory to name the file automatically. |
| format | `clf`, `ctf` or `csp`. |
| output | `display codes`, or a linear display target (`lin_ciexyzd65_display`, `lin_rec709_display`, `lin_p3d65_display`). |
| ctf target | `2.4` writes PQ decodes as the `PQ_TO_Lin` FixedFunction; `2.1` (default) as a half-domain LUT1D that OCIO 2.2 reads. |
| levels | `full` (default) or legal in/out, as unclamped `Range` nodes first/last: delete one to convert the file. |
| log input | Leave out the `Log` node; the file takes the shaper's log codes, as the released config does. |
| embed node script | Store the baked nodes so **From CLF** can rebuild them. |
| domain | `preset`, or `auto`: probe the chain and extend the code range if it still responds above the shaper's top. |
| Generate / Restore / From CLF | Bake; apply the file's knob values to the selected or upstream nodes; rebuild the baked nodes. |

**OpenDRT.nk** has a "CLF Helpers" group: Bake CLF (T-LogE, 48³), Restore
CLF, and a `params` field with Apply Params.

**ODT** (`ODT.nk`) converts between `lin_ciexyzd65_display` (1.0 = 100 cd/m²)
and the 16 display colorspaces of the Color Interop Forum's display config,
OCIO 2-style: sRGB, Rec.1886, gamma 2.2, Display P3 (and HDR), gamma 2.6
P3-D65, PQ P3-D65 and Rec.2100, HLG, AdobeRGB, both DCDMs, and the linear
Rec.709, P3-D65 and Rec.2020 displays. It also has OpenDRT's gamma 2.2 P3-D65,
which the CIF does not publish and which therefore gets OpenDRT's namespaced
ID. `forward` encodes from XYZ, `inverse` decodes to it. It is Expression and
ColorMatrix nodes, and matches OCIO evaluating that config to 6e-5. It
re-encodes colorimetrically and does not redo OpenDRT's gamut compression, so
render OpenDRT for the display you deliver where saturated colours matter. ODT nodes at the end of a chain are not baked:
CLFGenerate writes them as exact CLF operations after the cube. So
`OpenDRT -> ODT inverse -> ODT forward` reaches any display, or a linear one,
from the same code-value cube. HLG has no CLF operator and is baked instead.

**Domain.** T-LogE covers scene −0.0046 to 512, enough for camera footage, but
OpenDRT keeps rendering above it (to about 7,000 at 100 nits, 14,000 at 1000
nits PQ), so very bright CG clips in a `preset` bake. `auto` extends the range,
matching Nuke within 1e-2 up to the new top at a cost of 1.5 to 1.7x more error
below 512. That is why `preset` is the default.

**Linear outputs.** The `output` menu is a shortcut for the ODT pair above,
with two OpenDRT-specific additions. The cube is always baked code value to
code value; exact decode nodes follow it (`Exponent`, PQ `LUT1D` or
`PQ_TO_Lin`, one `Matrix`).
The scale is the CIF one: power EOTFs decode code 1.0 to 1.0, PQ to 1.0 = 100
cd/m². OpenDRT's X'Y'Z' output already carries DCDM's 48/52.37 headroom
(unless the creative white is cooler than D65), and decodes undo it, so a
DCDM white decodes to Y = 1. The render white is
Bradford-adapted to D65, so a white patch is D65 whatever the container or
creative white, and OpenDRT's P3-D60 and P3-DCI containers decode too. HLG is
refused, because OpenDRT.nk applies only 20.5% of the BT.2100 inverse OOTF
(`mix 0.205`) where the DCTL applies all of it.

**Cinespace.** Written directly: the shaper as a 4096-point prelut with
every point on the curve, then the cube through the same operations the CLF
applies after its LUT3D. OCIO's own csp reader resamples that prelut uniformly
and loses shadows, so for OCIO use a log-input csp (T-LogE in the config,
tetrahedral `FileTransform`), which equals the CLF exactly, or use the CLF.

**File names**

```
OpenDRT-v1.1.0_Standard_video100__lin_egamut2__to__g24_rec709__48.clf
OpenDRT-v1.1.0_LowContrast-6f137a09_cinema1000__lin_ap1__to__pq_rec2020-p3lim-dw148__48-to28k.clf
```

Version, look (preset name, else tonescale name plus a hash of the look
parameters, else the hash), viewing condition, input and output IDs, and the
lattice size, with `-to<top>` when the code range is extended.

**Parameter string.** Each OpenDRT bake's CLF `id` is the full parameter set,
`opendrt1_1{tonescale{tn_Lp{100.0}…}…}clfbake{…}`. Paste one into the OpenDRT
node's `params` and press Apply Params; `opendrt1_1{tn_Lp{1000}eotf{'PQ'}}`
works too.

## What the CLF contains

After the `Log` (unless log input), optional `Range` and `LUT3D` nodes,
`<Info><CLFBake>` holds:

- **Shaper**: preset, size, code range and LogCameraTransform parameters.
- **Nodes**: every user knob of every baked node, in `toScript` form.
- **Model**: OpenDRT's parameters by their own ids, shared with the DCTL.
- **Mastering**: ST 2086 display volume, grey and white measured from the
  chain, surround and condition token (`video100`, `cinema48`), creative
  white, H.273 code points.
- **Interop**: Color Interop IDs, published ones bare when exact, otherwise
  `opendrt-v1.1:<base>|<modifiers>` with a fallback. The modifiers are
  `p3lim`, `d60sim` and similar, `dw<nits>`, `clamp0`, `EE`/`LL`,
  `codes0to1.19`, and `dcdm` for PQ X'Y'Z' carrying OpenDRT's headroom.
- **Script**: the baked nodes, for From CLF.

OpenDRT's X'Y'Z' 2.6 already is `g26_xyzd65_display`; only a creative white
cooler than D65 needs a conforming `Matrix` to earn it. `ocio:lin_ciexyzd65_display`
is reached by one too, peak/100 × 52.37/48. Both are recorded as
`outputConform`.

## Testing

From this directory, with PyOpenColorIO (bundled with Nuke) as the independent
reader:

```
nuke -t test_clfbake.py                        # 56 checks, ~2 minutes; run on 15.1 too
nuke -t sweep_clfbake.py                       # every look, tonescale and display preset
CLFBAKE_DOMAIN=auto nuke -t sweep_clfbake.py
```

`CLFBAKE_PRESET=<n>` picks another shaper, set through the environment because
`nuke -t` treats a trailing number as a frame range.

## Updating

`clfbake.py` holds all the Python, including the display table the ODT node
and its CLF export share. `build_clfbake.py` builds the node layouts: it writes
`CLFBake.nk` and `ODT.nk`, and re-splices the CLF Helpers block into
OpenDRT.nk, between `clf_grp` and `endGroup_clf`. Rerun it after any change to
OpenDRT.nk.

```
nuke -t build_clfbake.py && nuke -t test_clfbake.py
```

Measured on the test chain, so not worth re-trying:

- Storing linear light, BT.709, sRGB, log or gamma-wrapped PQ in the cube
  instead of display codes is 1.2 to 2x worse.
- A fitted XLog ties an extended T-LogE range, and an equalised shaper buys
  about 15%; 65³ is the lever.
- The sweep's worst case, 3.3e-2 with purity compression off, is out-of-gamut
  nonlinearity, not the clamp.
