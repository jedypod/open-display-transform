/* libLMT
    -------------------------
    
    Library of functions for creating look modification transforms.

    Written by Jed Smith
    github.com/jedypod/open-display-transform

*/


/* ##########################################################################
    Utility functions
    ---------------------------
*/



// Extract a range from e0 to e1 from f, clamping values above or below.
__DEVICE__ float extract(float e0, float e1, float x) {
  return _clampf((x - e0) / (e1 - e0), 0.0f, 1.0f);
}

// Linear window function to extract a range from float x: https://www.desmos.com/calculator/uzsk5ta5v7
__DEVICE__ float extract_window(float e0, float e1, float e2, float e3, float x) {
  return x < e1 ? extract(e0, e1, x) : extract(e3, e2, x);
}

// Given hue, offset, width, extract hue angle
__DEVICE__ float extract_hue_angle(float h, float o, float w, int sm) {
  float hc = extract_window(2.0f - w, 2.0f, 2.0f, 2.0f + w, _fmod(h + o, 6.0f));
  if (sm == 1) 
    hc = hc * hc * (3.0f - 2.0f * hc); // smoothstep
  return hc;
}

// Calculate and return hue in degrees between 0 and 6
__DEVICE__ float calc_hue(float3 rgb) {
  float mx = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  float mn = _fminf(rgb.x, _fminf(rgb.y, rgb.z));
  float ch = mx - mn;
  float h;
  if (ch == 0.0f) h = 0.0f;
  else if (mx == rgb.x) h = _fmod((rgb.y - rgb.z) / ch + 6.0f, 6.0f);
  else if (mx == rgb.y) h = (rgb.z - rgb.x) / ch + 2.0f;
  else if (mx == rgb.z) h = (rgb.x - rgb.y) / ch + 4.0f;
  return h;
}

/* Chroma
    In the RGB Ratios model, traditional chroma is 1-min(r,g,b). This is equal to (max(r,g,b)-min(r,g,b))/max(r,g,b)
    Traditional chroma is unsuiteable to use as a factor for adjusting color "value" or "exposure",
    because colors close to achromatic are affected too much.
    In order to form a linear increase in exposure with increasing distance from achromatic,
    we use a novel chroma model: a lerp between min(r,g,b) and max(r,g,b): hch = max(r,g,b)*(1-f)+min(r,g,b)*f,
    where f is some factor between 0 and 1.
    When chroma = 1-min(r/hch,g/hch,b/hch), and f = 1/multiply, a linear increase in exposure with increasing
    distance from achromatic is achieved.
    In the RGB Ratios model, this simplifies to min(r,g,b)*(1-f)+f, since max(r,g,b) is always 1
*/
// Calculate chroma based on exposure for primaries
__DEVICE__ float chroma(float3 r, float m, float str) {
  float ch = _fminf(1.0f, 1.0f / m);
  ch = _fminf(r.x, _fminf(r.y, r.z)) * (1.0f - ch) + ch;
  ch = ch == 0.0f ? 0.0f : _fminf(r.x / ch, _fminf(r.y / ch, r.z / ch));
  // Chroma factor strength
  // Full strength of 1.0 is linear. Reducing strength increasingly only affects more chrominous colors.
  ch = ch * str + 1.0f - str; // 1 - lift
  return ch;
}






/*  ##########################################################################
    Notorious Six Value
    v0.0.2
    ------------------

    Value (borrowing the term from painting), refers to the brightness of a color. 
    This tool allows you to adjust the value of different colors. Includes:
      - Primary and secondary hue angle adjustments
      - Custom hue angle 
      - Zone extraction controls (disabled by default)
      - Strength parameter: controls how much colors near grey are affected.
*/


