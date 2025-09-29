# Release Notes

## OpenDRT v1.1.0b47

- Improve HDR/SDR behavior by using variations of the hyprbolic compression tonescale for different look modules.
- Bring back HDR Purity user control.
- Expose Display Grey Luminance as a user control. Since it was always set to 10 in all the presets it makes sense to put this in the hands of the user.
- Re-Expose HDR Grey Boost parameter... I guess this was useful for people.
- Refine Colorful preset - there was some halos around saturated light sources that was possible to improve.

## OpenDRT v1.1.0b45: Big rewrite after 44 beta versions of testing and refinements.

Generally, redesign many aspects to improve smoothness and rework some problematic and over-complicated design choices.

- Brilliance: Now split into pre-tonescale and post-tonescale brilliance adjustments. This improves smoothness and makes folding less likely than with the previous design.
- Purity Compression: Complete redesign. Remove second norm and tonescale previously used for purity compression control. Now use tonescale as a base purity compression factor and limit that in different ways. Add checkbox to completely disable purity compression if desired for some reason.
- Mid Purity: Simplify design overall design. Modify parameter space to have controls for intensity range and purity range (strength), instead of an ambiguous strength control.
- Hue Shift RGB: now using a separate hue extraction, so R is more oriented towards orange and B is more oriented towards Cyan. Expose range controls for these as well as it might be creatively desireable to have blue hueshift affect more of the intensity range for example.
- Look Presets: Refine all presets. Default preset is gone. Base preset is gone (moved to initial state of "StickShift Mode" for the tinkerers). New look presets: Arriba, Sylvan, Dystopic, Aery. See tooltip description for more information.
- Tonescale Presets: Misc tweaks and fixes to all tonescale presets. Lock Display Grey Luminance to 10 nits on all so that they are more easily comparable.
- Creative Whitepoint: Add cooler D75 and D93 creative whitepoints and integrate them into the DCI display encoding presets.
- Purity Compress Low: rename to Purity Softclip and expose CMY sliders for more control.
- Contrast Low: remove per-channel functionality. Location is now down in the same section as the rest of the tonescale functions and complexity is significantly reduced. Same look can more or less be achieved using mid purity low adjustments, and smoothness is improved. Tonescale is not completely independent from "color" adjustment. And at the same time intimately tied to the look, because a normal looking saturation presented through a high contrast tonescale might look way too saturated through a low contrast tonescale. Keep this in mind when building presets.
- Remove HDR Purity control. This was adding complexity to the algorithm, and the problem can be better solved by adjusting the purity compression behavior of the look.
- Hard-code HDR Grey Boost in presets mode. Was too confusing for the younglings. Still accessible in Stickshit mode.


## OpenDRT v1.1.0b1: Bring back surround compensation model from v0.1.3

- Move default tn_Lg (middle grey) value down to 10 nits. When tn_su is "dark", this value isn't changed. If tn_su is "dim" or "bright", middle grey is mapped higher accordingly with an unconstrained power function.

## OpenDRT v1.1.0b2: Add DCI display encoding presets - fixes #34

- DCI - 2.6 Power / P3-D60, DCI - 2.6 Power / P3-DCI, DCI - 2.6 Power / XYZ
- Rework creative white system to work with varying display technical whitepoints.

## OpenDRT v1.0.1

- **Fixes**
  - Increase Purity Compress Low strength for cyan and yellow. Some images had too much "gamut clipping" on the low end. This change should improve smoothness without sacrificing perceived saturation in a significant way.
- **New Features**
  - Add tonescale overlay visualization in the Resolve DCTL

## OpenDRT v1.0.0

OpenDRT v1.0.0 adds updates and new features with the goal of improving the default image rendering capabilities so that additional look operations upstream are not necessarily required. Significant rewrites and improvements have also been made to improve gradient smoothness and overall image appearance.

### New Features

