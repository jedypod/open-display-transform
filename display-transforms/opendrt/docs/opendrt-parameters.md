## Modules Overview

OpenDRT's functionality is organized into the following modules:

* **Tonescale:** Parameters related to the tonescale, which allows the user to control things like overall contrast, "highlight" and "shadow" "rolloff", and overall exposure through placement of middle grey, as well as HDR-specific controls for peak display luminance.
* **Purity:** Parameters related to adjusting overall colorfullness over the intensity range of the formed picture.
* **Brilliance:** Parameters for adjusting the luminance of more colorful stimuli. This can compensate for clipping and smoothness issues with narrow spectra light sources, as well as creative adjustments to what is sometimes erroneously referred to as "density".
* **Hue Shift:** Parameters for modifying hue angles over the luminance range. Very important for preferred stimuli reproduction, and to avoid perceived hue shifts due to the Abney Effect for example.


## Technical Documentation

### Input Parameters

* **Input Gamut (`in_gamut`):** Specifies the color space primaries of the input image data.
    * *Options:* XYZ, ACES 2065-1 (AP0), ACEScg (AP1), P3-D65, Rec.2020, Rec.709, Arri Wide Gamut 3/4, Red Wide Gamut RGB, Sony SGamut3/SGamut3Cine, Panasonic V-Gamut, Blackmagic Wide Gamut, Filmlight E-Gamut/E-Gamut2, DaVinci Wide Gamut.
* **Input Transfer Function (`in_oetf`):** Specifies the transfer function (log curve) of the input image data.
    * *Options:* Linear, Davinci Intermediate, Filmlight T-Log, ACEScct, Arri LogC3/LogC4, RedLog3G10, Panasonic V-Log, Sony S-Log3, Fuji F-Log2.

