# Open Display Transform

An open collection of tools and experiments for rendering wide-gamut scene-linear data into an image for an SDR or HDR display device.

All tools are available as a node for Nuke or Nuke Non-Commercial, and as a DCTL for Resolve Studio. Matchbox shaders are in development.

## [Display Transforms](display-transforms)
- **OpenDRT**  
  A simple and robust display transform based on [CIE 2006 LMS](https://doi.org/10.2352/issn.2169-2629.2019.27.38) and the [Michaelis-Menten](http://retina.anatomy.upenn.edu/~rob/lance/michaelis.html) [Equation](https://community.acescentral.com/t/output-transform-tone-scale/3498/14).  
  Neutral appearance. Color preserving where possible, faithful to input image data.
- **rgbDT**  
  A classic per-channel display-transform. Uses a custom rendering gamut designed to handle input colorimetry beyond the bounds of the spectral locus without sacrificing image appearance.
- **JzDT**  
  Another experiment using the max(r,g,b) norm and the JzAzBz LMS space.

## [Look Transforms](look-transforms)
A collection of tools designed to creatively adjust image appearance.


# [Documentation](https://github.com/jedypod/open-display-transform/wiki)
There is a collection of documentation [available on the wiki](https://github.com/jedypod/open-display-transform/wiki).