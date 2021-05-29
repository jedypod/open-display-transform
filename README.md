# Open Display Transform
![OpenDRT v0.0.81b3 Nuke](/docs/img/OpenDRT_Nuke_v0.0.81b3.png)
![OpenDRT v0.0.81b3 Resolve](/docs/img/OpenDRT_Resolve_v0.0.81b3.png)

A simple and robust open source display transform for rendering wide gamut high dynamic range scene-linear images on an SDR or HDR display device.

Available as a node for Nuke or Nuke Non-Commercial, and a DCTL for Resolve Studio.

## Design Goals

- **Simple** - Simplicity of design 
- **Robust** - Handle extremes without breaking
- **Neutral** - No strong look, no creative intent, faithful to input image colorimetry
- **Chromaticity Preserving** - Faithfully represent the chromaticity values of the input image
- **Information Preserving** - Preserve as much data as possible from the input image
- **Invertible** - Can operate in the forward and inverse directions within the limitations of display-referred imagery
- **Look Not Included** - Intended to be used in conjunction with a look transform upstream

# Read the [Documentation](./docs)
