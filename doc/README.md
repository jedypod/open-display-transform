# Technical Approach

## Tonescale

Tonescale is an ACES term which refers to the process of mapping a large range of intensity values down into a lower range. Essentially it is a tonemapping operation. Most commonly this transform uses a log encoding of the scene-linear image data, and then applies some type of [sigmoidal](https://en.wikipedia.org/wiki/Sigmoid_function) s-curve. These curves usually have a linear section around middle grey, and a nonlinear section in the toe and shoulder regions of the curve, which compress shadows and highlights.

Many image makers are familiar with the process of increasing contrast in an image. When we gamma down an image we simultaneously increase contrast and saturation. When we apply an S-curve to an image, the highlights get desaturated, and the midtones and shadows get more saturated. This is because of how the nonlinear transformation affects the individual R, G, B channels. 

Many image makers have an intuitive understanding of what is happening but are unaware of the technical details. I will try to break this down and explain it here.

To explain this concept I will use this test image. 

![hueswatches](./img/hueswatches.jpg)

This image contains a set of 24 hue swatches. These hue swatches are **not** perceptual, they are purely RGB values. Each hue swatch varies linearly in luminance from 0 on the left to 1 on the right. Saturation or chroma varies linearly from full chroma (at the RGB gamut boundary) (1) at the bottom to achromatic (0) at the top. 

The 1st column contains primary colors: Red green and blue. Columns 2-4 are 3 equally spaced samples between the primary colors and the secondary colors. The 5th column are the secondary colors (cyan, magenta, and yellow). And the last 3 columns are another 3 samples between the secondary colors and the primary colors. In short: 24 equally spaced chromaticity-linear lines rotating around the achromatic axis. 

Viewed on a CIE 1931 xy chromaticity diagram, and assuming an input RGB gamut of Rec.2020, the image plot looks like this.	

<img src="./img/plot_hueswatches_1931.png" alt="plot_hueswatches_1931"  />

First we need to expose up out input image in order to get a larger scene-like range of luminance information. We will expose it up by 6 stops. This puts our 1.0 max luminance at a new value of 64. Plenty of range for compressing down!

If we take some log+s-curve tonemapping transform, and apply it directly to this exposed up image, we get something that looks like this.

![plot_hueswatches-per-channel](./img/plot_hueswatches-per-channel.jpg)

On first glance it looks pretty reasonable. Filmic, almost! Not bad, but let's take a closer look. To take a closer look we are going to plot the image data directly in a 3 dimensional coordinate system. 

We can do this in Nuke using a PositionToPoints node, or by using the included PlotRGBCube gizmo. Here we can see the 0-1 display-referred luminance range of each of the primary hue directions: Green forming the up (Y) axis, and Red and Blue forming the other two horizontal (X and Z) axes. If you look closely you will notice that an achromatic triplet of (0, 0, 0) is at the origin, and an achromatic triplet of (1, 1, 1) is at the 3D position (1, 1, 1). 

![RGBCube_horizontal](./img/RGBCube_horizontal.png)

If we rotate this cube 45 degrees on the Z axis and `-degrees(atan(sqrt(0.5))) ` on the X axis, we can orient the cube such that the achromatic axis is aligned to the vertical Y axis. This is useful for visualization.

![RGBCube_achromatic_up](./img/RGBCube_achromatic_up.png)

Here we visualize the above per-channel tonemapped image of the hue swatches, looking directly down the achromatic axis from the top through an orthographic camera. 

![plot_hueswatches-per-channel_top](./img/plot_hueswatches-per-channel_top.jpg)

Note how the primary and secondary colors maintain their "chromaticity linearity" (the straight line stays straight through the tonemapping transformation), while hues in between the primary and secondary hues collapse towards the secondaries. For example, values between pure blue and pure magenta collapse towards magenta at an alarming rate.

Fun fact, if you look closely close to the achromatic axis, you can see values collapsing towards the primary colors where shadows are being compressed.

Here is the same plot of the RGB cube but viewed from a three-quarter angle.

![plot_hueswatches-per-channel_persp](./img/plot_hueswatches-per-channel_persp.jpg)

Here you can clearly see values between green and yellow collapsing towards yellow, and values between red and yellow collapsing towards yellow.

Let's try a chromaticity-preserving approach. This is simple to do. We can take our input RGB, take a [norm](https://en.wikipedia.org/wiki/Norm_(mathematics)) of that vector, like max(R,G,B), apply the compression to the norm, divide the compressed norm by the original norm. This results in a compression factor. We can then multiply our compression factor into our RGB, and we get a chromaticity preserving adjustment of pixel intensity.

![chromaticity_preserving_nuke_script](./img/chromaticity_preserving_nuke_script.png)

Looking at our image we get this:

![plot_hueswatches-chromaticity-preserving](./img/plot_hueswatches-chromaticity-preserving.jpg)

Let us take a moment and compare this with the per-channel approach. Remember the tonemapping operation is exactly the same.

![plot_hueswatches-per-channel](./img/plot_hueswatches-per-channel.jpg)

Obviously there is a huge amount more saturation preserved. But remember this is an image with a max value of 64 in scene linear, so it is very bright. The behavior of the per-channel approach is closer to what we desire here, at least for it's apparent desaturation of very bright highlights. Highlights converging to achromatic with increasing exposure. This behavior is not apparent at all in the chromaticity-preserving approach, and is thus something we will have to engineer. The per-channel approach is not all perfect though. If you look closely you can see significant nonlinearities in hue as brightness increases from left to right. For example, if you look at swatch Col 2, Row 2, you can see the warm green skewing significantly towards yellow. In Col 8, Row 3, the bluish color skews significantly towards magenta. And finally in Col 8, Row 2, you can see the orange color skewing significantly towards yellow.

Anyway enough rambling, let's look at the plots of the chromaticity preserving approach!

![plot_hueswatches-chromaticity-preserving_top](./img/plot_hueswatches-chromaticity-preserving_top.jpg)

As promised, using a chromaticity preserving tonemapping approach, straight lines stay straight and evenly spaced. ![plot_hueswatches-chromaticity-preserving_persp](./img/plot_hueswatches-chromaticity-preserving_persp.jpg)

Even when viewed from the side. If our goal is to engineer the behavior that we desire, this is a much better starting point. The per-channel approach has some of the right behaviors, and also some undesired behaviors that would be very difficult to undo. This is why I have chosen a chromaticity preserving approach as the basis for this transform, given the design goals laid out above.

The Nuke script that was used to generate these plot images is available here if you wish to view it in more detail: [plot_hueswatches-chromaticity-preserving_vs_per-channel.nk](./img/plot_hueswatches-chromaticity-preserving_vs_per-channel.nk) 

# RGB Ratios Model

The model  I'm using is based on the concept of splitting RGB into a norm that represents the achromatic axis, or the neutral values, and RGB ratios that represent the color information. Operating independently on color and luminance is valuable because it lets us control chroma, hue and luminance separately. 

Let's put some pictures to these ideas. Here again are our set of 24 hue swatches.

![HueSwatches24_01_rgb](./img/HueSwatches24_01_rgb.png)

If we take the `max(r,g,b)` norm of these rgb values, we get a representation of the achromatic axis. This shows us luminance separated from color.

![HueSwatches24_02_maxrgb](./img/HueSwatches24_02_maxrgb.png)

Using the norm we can extract the inverse rgb ratios. There are a couple of different ways to do this: 

```
norm = max(r, max(g, b))

# option 1: calculate inverse rgb ratios directly
inverse_rgb_rats = (norm - rgb) / norm

# option 2: calculate rgb ratios
rgb_rats = rgb / norm
inverse_rgb_rats = 1.0 - rgb_rats
```

Inverse rgb ratios represent the achromatic value at 0.0, and represent increasing chroma in the complementary hue directions (essentially cyan, magenta, yellow saturation). A inverse rgb ratio of 1.0 is at the RGB gamut prism boundary. We exploited this facet of this model for the gamut mapping algorithm.

![HueSwatches24_03_inverse_rgb_ratios](./img/HueSwatches24_03_inverse_rgb_ratios.png)

If you take the `max(r,g,b)` of the inverse RGB ratios you get a hexagonal representation of chroma. Interestingly this is identical to `max(r,g,b) - min(r,g,b)` which is identical to S in hexagonal HSV.

![HueSwatches24_04_hexagonal_saturation](./img/HueSwatches24_04_hexagonal_saturation.png)

Instead of taking the `max(r,g,b)` if we weight the inverse rgb ratios by the luminance weights for the rendering gamut, we get a weighted representation of the chroma. This is useful because it is desireable in a display rendering transform to control the behavior of different hue regions according to this perceptual  facet. For example, yellow and green should desaturate more quickly than blues and reds. Similarly blues and reds should appear darker at lower luminance levels, and brighter at higher luminance levels to maintain a natural appearance, at least with the subjective testing that I have done.

![HueSwatches24_05_inverse_rgb_ratios_luminance_weights](./img/HueSwatches24_05_inverse_rgb_ratios_luminance_weights.png)

"Forward" rgb ratios are also useful. They look like this. Instead of the achromatic axis being at 0.0, it is at 1.0. This means we can multiply these values to get a "more intense" color in certain regions. I'm not sure how to describe this properly, but it seems like an important facet of this model to achieve vibrant color.

![HueSwatches24_07_rgb_ratios](./img/HueSwatches24_07_rgb_ratios.png)

# Engineering a Path to White

Here is one method to engineer a path to white for high intensity input colors. This time we'll remove the chroma ramp, and keep fully saturated color from top to bottom.

![HueSwatches24_demo_01](./img/HueSwatches24_demo_01.png)

And then we will expose up our image to get some insanely bright insanely saturated input colors to test. (Shown here with a simple gamma 2.2 transform - note the collapse towards the secondary colors: cyan magenta and yellow!)

![HueSwatches24_demo_02](./img/HueSwatches24_demo_02.png)

We'll take the norm using our max(r,g,b) method (note that this image has the intensity compression curve - the Tonescale already applied for display purposes).

![HueSwatches24_demo_03](./img/HueSwatches24_demo_03.png)

From the max(r,g,b) norm, we can calculate the inverse rgb ratios.

![HueSwatches24_demo_04](./img/HueSwatches24_demo_04.png)

And the luminance weights

![HueSwatches24_demo_05](./img/HueSwatches24_demo_05.png)

We can bias our compressed norm with something like a power function. This specifies how much of the highlight region we want to affect with our path to white.

![HueSwatches24_demo_07](./img/HueSwatches24_demo_07.png)

We can then use the luminance weights and the path to white factor, and combine the two, but only in the upper regions of the luminance range.



# Perceptual Model

When a path to white is taken that goes directly from the chromaticity towards the achromatic axis in a linear line, shifts in the perceived hue can occur because of the [Abney effect](https://en.wikipedia.org/wiki/Abney_effect).To compensate for this we can use a perceptual model to alter the path that the hue takes. Our model will no longer be chromaticity preserving, but it is a subtle change and looks a lot better, especially for saturated blue colors, and reddish orange hues.

I am using the excellent and extremely simple [oklab colorspace](https://bottosson.github.io/posts/oklab/) from [Bjorn Ottosson](https://bottosson.github.io). I am only using it to compensate for the path to white, not for the gamut compression, as it seems to behave a bit strangely for hues that are outside of the spectral locus. (Not surprising). Basically what I do is convert source and destination rgb ratios to oklab LCh cylindrical. Since we are operating on rgb ratios independently from luminance, we shouldn't see much of a luminance shift. Destination rgb ratios have had the path to white applied. We copy hue from source to destination, and then inverse back to render gamut rgb.

![nodes_perceptual](./img/nodes_perceptual.png)

Here are two hue swatches: a pure blue, and a pure red, rendered through the display transform with a path to white applied. Note the purple and pinkish hues on the blue and red as it goes towards white.

![perceptual_01_abney](./img/perceptual_01_abney.png)

Here is the same image with the oklab perceptual model applied.

![perceptual_02_oklab](./img/perceptual_02_oklab.png)

And here is the notorious blue bar image, rendered through the Open Display Transform:

![perceptual_03](./img/perceptual_03.png)

![perceptual_04](./img/perceptual_04.png)

It helps with fire a bit too

![perceptual_01](./img/perceptual_01.png)

![perceptual_02](./img/perceptual_02.png)

And crazy images with really saturated out of gamut colors

![perceptual_05](./img/perceptual_05.png)

![perceptual_06](./img/perceptual_06.png)