__DEVICE__ float3 nosix_value(float3 rgb, 
    float my, float mr, float mm, float mb, float mc, float mg, float mcu, 
    float cuh, float cuw, float str, int ze, float zp, int zr) {

  float3 in = rgb;
  
  // max(r,g,b) norm
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  
  float3 r; // RGB Ratios
  if (n == 0.0f) r = make_float3(0.0f, 0.0f, 0.0f);
  else r = rgb / n;

  float h = calc_hue(r);


  /* Primary hue angles: RGB
      ----------------------------  */

  // Hue extraction
  float3 hp = make_float3(
    extract_hue_angle(h, 2.0f, 1.0f, 1),
    extract_hue_angle(h, 6.0f, 1.0f, 1),
    extract_hue_angle(h, 4.0f, 1.0f, 1));
 
   // Exposure - input param range is -1 to 1, output exposure is +/- 4 stops.
  const float3 mp = make_float3(
    _powf(2.0f, mr * 4.0f),
    _powf(2.0f, mg * 4.0f),
    _powf(2.0f, mb * 4.0f));
 
   // Power
  const float3 pp = make_float3(
    _fminf(1.0f, 2.0f / mp.x),
    _fminf(1.0f, 2.0f / mp.y),
    _fminf(1.0f, 2.0f / mp.z));

  // Adjust hue width with inverse power function: "Smooth1". Width decreases with exposure.
  float3 hp_w = make_float3(
    1.0f - _powf(1.0f - hp.x, pp.x),
    1.0f - _powf(1.0f - hp.y, pp.y),
    1.0f - _powf(1.0f - hp.z, pp.z));

  // Multiplication factor: combine for all hue angles
  float mfp = ((1.0f - hp_w.x) + mp.x * hp_w.x) * ((1.0f - hp_w.y) + mp.y * hp_w.y) * ((1.0f - hp_w.z) + mp.z * hp_w.z);

  // Chroma
  float chp = chroma(r, mfp, str);
  

  /* Secondary hue angles: CMY
        ----------------------------  */
  
  // Hue extraction
  float3 hs = make_float3(
    extract_hue_angle(h, 5.0f, 1.0f, 1),
    extract_hue_angle(h, 3.0f, 1.0f, 1),
    extract_hue_angle(h, 1.0f, 1.0f, 1));

  const float3 ms = make_float3(
    _powf(2.0f, mc * 4.0f),
    _powf(2.0f, mm * 4.0f),
    _powf(2.0f, my * 4.0f));
 
  const float3 ps = make_float3(
    _fminf(1.0f, 2.0f / ms.x),
    _fminf(1.0f, 2.0f / ms.y),
    _fminf(1.0f, 2.0f / ms.z));
 
  float3 hs_w = make_float3(
      1.0f - _powf(1.0f - hs.x, ps.x),
      1.0f - _powf(1.0f - hs.y, ps.y),
      1.0f - _powf(1.0f - hs.z, ps.z));

  float mfs = ((1.0f - hs_w.x) + ms.x * hs_w.x) * ((1.0f - hs_w.y) + ms.y * hs_w.y) * ((1.0f - hs_w.z) + ms.z * hs_w.z);

  // Chroma
  float chs = chroma(r, mfs, str);


  /* Custom hue angle: Defaults to orange
      ----------------------------  */

  float hc = extract_hue_angle(h, cuh / 60.0f, cuw, 1);
  float m_c = _powf(2.0f, mcu * 4.0f);
  float m_p = _fminf(1.0f, 2.0f / m_c);
  float hc_w = 1.0f - _powf(1.0f - hc, m_p);
  float mfc = (1.0f - hc_w) + m_c * hc_w;
  float chc = chroma(r, mfc, str);

  // Apply exposure
  r = mfp * r * (1.0f - chp) + r * chp;
  r = mfs * r * (1.0f - chs) + r * chs;
  r = mfc * r * (1.0f - chc) + r * chc;
  
  rgb = r * n;

  // Zone extract
  if (ze == 1) {
    n = _fmaxf(1e-12f, n);
    const float fl = 0.004f;
    float zpow = _powf(2.0f, -zp + 1.0f);
    float toe = (n * n / (n + fl));
    float f = _powf((toe / (toe + 1.0f)) / n, zpow);
    if (zr == 1) f = 1.0f - _powf((n / (n + 1.0f)) / n, zpow);
    rgb = in * (1.0f - f) + rgb * f;
  }

  return rgb;
}






