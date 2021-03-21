# Open Display Transform

An open source, chromaticity preserving, simple neutral and robust display transform for preparing wide gamut scene-linear high dynamic range images for being presented on a display device. 

Currently available as a Nuke node. Resolve DCTL is planned once the design is in a less experimental stage.

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

# [Documentation](./doc)

