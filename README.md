# Open Display Transform
![OpenDRT v0.0.80](/docs/img/OpenDRT_Nuke_v0.0.80.png)
A simple, robust, and open source display transform for rendering wide gamut  high dynamic range scene-linear images on a display device. 

Currently available as a Nuke node. Resolve DCTL is coming.

## Design Goals

- **Simple** - Simplicity of design 
- **Robust** - Can handle a variety of extremes without breaking
- **Neutral** - No strong look, no creative intent, faithful to input imagery
- **Chromaticity Preserving** - Faithfully represent the chromaticity values of the input image
- **Information Preserving** - Preserve as much data as possible from the input image
- **Invertible** - Can operate in the forward and inverse directions within limitations
- **Separate the Look** - Intended to be used in conjunction with a look transform upstream in the processing chain

## What does a display transform do?

- Convert scene-referred to display-referred
  - Compress high dynamic range to low dynamic range
  - Compress wide gamut to smaller display gamut
- Apply chromaticity conversion and inverse EOTF to prepare image for display device

# Read the [Documentation](./docs)