/* Notorious Six Vibrance
    v0.0.2
    ------------------

    Vibrance emulates what happens to color in the bottom end of
    a per-channel contrast increase: Secondary hues are bent towards primary hues.

    Image "richness" is increased without slamming into the gamut boundary as with a 
    traditional saturation adjustment. 

    If chromaticity-linear is enabled, chroma is adjusted on a linear line between 
    source chromaticity and the achromatic axis. Otherwise, hue bends toward primaries (RGB).    

*/


__DEVICE__ float3 nosix_vibrance(float3 rgb, 
    float mgl, float my, float mr, float mm, float mb, float mc, float mg, float mcu, 
    float cuh, float cuw, float str, float chl, int ze, float zp, int zr) {

  float3 in = rgb;

  // Parameter setup
  float3 pp = make_float3(
    (mr + 1.0f) * (mgl + 1.0f),
    (mg + 1.0f) * (mgl + 1.0f),
    (mb + 1.0f) * (mgl + 1.0f));
  float3 ps = make_float3(
    (mc + 1.0f) * (mgl + 1.0f),
    (mm + 1.0f) * (mgl + 1.0f),
    (my + 1.0f) * (mgl + 1.0f));
  
  float pc = (mcu + 1.0f);

  // max(r,g,b) norm
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  
  float3 r; // RGB Ratios
  if (n == 0.0f) r = make_float3(0.0f, 0.0f, 0.0f);
  else r = rgb / n;
  // r = maxf3(-1.0f, r);

  float h = calc_hue(r);

  // hue extraction for primaries (RGB)
  float3 hp = make_float3(
    extract_hue_angle(h, 2.0f, 1.0f, 0),
    extract_hue_angle(h, 6.0f, 1.0f, 0),
    extract_hue_angle(h, 4.0f, 1.0f, 0));

  // hue extraction for secondaries (CMY)
  float3 hs = make_float3(
    extract_hue_angle(h, 5.0f, 1.0f, 0),
    extract_hue_angle(h, 3.0f, 1.0f, 0),
    extract_hue_angle(h, 1.0f, 1.0f, 0));

  float hc = extract_hue_angle(h, cuh / 60.0f, cuw, 0);

  if (chl == 0) {
    // Primary hue angle vibrance adjustment
    r.x = r.x < 0.0f ? r.x : _powf(r.x, pp.x) * hp.x + _powf(r.x, pp.y) * hp.y + _powf(r.x, pp.z) * hp.z + r.x * (1.0f - (hp.x + hp.y + hp.z));
    r.y = r.y < 0.0f ? r.y : _powf(r.y, pp.x) * hp.x + _powf(r.y, pp.y) * hp.y + _powf(r.y, pp.z) * hp.z + r.y * (1.0f - (hp.x + hp.y + hp.z));
    r.z = r.z < 0.0f ? r.z : _powf(r.z, pp.x) * hp.x + _powf(r.z, pp.y) * hp.y + _powf(r.z, pp.z) * hp.z + r.z * (1.0f - (hp.x + hp.y + hp.z));

    // Secondary hue angle vibrance adjustment
    r.x = r.x < 0.0f ? r.x : _powf(r.x, ps.x) * hs.x + _powf(r.x, ps.y) * hs.y + _powf(r.x, ps.z) * hs.z + r.x * (1.0f - (hs.x + hs.y + hs.z));
    r.y = r.y < 0.0f ? r.y : _powf(r.y, ps.x) * hs.x + _powf(r.y, ps.y) * hs.y + _powf(r.y, ps.z) * hs.z + r.y * (1.0f - (hs.x + hs.y + hs.z));
    r.z = r.z < 0.0f ? r.z : _powf(r.z, ps.x) * hs.x + _powf(r.z, ps.y) * hs.y + _powf(r.z, ps.z) * hs.z + r.z * (1.0f - (hs.x + hs.y + hs.z));

    // Custom hue angle vibrance adjustment
    r.x = r.x < 0.0f ? r.x : _powf(r.x, pc) * hc + r.x * (1.0f - hc);
    r.y = r.y < 0.0f ? r.y : _powf(r.y, pc) * hc + r.y * (1.0f - hc);
    r.z = r.z < 0.0f ? r.z : _powf(r.z, pc) * hc + r.z * (1.0f - hc);
  } 
  else {
    // Chromaticity-linear

    float c =  1.0f - _fminf(r.x, _fminf(r.y, r.z)); // Chroma
    c = _powf( _fmaxf(0.0f, c), str); 

    // Modify parameter scales for chromaticity-linear
    pp = make_float3(
      (mr < 0.0f ? mr * 0.9f + 1.0f : mr * 3.0f + 1.0f) * ((mgl > 0.0f ? mgl * 3.0f : mgl * 0.9f) + 1.0f),
      (mg < 0.0f ? mg * 0.9f + 1.0f : mg * 3.0f + 1.0f) * ((mgl > 0.0f ? mgl * 3.0f : mgl * 0.9f) + 1.0f),
      (mb < 0.0f ? mb * 0.9f + 1.0f : mb * 3.0f + 1.0f) * ((mgl > 0.0f ? mgl * 3.0f : mgl * 0.9f) + 1.0f));
    ps = make_float3(
      (mc < 0.0f ? mc * 0.9f + 1.0f : mc * 3.0f + 1.0f) * ((mgl > 0.0f ? mgl * 3.0f : mgl * 0.9f) + 1.0f),
      (mm < 0.0f ? mm * 0.9f + 1.0f : mm * 3.0f + 1.0f) * ((mgl > 0.0f ? mgl * 3.0f : mgl * 0.9f) + 1.0f),
      (my < 0.0f ? my * 0.9f + 1.0f : my * 3.0f + 1.0f) * ((mgl > 0.0f ? mgl * 3.0f : mgl * 0.9f) + 1.0f));
    pc = (mcu < 0.0f ? mcu * 0.9f + 1.0f : mcu * 3.0f + 1.0f);

    float m = _fminf(r.x, _fminf(r.y, r.z)) * (1.0 - str) + str;
    float vf;

    // Primaries
    vf = c == 0.0f ? 1.0f : ((1.0f - _powf(1.0f - c, pp.x)) * hp.x + (1.0f - _powf(1.0f - c, pp.y)) * hp.y + (1.0f - _powf(1.0f - c, pp.z)) * hp.z + c * (1.0f - (hp.x + hp.y + hp.z))) / c;
    r = m * (1.0f - vf) + r * vf;

    // Secondaries
    vf = c == 0.0f ? 1.0f : ((1.0f - _powf(1.0f - c, ps.x)) * hs.x + (1.0f - _powf(1.0f - c, ps.y)) * hs.y + (1.0f - _powf(1.0f - c, ps.z)) * hs.z + c * (1.0f - (hs.x + hs.y + hs.z))) / c;
    r = m * (1.0f - vf) + r * vf;

    // Custom
    vf = c == 0.0f ? 1.0f : ((1.0f - _powf(1.0f - c, pc)) * hc + c * (1.0f - hc)) / c;
    r = m * (1.0f - vf) + r * vf;
    
  }

  rgb = r * n;

  // Zone extract
  if (ze == 1) {
    n = _fmaxf(1e-12f, n);
    const float fl = 0.004f;
    float zpow = _powf(2.0f, -zp + 1.0f);
    float toe = (n * n / (n + fl));
    float f = _powf((toe / (toe + 1.0f)) / n, zpow);
    if (zr == 1) f = 1.0f - _powf((n / (n + 1.0f)) / n, zpow);
    rgb = in * (1.0f - f) + rgb * f;
  }

  return rgb;
}






