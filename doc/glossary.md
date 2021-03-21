# Glossary of Terms

Here I will define a glossary of terms which I will use in this documentation.

- **Display Transform** - A transform which applies aesthetic and colorimetric transformations to an image in order to prepare it for being properly displayed on a device such as a monitor or television. Also sometimes called a Display Rendering Transform or DRT (from Filmlight), an Output Transform (ACES) or a View Transform.
- **Chromaticity** - A specific color coordinate usually defined as a cartesian x,y coordinate in some chromaticity space such as CIE 1931 xy, or CIE 1976 u'v'. 
- **Achromatic** - A value lacking chroma: Neutral, grey, black and white. A value where the RGB components are equal to each other. Achromatic values form an axis between 0 and 1 in a display-referred colorspace.
- **Display Device** - A device which displays an image such as a CRT monitor, an OLED Television, an LCD computer monitor, or an LED wall.
- **Tonescale** - A term from the ACES Output Transform which refers to the compression of image intensity from a high dynamic range to a lower dynamic range. For example a scene might have a range of 0.01 to 100,000 nits. When representing such an image on a display, we are limited to a much smaller dynamic range, around 0.002 to 100 nits for an SDR display for example.
- **Nit** - A unit of measure for light intensity. Equal to 1 Candela per Meter Squared. 
- **Scene-Referred** - Also called "Scene-Linear" - an image encoding in which pixel values have an intensity that is [proportional](https://en.wikipedia.org/wiki/Proportionality_(mathematics)) to scene light intensity.
- **Display-Referred** - An image encoding in which pixel values have been modified and compressed in a nonlinear fashion to look good on a display device.
- **Code Value** - A term used to refer to a single step in the integer encoding of a display-referred images. For example, an 8 bit integer h264 video has 256 total code values to represent image information.
- **Inverse EOTF** - Also known as simply **EOTF**, this term refers to the Electro-Optical Transfer Function of a display device. Technically, the EOTF is the nonlinear curve that the display device applies to the code values before emitting the light from the screen. Therefore, the inverse of this curve must be applied to the image before sending the image "across the wire" to the display device, so that the image looks correct.
- **Middle Grey** - Often used for image calibration, the term middle grey refers to an idealized surface with 18% diffuse reflectance. Middle Grey is usually mapped to a value of around 0.18 in a scene-linear encoding. By convention, middle grey is usually mapped to around 0.10 in display-linear after the display transform has been applied, but before the inverse EOTF.

