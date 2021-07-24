# Glossary of Terms

Here I will define a glossary of terms which I will use in this documentation.

- **Display Transform** - A transform which applies aesthetic and colorimetric transformations to an image in order to prepare it for being properly displayed in a specific viewing condition, for example on an television in a dark room, or in a DCI calibrated projector in a theater. Also sometimes called a Display Rendering Transform or DRT (from Filmlight), an Output Transform (ACES) or more generally a View Transform.
- **Scene-Referred** - Image data having a precisely known mathematical relationship between light in a scene and image pixel values. See [this tweet](https://twitter.com/momaku/status/812025645626703874) from [Charles Poynton](https://www.poynton.ca) for more precision!
- **Display-Referred** - Image data having a precisely known mathematical relationship between image code values and light emitted from a display device.
- **Scene-Linear** - A specific form of scene-referred imagery in which pixel values have an intensity that is [proportional](https://en.wikipedia.org/wiki/Proportionality_(mathematics)) to scene light intensity.
- **Chromaticity** - A specific color coordinate usually defined as a cartesian x,y coordinate in some chromaticity space such as CIE 1931 xy, or CIE 1976 u'v'.
- **Achromatic Axis** - In a 3-dimensional RGB coordinate system, the achromatic axis is formed along the line where the individual color components are equal to each other. That is, where R=G=B. In a scene-referred colorspace, the achromatic axis can be of infinite length. In a display-referred colorspace, the achromatic axis is the diagonal line between the origin and the white corner of the display gamut cube.
- **Display Device** - A device which displays an image such as a CRT monitor, an OLED Television, an LCD computer monitor, or an LED wall.
- **Nit** - A unit of measure for light intensity. Equal to 1 Candela per Meter Squared. 
- **Tonescale** - A term from the ACES Output Transform which refers to the compression of image intensity from a high dynamic range to a lower dynamic range. For example a scene might have a range of 0.01 to 100,000 nits. When representing such an image on a display, we are limited to a much smaller dynamic range, maybe around 0.02 to 100 nits for an SDR display for example.
- **Code Value** - A term used to refer to a single step in the integer encoding of a display-referred images. For example, an 8 bit integer h264 video has 256 total code values to represent image information.
- **Inverse EOTF** - Also known as simply **EOTF**, this term refers to the Electro-Optical Transfer Function of a display device. Technically, the EOTF is the nonlinear curve that the display device applies to the code values before emitting the light from the screen. Therefore, the inverse of this curve must be applied to the image before sending the image "across the wire" to the display device, so that the image looks correct.
- **Middle Grey** - Refers to an idealized surface with 18% diffuse reflectance. "Grey cards" are often used for calibrating white balance and exposure. Middle Grey is usually mapped to 0.18 in scene-linear. By convention, middle grey is usually mapped to around 0.10 in display-linear, although this can vary.

