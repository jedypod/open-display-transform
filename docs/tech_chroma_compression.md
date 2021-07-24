# Display Gamut Volume
What is a display  gamut volume and how is it different from a scene-linear gamut volume? One has a ceiling, the other doesn't.



# Perceptual Dechroma
We Convert display linear RGB both with (rgb) and without (rgb_nc) dechroma into ICtCp cylindrical.
In ICtCp cylindrical, R = intensity, G = saturation, B = hue.
rgb_nc is our source. rgb is our destination. We copy hue from src to dst, then invert from ICtCp back to
RGB. We have effectively bent the dechroma'd chromaticities from chromaticity-linear to perceptual hue paths,
without changing the chroma.
While in Rec2020, we also apply gamut compression. 
On rgb_nc, this is very subtle, just enough to bring commonly ocurring chromaticities beyond the spectral 
locus to within the spectral locus. This is applied because most perceptual colorspaces do not behave well when
encountering chromaticities which are beyond the spectral locus. Therefore we treat these types of 
chromaticities as "near" the spectral locus instead. This is a pragmatic solution to avoid artifacts.