- Improve **Tonescale**
  - Add **Midtone Contrast** to the tonescale functions. This operation allows creative control over "contrast" in the midtones and shadows, and enables opendrt to form a more finished image out of the box, if desired. It can be applied per-channel or in an RGB ratio preserving manner.
  - Add **High Contrast** to the tonescale functions. This operation allows creative control over the slope of the shoulder in the tonescale, allowing higher "highlight" contrast like ACES 1.x, or more "filmic" low-slope shoulder tonescale looks.
  - Add **Offset** control. It turns out that adding a small positive offset is a very important creative component of image appearance, and to omit this would be a mis-step.
  - Revise tonescale system math. 
    - Previously OpenDRT used a tonescale system similar to [the one Daniele Siragusano posted on acescentral](https://community.acescentral.com/t/output-transform-tone-scale/3498/224), but slightly modified to allow exact intersection constraints for middle grey and peak display. It accomplished this by applying the display linear output scale before the power function. The end result was pretty much identical due to the intersection constraints, but the downside was that it was difficult to access the 0-1 range pre-output y scale, which is necessary for many look operations like the high end purity compression. Basically you had to do all parts of the tonescale and then un-scale it for the purity compression and other operations. This always bothered me. 
    - For this new version I went back and figured out a new way to solve the constraints when applying output y scale after the power function. This model differs from Daniele's formulation. It prioritizes an exact solve for middle grey, and uses an approximate solve for peak display. Peak display intersection is much less critical to accurately map since small variations are not visible in the image and will suffer from lack of precision in the final integer display encoding. More details available here: https://www.desmos.com/calculator/1c4fhzy3bw
- Refine **Purity Compression**
  - Previously the purity compression behavior was tied to the "rendering space" weights. To allow more control, purity compression is now driven by a separate non-normalized weighted euclidean norm, which allows better creative control over the purity compression behavior per hue angle. These parameters are exposed as Purity Compression R G B controls. 
  - Purity Compression Range is the new name for the previously exposed Purity Compress Low slider. 
  - Add Purity HDR control. This allows creative control over the amount of purity compression as Peak Luminance is increased. At 0, the purity compression will not change as display peak luminance goes up. At 1, purity compression is reduced as peak luminance increases. The previous model for top end purity compression did not work well with the transition from SDR to HDR.
- Add **Mid Purity** adjustments
  - Mid-range purity turns out to be incredibly important for image formation, especially some amount of compression in purity at the top end in the cyan-yellow regions. This helps improve the horrible pasty pastel image appearance in image formation approaches like ACES 2, TCAM, and Arri Reveal. To this end I've added a look module to accomplish this as well as to _boost_ mid-range purity at the bottom end.
- Expose **Value** parameters. This module is a mix between a creative look adjustment and a necessary image rendering adjustment. Basically it scales down the vector, increasing with distance from achromatic. This operation reduces disruptions in gradients of narrow spectra lights sources, and can also be used creatively to achieve more "dense" or "filmic" color appearance.
- Add **Hue Shift** preferential look modification module. Older versions of OpenDRT had something similar, but it was limited to only adjusting the apparent hue of "highlights" affected by the top end purity copmression. This new module offers more flexibility, and is re-engineered to work better as a creative control. It affects more the hue angles near the primaries, and has a creative "range" parameter which allows control over the intensity range that is affected. For example if you boost "range r", reds in the shadows will shift more orange.
- Add **Hue Focus** preferential look modification module. This operation affects mid range purity and also hue angle. For example if Hue Focus Low R is increased, mid-range purity of reds is increased, and there is a hue distortion at the bottom end towards the red primary from both the yellow and magenta side. And conversely, if Hue Focus High R is decreased, mid-range purity at the top end is decreased, and the hue angles distort towards the yellow and magenta secondary. This module allows a creatively controllable way to dial in some of the nice look aspects of per-channel without being creatively shackled to the tonescale curve.
- Add **Creative White** adjustment. This sets the color of the peak luminance in the final image. D65 is the default, but the color can be made warmer all the way down to D50 to achieve a filmic look with warmer highlights. Additionally a **Creative White Range** slider was added to control how much to affect midtones and shadows. At 1.0, this operation is simply a CAT matrix to the desired whitepoint. At 0.0, it is mixed by the tonescale curve.
- Expose **Softclip** parameter, and allow it to be disabled. This is a final "gamut compress" style operation that improves smooth rendering of colorful gradients, though at the cost of a slight reduction in saturation at the gamut boundary.
- Add a selection of **Look Presets**
  - **Base**: Just the base image formation without any preferential hue distortion or contrast boost, though includes a base level of the "Value" adjustment to create smooth gradients. A good starting point for stronger more involved look development.
  - **Default**: Balanced, "neutral" image reproduction with natural colors and enough saturation and preferential hue distortions to create a nice looking picture, without being so strong of a look as to preclude it as a base for further look development.
  - **Filmish**: A very basic "film look", with stronger color crosstalk / preferential hue distortion, higher color contrast. Coule work well if a warmer D50 whitepoint were used as well.
- Add a selection of **Tonescale Presets**
  - High Contrast: The default setting. Enough contrast to maybe be called a "finished" image, but also could be a good base to build on.
  - Low Contrast: A low contrast starting point. Requires further contrast to be added in grading in order to achieve a "finished" image.
  - ACES 1.x: An emulation of the ACES 1.x tonescale curve. One deviation is mapping 0.0 to 0.0 through the tonescale curve, rather than mapping +0.02 to 0.0... because ain't nobody got time for that nonsense.
  - ACES 2.0: An exact match of the ACES 2.0 tonescale curve, in case you are a fan of a low contrast curve with extremely crushed shadows.
  - High Contrast 2: A more dark and "cinematic" high contrast tonescale curve. Maps middle grey to 6 nits in a 100 nit container for creative effect.
  - Low Contrast 2: A variation of Low Contrast which sets the overall slope a bit lower, but adds a positive offset and a bit more deep shadow contrast. A modern interpretion of the K1S1 legacy.


### Improvements

- Re-engineer mid-range purity low and high to be more robust.
- Re-engineer density method to have RGBCMY controls, and to avoid folding.
- Reduce density of blue. Combined with the new Hue Shift design, this improves presentation of saturated blue colors.

### Bug Fixes

- The Nuke implementation's HLG output had incorrect HDR scaling for peak luminances other than 1000 nits.


# DCTL Notes
Due to the limited nature of DCTL, I've made the choice to only expose the presets and not the full parameter space. For those of you who are more technically minded and interested in experimenting, you can access the full parameter set with the following steps:

1. Un-comment lines 66 to 128 below to expose the DCTL parameters.
2. Set the Look preset and Tonescale preset to "Custom (Check DCTL)"



## OpenDRT v1.0.0b45

- Add two new look presets: 
  - Colorful: A very saturated bright exhuberant look, maybe a good fit for animation.
  - Aery: A low contrast colorful look with strong preservation of color in highlights and strong mid-range purity reduction.
  - Umbra: A dark moody cinematic look with strong color crosstalk, natural blues, and a warm D50 whitepoint.
- Change Base preset to remove extra contrast and remove Brilliance module. Really just the base transform now.
- Add Hueshift RGB Range parameter instead of constant 0.5 value. Useful to control for some looks.
- Expand contrast low width parameter range maximum from 1 to 2 (useful for some looks where you want to bias this parameter to affect more the upper range)
- Change center of Hue extract Y so it affects more green, and can push farther without fucking up skin. This makes it more useful.
- Narrower RGB hue angles by default: from 0.8 to 0.6
- BrillianceLimit: bring back Br>1?(1-Ag):Ag on ts for brilliance increase.
- Change upper parameter range to 1 for Brilliance RGB. Probably a bad idea but might be useful for some looks.
- Bugfix: negative values were possible on output of MidPurity, which could cause artifacts.
- Bugfix: Nuke node's tonescale remove preset button was affecting look preset not tonescale preset.
- DCTL: Include Creative Whitepoint in look presets but allow override by including "Use Look Preset" option in dropdown.
- Add "Enable" to module enable switches to avoid duplicate labels.
- DCTL: Bugfix tooltips: some parameters had the same label which was causing tooltips to be repeated.


## OpenDRT v1.0.0b44

- Fix tooltip for Creative White Range - it was backwards.
- Improve Mid Purity
  - `Mid Purity High` is now significantly stronger and affects more of the purity range at the top end.
  - `Mid Purity High Strength` now only affects bottom of the intensity range.
- `Purity Range High` now only affects mid-range purity values if > 1.0, and only high-range purity values if < 1.0.
- Change default tonescale presets: boost toe from 0.001 to 0.003. This improves shadow contrast with the increased offset of 0.005.
- Refine Default preset. 
  - `Increase Render Space Blue Weight` from 0.4 to 0.5
  - `Purity Compress R` from 0.4 to 0.5
  - `Purity Compress G` from 1 to 2
  - `Purity Range Low` from 0.2 to 0.15
  - Reduce `Purity Range High` from 1.0 to 0.66
  - `Mid Purity Low` from 0.35 to 0.33
  - `Mid Purity High` from -0.8 to -0.66
  - `Mid Purity High Strength` from 0.66 to 0.3
  - `Brilliance G` from -0.35 to -0.4
  - `Brilliance B` from -0.1 to -0.2
  - `Brilliance M` from -0.15 to 0
  - `Brilliance Range` from 0.75 to 0.66


## OpenDRT v1.0.0b43

- Refine Parameters:
  - Remove most of Hue Contrast, only keep R
  - Remove Hue Shift RGB and CMY Ranges
  - Remove Purity Range High
  - Rename High Contrast to Contrast High
  - Rename Mid Contrast to Contrast Low
  - Rename "Softclip" to "Purity Compress Low". Still just a checkbox, as the parameters are tuned for common camera gamuts and probably not worth exposing to further confuse users.
  - Rename "Value" to "Brilliance" as this parameter adjusts the scale of the vector, and therefore both "saturation" and "value".
- Refine Default Preset: 
  - Refine tonescale: Reduce toe from 0.003 to 0.001, reduce contrast low width to 0.5 from 0.7, increase amount to 1.0 from 0.8. Remove Contrast High from default high contrast tonescale.
  - Reduce Mid Purity Low from 0.5 to 0.25 so that default preset is less over-saturated. Reduce Mid-Purity High a touch.
  - Reduce Purity Range Low from 0.3 to 0.2. It actually works pretty well keeping this lower and increasing purity compression where desired.
  - Tweak render space: drop strength from 0.35 to 0.25, slightly reduce blue weight from 0.5 to 0.45, and increase red weight from 0.2 to 0.25
  - Reduce Purity Range High from 1.0 to 0.8. It seems pretty safe to do this and keeps colorful highlights colorful while not introducing too much gradient disruptions.
  - Rebalance many other parameters for the new hue extraction method.
  - Add back Brilliance CMY. Chances are these can be left at 0 in most cases, but it could be helpful for some parameter combinations, and is relatively smooth if parameters are kept at reasonable values.
  - Boost HueShift parameter range from max value of 0.5 back to 1.0. Should probably not be pushed that far, but leaving the option there in case the user has poor taste.
- Re-write hue angle extraction method. Now using a simple gaussian window of cylindrical hue from opponent space. This significantly improves smoothness in Brilliance, Hue Shift and Hue Contrast.
  https://www.desmos.com/calculator/vhr9hstlyk
- Re-write what was previously called "Softclip":
  - Change math of "gamut compress" algorith to use a constrainted Softplus https://www.desmos.com/calculator/doipi4u0ce
  - Add rolloff to normalize in order to avoid extremely out of gamut values going to black
- Rename "Value" to Brilliance, probably a better name to describe what is being adjusted.
- Re-write Brilliance algorithm. Now significantly smoother and based on gaussian hue angles. Also includes soft plus rolloff to avoid negative multiply.
- Add tooltips to both nuke node and DCTL as a first step towards some documentation.
- DCTL: Add RedLog3G10 to input transfer functions


## OpenDRT v1.0.0b42

- Improve smoothness:
  - Add smoothing to tent window rgb / cmy hue extractions
  - Add smoothing at achromatic for min(r,g,b) "saturation"
  - HueShift RGB and CMY are now mixed by minrgb to smooth kink at achromatic
  - Mid purity now uses "chroma" extracted from simple opponent space to avoid mach bands and kinks.
  - Redesign Mid purity algorithm. Low and high use the same method now. Simpler and smoother. Uses simple cubic sigmoid scale: https://www.desmos.com/calculator/hzgib42en6
  - Refine soft clip to compress towards average instead of peak
- Remove some parameters
  - Mid purity high: only expose compression amount and strength
  - Value: remove CMY.. it's too dangerous. Even this approach is problematic but I don't have a better idea yet.
  - Purity Range High R is removed now and replaced with global Purity Range High. Probably this should be removed completely because it's kindof a bad idea, although it might be useful if combined with other more sophisticated methods of purity compression upstream. maybe I'll leave it in there for that reason.
- Expose "Render Space" parameters: strength and red/green weight. Might as well give control for these, though the user had better know what they are doing.
- Refine "Default" look preset
  - "High Contrast" tonescale preset: change contrast from 1.4 to 1.5, change offset to 0.005 from 0.002, change toe from 0.001 to 0.003 (helps a bit with deep shadows), add High Contrast reduction for smoother "highlight rolloff".
  - Refine "Low Contrast 2" tonescale preset
  - Add subtle CMY hue distortion in default preset
  - Refine purity compression, render space weights, and value parameters
  - Boost "Purity Range Low" from 0.25 to 0.3. This helps a bit with smoothness in high purity high intensity light sources
  - Set Hue Contrast blue low and high to 0, red low to 0.5
- Remove "Filmish" preset. The minimal look tools included are insufficient for this name.
- Add "Colorful" preset: a lower contrast high saturation look.
- Change "Base" preset to turn off "Value" adjustment as well as to use the Low-Contrast tonescale.


## OpenDRT v1.0.0b41

- Limit Purity High Range to only affect reds->Oranges, rename parameter to Purity Range High R
- Rebalance Default preset to improve rendering of saturated greens and blues
- Rebalance Filmish preset to be less stupid
- Fix behavior of Purity HDR slider. It was not scaling directly with Lp but scaling up then down because the lerp was not working as intended.
- Move Creative Whitepoint into stickshift version. want filmish to have D55 peak white.
- HueShiftRGB limit range to 0 to 0.5
- HueShiftCMY limit range to 0 to 0.5
- Value range -0.5 to 0
- Purity Range High R 0.5 to 1


## OpenDRT v1.0.0b40

- Refine Mid Purity High Compression algorithm to improve gradient smoothness through achromatic.
- Expose Mid Purity High Range parameter. This is fiddly and users might find this necessary to tweak. Reduce default value from 0.5 to 0.4
- Bring back Purity Range High parameter. It actually helps fire and sunsets quite significantly to not compress all the way to achromatic, keeping some color. Setting it to 0.8 by default (Purity Range Low and High are basically biases for where along the input intensity axis purity is compressed. See https://www.desmos.com/calculator/8ynarg1uxk)


## OpenDRT v1.0.0b39

- Rename "Hue Focus" to "Hue Contrast"
- Refine Hue Contrast algorithm 
  - Smoother behavior near peak achromatic
  - Add "Strength" control
  - Change parameter space so high contrast is positive numbers not negative. This probably improves user experience.
- Limit Mid Purity High Strength to 0.9 max
- Refine parameter names
- Improve code for enabling "stick shift" mode. 
  - Should be a bit easier to figure out now.
  - Disable presets parameters if in "stick shift" mode.


## OpenDRT v1.0.0b38

- Refine presets
- Change high contrast parameter space to be -1 to 1 


## OpenDRT v1.0.0b37

- Add creative whitepoint range slider to allow user control of whitepoint mapping over luminance range. For example to keep middle grey at D65 but push peak luminance to D50.
- Improve accuracy of "shoulder clip" solution in tonescale system. Now it doesn't shift as much with varying contrast values. https://www.desmos.com/calculator/1c4fhzy3bw
- Avoid invoking the spector of "density": change name to value.
- Double strength of mid range purity slider. I guess users should be responsible. I guess...
- Add mid range purity strength slider for more control. 
- Tweak render space weights again (push blue weight slightly)
- Tweak "Value" defaults to compensate for new render space weights
- Tweak presets to compensate
- Refine look presets vs tonescale presets. Look presets reset tonescale presets, but tonescale then overrides
- Port nuke prototype to DCTL (painful)


## OpenDRT v1.0.0b36

- Rewrite midrange purity... again. Reverting back to a simpler method, because the hue-dependent method from b33 and b34 introduced discontinuities in gradients through achromatic. 
  - midPurityLow now increases saturation limiting the amount by ~luminance weights of inverse rgb ratios, so that yellow saturatio nis increased less than red and blue. The target remains 1.0 in rgb ratios (will result in darker intensity when increasing saturation). The amount remains limited by distance from achromatic to avoid artifacts and discontinuities in pure stimuli.
  - midPurityHigh now desaturates mid-range purities in all hue angles. This actually looks better and avoids discontinuities along gradients through achromatic. Added a MaxRGBDivide on CMY / inverse rgb ratios, which helps. The strength is hard coded at min(r,g,b) squared, but an additional strength parameter was exposed which allows the intensity of the desaturation, and the range simultaneously to be adjusted.
- Remove some vendor speceific tonescale presets and add some more generic ones. 
- Remove colorful preset, opendrt is already really colorful it turns out. base, default, and filmish are maybe enough.
- Revert presets split. It was a bad idea. 


## OpenDRT v1.0.0b35

- Bugfix HueFocus:
  - The tonescale "range" factor was biased too much in highlights leading to artifacts. Changing to purity compress tonescale squared.
  - The huefocus "strength" factor was biased in the wrong direction (sqrt instead of squared), contributing to artifacts.
- Tonescale improvements
  - Add "High Contrast" module which allows the tonescale to match higher highlight saturation looks like ACES 1.x
  - Add "Shoulder clip" parameter. This controls the clipping point of the tonescale curve through display peak. Previously we omitted this with the rewrite in interest of simplicity so that scene-linear inf maps to 1.0, but this makes it difficult to match other tonescales and one could argue there is a small perceptual difference. We are not doing an exact constraint though this time around as that adds too much complexity. Instead it's an approximation, and then mapped to a 0-1 slider where 0 is clipping a lot and 1 is not clipping much. The behavior from sdr->hdr is better than an absolute mapping as well.
- Presets: split tonescale and "color" presets.
- Add a bunch of tonescale presets roughly matching a few common tonescale curves, for fun.


## OpenDRT v1.0.0b34

- bring back C and Y midrange purity high adjustments, and strength


## OpenDRT v1.0.0b33

- simplify midrange purity to two parameters, improve algorithm to be hue-dependent (high affects CMY, low affects RGB)
- midrange purity high now has stronger effect

## OpenDRT v1.0.0b32

- Redesign mid-range purity module. 
  - more complicated now with more sliders, but result is better I think. 
  - Controls for cyan and yellow high purity reduction (these are the two hue regions where this seems to need to happen).
  - Worried i'm going off the rails with all this and wondering if I should start stripping out stuff. Where is the line of "necessity" ...
- Rebalance weights and purity compression values to try to preserve yellows better
- Add saturation limit in per-channel midtone contrast in the blue region (was causing artifacts / too pure blue and discontinuities, this helps)


## OpenDRT v1.0.0b31

- the weighted yellow butt-cheeks norm is a bad idea. You can get pretty much the same result with a much simpler approach.
- I've been screwing around with midrange purity approaches all afternoon
- I should probably stop screwing around and release something at some point


## OpenDRT v1.0.0b30

- Exposing the "render space" as creative parameters was a bad idea so i've removed it
- I also figured out how to set the blue weight on the render space lower (now matching P3 luminance so it's just a properly weighted luminance adjustment): by using a different weighted norm for purity compression 😃
- This allows separate adjustment for the purity compression weights compared to the rest of the transform, which allows you to better creatively adjust the purity compression separate from the rest which is great
- i've also completely reworked the sdr->hdr purity compression setup so that it is less stupid. now it's a 0-1 slider called "purity hdr". if it's at 0, purity compression doesn't change from sdr -> hdr, and if it's at 1 you get more purity in hdr (though i've found that it's desireable to split the difference to preserve some gradients in as you go up in nits
- I also fixed the add preset button which was out of date


## OpenDRT v1.0.0b28

- Expose controls for the "Rendering space" (How "desaturated" we are from P3, with custom weights.)

I think I have a much better solution for the blues now. I've decided to expose the controls for the "rendering space" since it does allow some interesting creative options. I've exposed the controls on the purity tab and called the main control "color contrast" - though it could probably be called "saturation" since boosting it increases colorfulness (and introduces top end display cube escapes which are then brought back in control by the density parameters)...

And I've significantly reduced the "weight B", which was previously quite high - this had nice appearance in blue lights but was causing pretty significant out of gamut issues at the bottom end which is what you were picking up on in that frame with the blue light on the carnival ride (thank you for spotting this and questioning it) .. i think where it is not is much improved, and the complexity is not increased.

I also decided to add purity compress controls for R G and B - it's like a multiply on top of the "global" purity compress controls - and i think it would be another useful parameter to adjust. If you wanted to boost B density, this might not be necessary anymore as you can instead tweak the purity compression for that region and probably get something that is better.
Actually, reducing B weight also changes the luminance of yellow which is not great... so i brought back the CMY density weights so its possible to compensate, and reworked the presets to use both approaches.


## OpenDRT v1.0.0b26

- Added two buttons for saving and deleting presets.
- Also changed quite a few knob names so they are more consistent as I work on the DCTL
- Also changed the density method so that positive density values will switch to reducing by the inverse tonescale instead of the forward tonescale, so that mid-range will be boosted more than high range values rather than the opposite. Positive Density values are probably a bad idea though.


## OpenDRT v1.0.0b13

First version I would consider a beta release after about 100 iterations of improvements from 0.3.5.
First draft of look modules added, midrange purity added, reworked density, hueshift. Reworked tonescale system, with offset and mid contrast.