/* Notorious Six Hue Shift
    v0.0.3
    ------------------
    Per hue-angle hue shift tool. Good for color cross-talk effects and
    precise control over hue shifts over specific luminance and/or chrominance ranges.

*/


__DEVICE__ float3 nosix_hueshift(float3 rgb, 
    float sy, float sr, float sm, float sb, float sc, float sg, float scu, 
    float cuh, float cuw, float str, float chl, int ze, float zp, int zr) {
  
  float3 in = rgb;

  // max(r,g,b) norm
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  
  // RGB Ratios
  float3 r;
  if (n == 0.0f) r = make_float3(0.0f, 0.0f, 0.0f);
  else r = rgb / n;
 
  // Chroma
  // Strength controls a lerp between min(r,g,b) and max(r,g,b) for the calculation of chroma
  float ch = _fminf(r.x, _fminf(r.y, r.z)) * (1.0f - str) + str;
  ch = ch == 0.0f ? 0.0f : _fminf(1.0f, 1.0f - _fminf(r.x / ch, _fminf(r.y / ch, r.z / ch)));
  
  // Chroma limit: reduces effect on more saturated colors, depending on chroma limit strength
  // 0.5 < chl < 1 : power function on limit
  // 0 < chl < 0.5 : mix back limit (better handles out of gamut colorimetry)
  float f0 = chl < 0.5f ? _fmaxf(0.0f, 0.5f - chl) * 2.0f : 1.0f / _fmaxf(1e-3f, (1.0f - chl) * 2.0f);
  ch = chl < 0.5f ? ch * f0 + ch * (1.0f - ch) * (1.0f - f0) : ch * _powf(_fmaxf(0.0f, 1.0f - ch), f0);

  // Hue
  float hue = calc_hue(r);

  // Hue extraction for primaries (RGB)
  float3 hp = make_float3(
    extract_hue_angle(hue, 2.0f, 1.0f, 0),
    extract_hue_angle(hue, 6.0f, 1.0f, 0),
    extract_hue_angle(hue, 4.0f, 1.0f, 0));
  hp = hp * ch;

  // Hue extraction for secondaries (CMY)
  float3 hs = make_float3(
    extract_hue_angle(hue, 5.0f, 1.0f, 0),
    extract_hue_angle(hue, 3.0f, 1.0f, 0),
    extract_hue_angle(hue, 1.0f, 1.0f, 0));
  hs = hs * ch;

  // Hue shift primaries
  r.x = (r.x - sb) * hp.z + (r.x + sg) * hp.y + r.x * (1.0f - (hp.z + hp.y));
  r.y = (r.y + sr) * hp.x + (r.y + sb) * hp.z + r.y * (1.0f - (hp.x + hp.z));
  r.z = (r.z - sr) * hp.x + (r.z - sg) * hp.y + r.z * (1.0f - (hp.x + hp.y));
  
  // Hue shift secondaries
  r.x = (r.x + sy) * hs.z + (r.x - sm) * hs.y + r.x * (1.0f - (hs.z + hs.y));
  r.y = (r.y + sc) * hs.x + (r.y - sy) * hs.z + r.y * (1.0f - (hs.x + hs.z));
  r.z = (r.z - sc) * hs.x + (r.z + sm) * hs.y + r.z * (1.0f - (hs.x + hs.y));

  // Hue extraction for custom
  float hc = extract_hue_angle(hue, cuh / 60.0f, cuw, 0);
  hc = hc * ch;
  
  // Calculate params for custom hue angle shift
  float h = cuh / 60.0f; // Convert degrees to 0-6 hue angle
  float s = scu * cuw; // Rotate only as much as the custom width
  // Calculate per-channel shift values based on hue angle
  float sc0 = 1.0f<=h&&h<2.0f?s*(h-1.0f):2.0f<=h&&h<3.0f?s*(3.0f-h):4.0f<=h&&h<5.0f?-s*(h-4.0f):5.0f<=h&&h<6.0f?-s*(6.0f-h):0.0f;
  float sc1 = 0.0f<=h&&h<1.0f?s*(1.0f-h):2.0f<=h&&h<3.0f?-s*(h-2.0f):3.0f<=h&&h<4.0f?-s*(4.0f-h):5.0f<=h&&h<6.0f?s*(h-5.0f):0.0f;
  float sc2 = 0.0f<=h&&h<1.0f?-s*(h-0.0f):1.0f<=h&&h<2.0f?-s*(2.0f-h):3.0f<=h&&h<4.0f?s*(h-3.0f):4.0f<=h&&h<5.0f?s*(5.0f-h):0.0f;

  // Hue shift custom
  r.x = (r.x + sc2) * hc + (r.x - sc1) * hc + r.x * (1.0f - (hc + hc));
  r.y = (r.y + sc0) * hc + (r.y - sc2) * hc + r.y * (1.0f - (hc + hc));
  r.z = (r.z - sc0) * hc + (r.z + sc1) * hc + r.z * (1.0f - (hc + hc));
  
  rgb = r * n;

  // Zone extract
  if (ze == 1) {
    n = _fmaxf(1e-12f, n);
    const float fl = 0.004f;
    float zpow = _powf(2.0f, -zp + 1.0f);
    float toe = (n * n / (n + fl));
    float f = _powf((toe / (toe + 1.0f)) / n, zpow);
    if (zr == 1) f = 1.0f - _powf((n / (n + 1.0f)) / n, zpow);
    rgb = in * (1.0f - f) + rgb * f;
  }

  return rgb;
}