### Tonescale Parameters 
([Desmos Plot of base tonescale model](https://www.desmos.com/calculator/aiicar4tjh))

* **Display Peak Luminance (`tn_Lp`):** Peak display luminance in nits. In SDR, the max value stays pinned at 1.0. In HDR, the max value is adjusted to match peak luminance in the HDR container.
* **HDR Grey Boost (`tn_gb`):** Amount of stops to boost Grey Luminance, per stop of exposure increase of Peak Luminance. For example, if HDR Grey Boost is 0.1, middle grey will be boosted by 0.1 stops per stop of Peak Luminance increase.
* **HDR Purity (`pt_hdr`):** How much to affect purity compression as Peak Luminance increases. A value of 0.0 will keep the purity compression behavior exactly the same for SDR and HDR. A value of 1.0 will preserve more purity as peak luminance increases (at the risk of gradient disruptions in high purity high intensity light sources).
* **Grey Luminance (`tn_Lg`):** Display luminance for middle grey (0.18) in nits. Sets the target value for middle grey within the available luminance range of the display device.
* **Contrast (`tn_con`):** Adjusts contrast or slope. A constrained power function applied in display linear.
* **Shoulder Clip (`tn_sh`):** Unitless control for the scene-linear value at which the tonescale system crosses the peak display linear value (1.0) and clips. This is not an exact constraint in order to keep the system simple, but corresponds to roughly 16 at Shoulder Clip = 0 and 1024 at Shoulder Clip = 1
* **Toe (`tn_toe`):** Quadratic toe compression. Strongly compresses deep shadows. Helpful to have some amount to smooth the transition into display minimum. Higher values with a strong positive Offset also valid. Similar to common camera DRT tonescale strategies. ([Desmos Function](https://www.desmos.com/calculator/skk8ahmnws)).
* **Offset (`tn_off`):** Pre-tonescale scene-linear offset. If 0.0, scene-linear 0.0 maps to display-linear 0.0 through the tonescale system. Many camera imaging pipelines apply a negative offset to set the average of shadow grain at 0.0. A positive Offset can be desireable to compensate for this and increase detail in shadows, in addition to being aesthetically desireable. Offset should NOT be a negative number (Looking at you ACES 1.x)
* **Enable Contrast High (`tn_hcon_enable`):** Contrast High allows control of the upper section of the tonescale function. Off by default, but can be useful if a stronger highlight contrast, or a softer highlight rolloff behavior is desired. ([Desmos Function](https://www.desmos.com/calculator/etjgwyrgad)).
* **Contrast High (`tn_hcon`):** Amount adjust highlights. Positive values increase highlight exposure, negative values decrease. 0 has no effect.
* **Contrast High Pivot (`tn_hcon_pv`):** Amount of stops above middle grey (0.18) to start the adjustment.
* **Contrast High Strength (`tn_hcon_st`):** How quickly above the Contrast High Pivot the effect begins.
* **Enable Contrast Low (`tn_lcon_enable`):** Contrast Low adds contrast to the midtones and shadows. Middle grey (0.18) is un-changed through the adjustment. ([Desmos Function](https://www.desmos.com/calculator/blyvi8t2b2)).
* **Contrast Low (`tn_lcon`):** Amount of contrast to add. 0.0 has no effect. 1.0 will expose down by 1 stop at the origin (0,0)
* **Contrast Low Width (`tn_lcon_w`):** The width of the adjustment. Width below 0.5 will mostly affect values between 0 and middle grey. Values above 0.5 will increasingly start to increase highlight contrast, which could be desired or not depending on what you are trying to do.
* **Contrast Low Per-Channel (`tn_lcon_pc`):** How much to apply Contrast Low using a per-channel method, which can introduce pleasing mid-range purity boosts and hue distortions. A value of 0.0 will preserve purity and hue angle. A value of 1.0 will use a per-channel method in low and mid purities. At high purities, purity is always preserved to avoid artifacts.

### Creative White Parameters

* **Creative White (`cwp`):** Set the creative whitepoint of the display peak luminance. With D65 all channels are equal. With D50, the peak luminance value will match a D50 whitepoint. This can be creatively desireable. This adjustment is applied post-tonescale.
* **Creative White Range (`cwp_rng`):** The intensity range affected by the Creative White adjustment. At 1.0, the entire intensity range is affected. As Range is decreased, more of midtones and shadows are left unaffected. It can be creatively desireable to keep midtones more neutral while shifting highlights warmer.

### Purity Parameters

* **Render Space Strength (`rs_sa`):** Render space is the encoding in which the RGB Ratios are taken. Strength controls how much to desaturate from P3 gamut. Creatively, the more you desaturate, the more brilliance is increased in the resulting image. To be used with caution as this affects every other aspect of the image rendering.
* **Render Space Red Weight (`rs_rw`):** The Red weight of the Render Space Strength. Modify with caution as this affects every other part of the image rendering.
* **Render Space Blue Weight (`rs_bw`):** The Blue weight of the Render Space Strength. Modify with caution as this affects every other part of the image rendering.
* **Purity Compress R (`pt_r`):** Adjust the amount of purity compression as intensity increases for Reds, Oranges and Magentas. A value of 0.0 will result in no purity compression and discontinuities in gradients in high purity high intensity light sources. A higher value will compress purity more as intensity increases.
* **Purity Compress G (`pt_g`):** Adjust the amount of purity compression as intensity increases for Greens, Yellows and Cyans. A value of 0.0 will result in no purity compression and discontinuities in gradients in high purity high intensity light sources. A higher value will compress purity more as intensity increases.
* **Purity Compress B (`pt_b`):** Adjust the amount of purity compression as intensity increases for Blue. A value of 0.0 will result in no purity compression and discontinuities in gradients in high purity high intensity light sources. A higher value will compress purity more as intensity increases.
* **Purity Range Low (`pt_rng_low`):** Where over the intensity range the purity compression starts. Higher values will compress purity more for low intensity. For example a Purity Range Low value of 0.5 will result in desaturated looking midtones.
* **Purity Range High (`pt_rng_high`):** Where over the intensity range the purity compression ends. Lower values will limit how much purity will be compressed at high intensities. For example a Purity Range High value of 0.5 will result in highly saturated looking highlights, at the risk of gradient discontinuities.
* **Enable Purity Compress Low (`ptl_enable`):** Purity Compress Low increases tonality and smoothness in extremely pure input values that can not be adequately compressed into the display-referred gamut volume. The algorithm is tuned for common camera observer colorimetry sources. To keep the interface simple, this algorithm is exposed only as a boolean checkbox.
* **Enable Mid Purity (`ptm_enable`):** The Mid Purity module adjusts mid-range purity of midtones and highlights. Without this module enabled, it is likely that midtones will not appear colorful enough, and midtones and highlights will appear too colorful resulting in chaulky pasty looking images especially in yellows and cyans.
* **Mid Purity Low (`ptm_low`):** Amount to increase purity of midtones and shadows in mid-range purity areas. A value of 0.0 will have no effect. A value of 1.0 is the maximum possible value while preserving smoothness.
* **Mid Purity Low Strength (`ptm_low_st`):** The strength of the Mid Purity Low adjustment. Higher values affect more of the purity range.
* **Mid Purity High (`ptm_high`):** Amount to decrease purity of upper midtones and highlights in mid-range purity areas. A value of 0.0 will have no effect. A value of 1.0 is the maximum possible value while preserving smoothness.
* **Mid Purity High Strength (`ptm_high_st`):** The strength of the Mid Purity High adjustment. Higher values affect more of the purity range.

### Brilliance Parameters

* **Enable Brilliance (`brl_enable`):** Brilliance scales the intensity of more pure stimuli. With the OpenDRT algorithm it is possible to get high intensity high purity values going out of the top of the display-referred gamut volume, which can cause discontinuities in gradients. The Brilliance module exists compensate for this, and to add some darkening to more pure stimuli, which can be creatively desireable (sometimes incorrectly referred to as 'density').
* **Brilliance R/G/B/C/M/Y (`brl_r`, `brl_g`, `brl_b`, `brl_c`, `brl_m`, `brl_y`):** Scale factors for the intensity of high-purity colors along the six primary/secondary hue axes. Negative values darken, positive values brighten.
* **Brilliance Range (`brl_rng`):** As Brilliance Range is increased, the brilliance adjustments affect more the low intensity values of the image data.

### Hue Shift Parameters

* **Enable Hueshift RGB (`hs_rgb_enable`):** Hue Shift RGB adds hue distortion to the red green and blue primary hue angles as intensity increases. By default OpenDRT will compress purity in a straight line in RGB/Chromaticity space. This can lead to perceived hue shifts due to the Abney Effect, for example a pure blue will perceptually shift towards purple as it desaturates. To compensate for this, and to use as a creative tool, this module allows creative control over the path that red green and blue hue angles take as their purity is compressed.
* **Hueshift R (`hs_r`):** Amount to distort Red towards Yellow as intensity increases.
* **Hueshift G (`hs_g`):** Amount to distort Green towards Yellow as intensity increases.
* **Hueshift B (`hs_b`):** Amount to distort Blue towards Cyan as intensity increases.
* **Hueshift RGB Range (`hs_rgb_rng`):** Amount of intensity range to affect with HueShift RGB.
* **Enable Hueshift CMY (`hs_cmy_enable`):** Hue Shift CMY adds hue distortion to the cyan magenta and yellow secondary hue angles as intensity **decreases**. This module allows some very minimal adjustments of secondary hue angles as a creative tool.
* **Hueshift C (`hs_c`):** Amount to distort Cyan towards Blue as intensity decreases.
* **Hueshift M (`hs_m`):** Amount to distort Magenta towards Blue as intensity decreases.
* **Hueshift Y (`hs_y`):** Amount to distort Yellow towards Red as intensity decreases.
* **Enable Hue Contrast (`hc_enable`):** Hue Contrast compresses hue angle towards the primary at the bottom end and expands the hue angle towards the secondary as intensity increases. It also increases purity as it compresses, and decreases purity as it expands. This leads to a nice creatively controllable simulation of this effect from per-channel tonescales. For OpenDRT we only keep the red hue angle control since it is the most useful.
* **Hue Contrast R (`hc_r`):** Amount to increase Hue Contrast at the red hue angle.

### Output Parameters

* **Display Encoding Preset (`display_encoding_preset` / `display_presets`):** Selects a predefined combination of display gamut, inverse EOTF, and peak luminance.
    * Rec.1886 (2.4 Power / Rec.709)
    * sRGB Display (2.2 Power / Rec.709)
    * Display P3 (2.2 Power / P3-D65)
    * Rec.2100 PQ (PQ / Rec.2020 P3-Limited)
    * Rec.2100 HLG (HLG / Rec.2020 P3-Limited)
    * Dolby PQ (PQ / P3-D65)

* **Clamp (`_clamp` / `clamp`):** If enabled, clamps the final RGB values to the range \[0, 1].

### Included Presets

OpenDRT comes with several built-in presets for both the overall look and the tonescale component specifically.

#### Look Presets (`look_preset`)

These presets adjust all parameters to achieve a specific aesthetic style.

* **Default:** An picture formation that includes minimal adjustments for an aesthetically pleasing image. Might be a good starting point.
* **Colorful:** A saturated, bright, exuberant look. Potentially a good fit for animation or stylized content.
* **Umbra:** A dark, moody, cinematic look featuring low shadow contrast, strong color crosstalk, natural blues, and a warm D50 whitepoint.
* **Base:** Includes only the essential base components of the OpenDRT image rendering with practically no preferential adjustments. Purity compression is RGB-ratio-preserving or "chromaticity-linear" and minimal, meaning bright saturated highlights will clip. Mid-range purity is strong. This is intended as a starting point for users who want absolute control for further look development, not as a pleasing picture formation.

#### Tonescale Presets (`tonescale_preset`)

These presets specifically adjust the parameters related to the tonescale module, allowing you to mix and match tonescales with different color rendering settings.

* **High-Contrast:** The default tonescale curve used in the "Default" look. Provides enough contrast to potentially be considered a finished image, but can also serve as a solid base for further grading.
* **Low-Contrast:** A low-contrast tonescale curve intended as a starting point for grading where additional contrast will be added later.
* **ACES-1.x:** A rough match to the ACES 1.x tonescale curve. Note: Unlike the original ACES 1.x, this maps scene 0.0 to display 0.0.
* **ACES-2.0:** An exact match to the ACES 2.0 tonescale function. Features very low contrast in highlights and strong shadow toe compression, while mapping scene 0.0 to display 0.0. Use with caution if adding upstream shadow contrast without a positive offset to compensate.
* **Marvelous Tonescape:** A dark, contrasty, "cinematic" tonescale curve. Maps middle grey to 6 nits in SDR instead of the more typical 11.1 nits.
* **Arriba Tonecall:** A low-contrast tonescale with a shadow handling approach typical of camera DRTs, featuring a large positive offset combined with strong shadow toe compression.
* **DaGrinchi Tonegroan:** Another low-contrast tonescale designed as a starting point for further manipulation. Kindof lame, probably use other options.
* **Aery Tonescale:** An "aery" tonescale function.
* **Umbra Tonescale:** Another dark, contrasty, "cinematic" tonescale curve. This is the tonescale function used in the "Umbra" look preset.

### Presets Management (Nuke Node)

The Nuke node provides some helpful functions to create and manage presets, for use in your own look development process:

* **Look Presets / Tonescale Presets Dropdowns:** Select from the built-in presets described above, or any presets you have created yourself. This is implemented as a command menu, so it interactively changes all of the knob values (parameters) specified in the preset.
* **Add Preset:** Saves the current settings as a new preset with the name you specify.
* **Remove Preset:** Deletes the selected preset.
* **Show DCTL:** Generates DCTL code corresponding to the current Nuke node settings. This can be useful to port a preset you create over to the DCTL code for use in Resolve.

### Stickshift Mode (DCTL Only)

The `OpenDRT.dctl` file contains commented-out `DEFINE_UI_PARAMS` lines (around line 49-101). By uncommenting these lines and commenting out the preset parameter lines (around 108-115), users can gain direct access to *all* underlying parameters within DaVinci Resolve, bypassing the preset system. This is intended for advanced users who want full control for custom look development directly in Resolve. The Nuke node always exposes all parameters.
