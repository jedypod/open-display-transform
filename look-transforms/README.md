# Look Modification
Here you will find some tools to create look modification transforms, as well as some pre-built look presets.

## Tools
- **LinearGrade** : [Nuke](tools/nuke/LinearGrade.nk) | [Resolve](tools/resolve/LinearGrade.dctl)  
  Very simple chromaticity-preserving scene-linear grade operator: `offset -> pivoted contrast -> exposure`  
  ![LinearGrade UI](docs/img/ui/LinearGrade_ResolveUI.png)
- **ZoneGrade** : [Nuke](tools/nuke/ZoneGrade.nk) | [Resolve](tools/resolve/ZoneGrade.dctl)  
  A more sophisticated grading tool which allows exposure adjustments over select portions of the input luminance range. Designed for grading in scene-linear, controls are in exposure units around 18% grey. Includes 4 zones: 2 high, 2 low. Named after the Ansel Adams zone system which I remember so well from black and white darkroom photography!  
  ![ZoneGrade UI](docs/img/ui/ZoneGrade_Nuke.png)
- **NotoriousSix HueShift** : [Nuke](tools/nuke/n6HueShift.nk) | [Resolve](tools/resolve/n6HueShift.dctl)  
  Hue shift tool. Allows smooth shifts of hue per hue angle, for each of the primary and secondary colors: RGB, CMY. With an additional hue shift for a custom angle and width. Preset is for orange. You can also enable a zoned range selection, which will limit the hue shift to a range of input luminance, depending on how you set the zone range slider. Lower values include more midtones and shadows, higher less.  
  ![HueShift UI](docs/img/ui/NotoriousSix_HueShift_ResolveUI.png)
- **NotoriousSix Value** : [Nuke](tools/nuke/n6ChromaValue.nk) | [Resolve](tools/resolve/n6ChromaValue.dctl)  
  Adjusts brightness of color by hue angle.  
- **NotoriousSix Vibrance** : [Nuke](tools/nuke/n6Vibrance.nk) | [Resolve](tools/resolve/n6Vibrance.dctl)  
  Vibrance emulates what happens to hue and chroma in the bottom end of a per-channel contrast increase: Chroma is increased and secondary hues are bent towards primary hues. Image "richness" is increased without slamming into the gamut boundary as with a traditional saturation adjustment.  
- **Nayatani_HK** : [Nuke](tools/nuke/Nayatani_HK.nk) | [Resolve](tools/resolve/Nayatani_HK.dctl)  
  Implements the [Nayatani (1997) model](https://doi.org/10.1002/(SICI)1520-6378(199608)21:4<252::AID-COL1>3.0.CO;2-P) for [Helmholtz-Kohlrausch effect](https://en.wikipedia.org/wiki/Helmholtz%E2%80%93Kohlrausch_effect) compensation.

## Look Presets
- Stay tuned ...
