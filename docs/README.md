# Open Display Transform Documentation

Here you will find a collection of documentation about Open Display Transform.

## General

General information and usage instructions.

- **[Installation](doc_installation.md)**
  How to install OpenDRT in Nuke and Resolve.
- **[Parameters](doc_parameters.md)**
  Documentation about the basic parameters.

## Technical

- **[What is a Display Transform?](tech_display_transform_intro.md)**
  Introductory information about what a display transform is and what it does.
- **Display Gamut Volume**
  What is a display gamut volume and what makes it different from a scene gamut volume?
- **Per-Channel Display Transforms**
  General information about per-channel display transforms. How they are designed, and what effects this rendering style has on the look and behavior of images.
- **Chromaticity-Preserving Display Transforms**
  Chromaticity-preserving display transforms. How they are designed, and what effects they have on the look and behavior of images.
- **Norm**
  What is a norm and what does it do?
- **Render Colorspace**
  The render colorspace and what effect this has on image appearance.
- **Tonescale**
  Everything you need to know about tonemapping a scene-referred image to a display-referred image. Black mapping. flare / glare compensation. shoulder compression. what happens in HDR?
- **Chroma Compression**
  What is chroma compression and why is it needed? Remember the display gamut volume?
- **Perceptual Hue Paths**
  Biasing chroma compression hue paths to be perceptual.
- **Whitepoint**
  Technical whitepoint vs. creative whitepoint. filmlight link, chromaticity of peak, could be anything
- **High Dynamic Range**
  What is HDR and how does the render transform change in this mode? grey mapping increases, flare compensation reduced, peak white point changes
- **Glossary of Terms**
  If you're confused about the definition of any complex color science terms used in these docs, it might be defined here.

## Support Materials

- **[Footage](support_footage.md)**
  A collection of sources for scene-linear source footage.