/* Zone Grade
    v0.0.1
    Chromaticity-preserving grading tool.

*/


__DEVICE__ float ex_high(float n, float ex, float pv, float fa) {
  // Zoned highlight exposure with falloff : https://www.desmos.com/calculator/csupr8rjk8

  // Parameter setup
  const float f = 5.0f * _powf(fa, 1.6f) + 1.0f;
  const float p = _fabs(ex + f) < 1e-8f ? 1e-8f : (ex + f) / f;
  const float m = _powf(2.0f, ex);
  const float t0 = 0.18f * _powf(2.0f, pv);
  const float a = _powf(t0, 1.0f - p) / p;
  const float b = t0 * (1.0f - 1.0f / p);
  const float x1 = t0 * _powf(2.0f, f);
  const float y1 = a * _powf(x1, p) + b;

  // Calculate scale factor for rgb
  float s = n < t0 ? 1.0f : n > x1 ? (m * (n - x1) + y1) / n : (a * _powf(n, p) + b) / n;
  return s;
}


__DEVICE__ float ex_low(float n, float ex, float pv, float fa) {
  // Zoned shadow exposure with falloff : https://www.desmos.com/calculator/oz8eyxoo9k

  // Parameter setup
  const float f = 6.0f - 5.0f * fa;
  const float p = _fminf(f / 2.0f, f / 2.0f * _powf(0.5, ex));
  const float t0 = 0.18f * _powf(2.0f, pv);
  const float _c = _powf(2.0f, ex);
  const float _a = _powf(t0, -p - 1.0f) * p * (_c - 1.0f);
  const float _b = -_powf(t0, -p) * (_c - 1.0f) * (p + 1.0f);
  
  // Calculate scale factor for rgb
  float s = n > t0 || n < 0.0f ? 1.0f : _powf(n, p) * (_a * n + _b) + _c; // implicit divide by n here
  return s;
}

__DEVICE__ float3 zone_grade(float3 rgb, 
    float ex, float c, float pv, float off, 
    float he, float hp, float hf, float le, float lp, float lf, 
    float he2, float hp2, float hf2, float le2, float lp2, float lf2) {

  // Parameter setup
  const float m = _powf(2.0f, ex);
  const float p = 0.18f * _powf(2.0f, pv);

  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));

  // Global controls
  rgb += off;
  float s = c == 1.0f ? m : n < 0.0f ? 1.0f : _powf(n / p, c - 1.0f) * m;
  rgb *= s;

  // Zone High
  n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  rgb *= ex_high(n, he, hp, hf);
  
  // Zone Low
  n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  rgb *= ex_low(n, le, lp, lf);

  // Zone Higher
  n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  rgb *= ex_high(n, he2, hp2, hf2);
  
  // Zone Lower
  n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  rgb *= ex_low(n, le2, lp2, lf2);

  return rgb;
}