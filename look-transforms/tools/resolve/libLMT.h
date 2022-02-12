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


__DEVICE__ float3 zone_extract(float3 in, float3 rgb, float zp, int zr) {
  float n = _fmaxf(1e-12f, _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z)));
  const float fl = 0.01f;
  float zpow = _powf(2.0f, -zp + 1.0f);
  float toe = (n * n / (n + fl));
  float f = _powf((toe / (toe + 1.0f)) / n, zpow);
  if (zr == 1) f = 1.0f - _powf((n / (n + 1.0f)) / n, zpow);
  return in * (1.0f - f) + rgb * f;
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


__DEVICE__ float lin_to_log_lx(float x, float mn, float mx, float sps) {
  // linear to log2 with linear extension : https://www.desmos.com/calculator/qmbh2z6ms6
  float sp = 0.18f*_powf(2.0f, sps); // splice point in stops around 0.18
  float lo = (_log2f(sp/0.18f) - mn)/(mx - mn); // Linear offset
  float ls = sp*(mx - mn)*_logf(2.0f); // Linear scale
  return x > sp ? (_log2f(x/0.18f) - mn)/(mx - mn):(x - sp)/ls + lo;
}

__DEVICE__ float log_to_lin_lx(float x, float mn, float mx, float sps) {
  float sp = 0.18f*_powf(2.0f, sps); // splice point in stops around 0.18
  float lo = (_log2f(sp/0.18f) - mn)/(mx - mn); // Linear offset
  float ls = sp*(mx - mn)*_logf(2.0f); // Linear scale
  return x > lo ? 0.18*_powf(2.0f, (x*(mx - mn) + mn)) : ls*(x - lo) + sp;
}



/*  ##########################################################################
    Notorious Six Chroma Value
    v0.0.3
    ------------------

    Value (borrowing the term from painting), refers to the brightness of a color. 
    This tool allows you to adjust the value of different colors. Includes:
      - Primary and secondary hue angle adjustments
      - Custom hue angle 
      - Zone extraction controls (disabled by default)
      - Strength parameter: controls how much colors near grey are affected.
*/


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
  ch = ch == 0.0f ? 1.0f : 1.0f - _fminf(r.x / ch, _fminf(r.y / ch, r.z / ch));
  // Chroma strength: 1 is linear. Reducing strength increasingly affects only more pure colors.
  // We use a variable-width power compression function, but this could be a multiply
  float w = 1.0f - str;
  ch = ch == 0.0f ? 0.0f : _powf(ch, w + 2.0f) / (_powf(ch, w + 1.0f) + w);
  return ch;
}


__DEVICE__ float3 n6_chroma_value(float3 rgb, 
    float my, float mr, float mm, float mb, float mc, float mg, float mcu, 
    float cuh, float cuw, float str, int ze, float zp, int zr, int smst) {

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
    extract_hue_angle(h, 2.0f, 1.0f, smst),
    extract_hue_angle(h, 6.0f, 1.0f, smst),
    extract_hue_angle(h, 4.0f, 1.0f, smst));
 
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
  float chp = _fminf(2.0f, chroma(r, mfp, str));
  

  /* Secondary hue angles: CMY
        ----------------------------  */
  
  // Hue extraction
  float3 hs = make_float3(
    extract_hue_angle(h, 5.0f, 1.0f, smst),
    extract_hue_angle(h, 3.0f, 1.0f, smst),
    extract_hue_angle(h, 1.0f, 1.0f, smst));

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
  float chs = _fminf(2.0f, chroma(r, mfs, str));


  /* Custom hue angle: Defaults to orange
      ----------------------------  */

  float hc = extract_hue_angle(h, cuh / 60.0f, cuw, smst);
  float m_c = _powf(2.0f, mcu * 4.0f);
  float m_p = _fminf(1.0f, 2.0f / m_c);
  float hc_w = 1.0f - _powf(1.0f - hc, m_p);
  float mfc = (1.0f - hc_w) + m_c * hc_w;
  float chc = _fminf(2.0f, chroma(r, mfc, str));

  // Apply exposure
  r = mfp * r * chp + r * (1.0f - chp);
  r = mfs * r * chs + r * (1.0f - chs);
  r = mfc * r * chc + r * (1.0f - chc);
  
  rgb = r * n;

  // Zone extract
  if (ze == 1) rgb = zone_extract(in, rgb, zp, zr);

  return rgb;
}






/* Notorious Six Vibrance
    v0.0.3
    ------------------

    **Description**
      Vibrance creates a nonlinear compression of chroma towards the gamut boundary.
      Effectively this increases apparent colorfullness for "mid-range" chroma values,
      without pushing colors beyond the gamut boundary like a traditional 
      distance-based saturation control.

    **Controls**
      - Global vibrance control
      - Per hue-angle controls
      - Custom hue-angle control
      - Hue-linear control. If at 1.0, chroma is adjusted on a linear line between 
        original chromaticity and the achromatic axis. Otherwise, hues are bent
        towards primary hue angles (RGB), similar to what happens in per-channel
        contrast increase.
      - Optional zone range extraction to limit effect to shadows or highlights

*/


__DEVICE__ float3 n6_vibrance(float3 rgb, 
    float mgl, float my, float mr, float mm, float mb, float mc, float mg, float mcu, 
    float cuh, float cuw, float hl, int ze, float zp, int zr) {

  float3 in = rgb;

  // Parameter setup for nonlinear vibrance
  const float p_base = 3.0f; // strength of controls
  const float mgl_str = _powf(p_base, mgl); // global strength multiplier
  const float3 pp = make_float3(
    _powf(p_base, mr) * mgl_str,
    _powf(p_base, mg) * mgl_str,
    _powf(p_base, mb) * mgl_str);
  const float3 ps = make_float3(
    _powf(p_base, mc) * mgl_str,
    _powf(p_base, mm) * mgl_str,
    _powf(p_base, my) * _powf(p_base / 1.5f, mgl)); // reduce influence for yellow
  const float pc = _powf(p_base, mcu);


  // max(r,g,b) norm
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  
  float3 r; // RGB Ratios
  if (n == 0.0f) r = make_float3(0.0f, 0.0f, 0.0f);
  else r = rgb / n;
  
  // Protect against crazy negative values
  r = make_float3(_fmaxf(r.x, -1.0f), _fmaxf(r.y, -1.0f), _fmaxf(r.z, -1.0f));

  // Calculate hue angle and chroma
  float h = calc_hue(r);
  float c =  1.0f - _fminf(r.x, _fminf(r.y, r.z));
  
  float3 r_hl = r; // rgb ratios for hue-linear vibrance

  // hue extraction for primaries (RGB)
  float3 hp = make_float3(
    extract_hue_angle(h, 2.0f, 1.0f, 0),
    extract_hue_angle(h, 6.0f, 1.0f, 0),
    extract_hue_angle(h, 4.0f, 1.0f, 0));
  hp = hp * c;

  // hue extraction for secondaries (CMY)
  float3 hs = make_float3(
    extract_hue_angle(h, 5.0f, 1.0f, 0),
    extract_hue_angle(h, 3.0f, 1.0f, 0),
    extract_hue_angle(h, 1.0f, 1.0f, 0));
  hs = hs * c;

  float hc = extract_hue_angle(h, cuh / 60.0f, cuw, 0);
  hc = hc * c;

  // Primary hue angle vibrance adjustment
  r.x = r.x < 0.0f ? r.x : 
    _powf(r.x, pp.x) * hp.x + _powf(r.x, pp.y) * hp.y + _powf(r.x, pp.z) * hp.z + r.x * 
    (1.0f - (hp.x + hp.y + hp.z));
  r.y = r.y < 0.0f ? r.y : 
    _powf(r.y, pp.x) * hp.x + _powf(r.y, pp.y) * hp.y + _powf(r.y, pp.z) * hp.z + r.y * 
    (1.0f - (hp.x + hp.y + hp.z));
  r.z = r.z < 0.0f ? r.z : 
    _powf(r.z, pp.x) * hp.x + _powf(r.z, pp.y) * hp.y + _powf(r.z, pp.z) * hp.z + r.z * 
    (1.0f - (hp.x + hp.y + hp.z));

  // Secondary hue angle vibrance adjustment
  r.x = r.x < 0.0f ? r.x : 
    _powf(r.x, ps.x) * hs.x + _powf(r.x, ps.y) * hs.y + _powf(r.x, ps.z) * hs.z + r.x * 
    (1.0f - (hs.x + hs.y + hs.z));
  r.y = r.y < 0.0f ? r.y : 
    _powf(r.y, ps.x) * hs.x + _powf(r.y, ps.y) * hs.y + _powf(r.y, ps.z) * hs.z + r.y * 
    (1.0f - (hs.x + hs.y + hs.z));
  r.z = r.z < 0.0f ? r.z : 
    _powf(r.z, ps.x) * hs.x + _powf(r.z, ps.y) * hs.y + _powf(r.z, ps.z) * hs.z + r.z * 
    (1.0f - (hs.x + hs.y + hs.z));

  // Custom hue angle vibrance adjustment
  r.x = r.x < 0.0f ? r.x : _powf(r.x, pc) * hc + r.x * (1.0f - hc);
  r.y = r.y < 0.0f ? r.y : _powf(r.y, pc) * hc + r.y * (1.0f - hc);
  r.z = r.z < 0.0f ? r.z : _powf(r.z, pc) * hc + r.z * (1.0f - hc);


  // Chromaticity-linear vibrance adjustment
  float m, vf;

  // Primary hue angles
  vf = c == 0.0f || c > 1.0f ? 1.0f : 
    ((1.0f - _powf(1.0f - c, pp.x)) * hp.x + (1.0f - _powf(1.0f - c, pp.y)) * hp.y + 
    (1.0f - _powf(1.0f - c, pp.z)) * hp.z + c * (1.0f - (hp.x + hp.y + hp.z))) / c;
  m = 1.1f; // lerp target > 1 darkens vibrance boosted colors. 1.1 tuned by eye to match per-channel 
  r_hl = m * (1.0f - vf) + r_hl * vf;

  // Secondary hue angles
  vf = c == 0.0f || c > 1.0f ? 1.0f : 
    ((1.0f - _powf(1.0f - c, ps.x)) * hs.x + (1.0f - _powf(1.0f - c, ps.y)) * hs.y + 
    (1.0f - _powf(1.0f - c, ps.z)) * hs.z + c * (1.0f - (hs.x + hs.y + hs.z))) / c;
  m = 1.0f; // don't want to darken secondaries.
  r_hl = m * (1.0f - vf) + r_hl * vf;

  // Custom hue angle
  vf = c == 0.0f || c > 1.0f ? 1.0f : 
    ((1.0f - _powf(1.0f - c, pc)) * hc + c * (1.0f - hc)) / c;
  r_hl = m * (1.0f - vf) + r_hl * vf;


  // Mix between nonlinear and hue-linear vibrance adjustment
  r = r * (1.0f - hl) + r_hl * hl;

  rgb = r * n;

  // Zone extract
  if (ze == 1) rgb = zone_extract(in, rgb, zp, zr);

  return rgb;
}






/* Notorious Six Hue Shift
    v0.0.4
    ------------------
    Per hue-angle hue shift tool. Good for color cross-talk effects and
    precise control over hue shifts over specific luminance and/or chrominance ranges.

*/


__DEVICE__ float3 n6_hueshift(float3 rgb, 
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
  r.x = r.x + sb*hp.z - sg*hp.y;
  r.y = r.y + sr*hp.x - sb*hp.z;
  r.z = r.z + sg*hp.y - sr*hp.x;
  
  // Hue shift secondaries
  r.x = r.x + sy*hs.z - sm*hs.y;
  r.y = r.y + sc*hs.x - sy*hs.z;
  r.z = r.z + sm*hs.y - sc*hs.x;

  // Hue extraction for custom
  float hc = extract_hue_angle(hue, cuh / 60.0f, cuw, 0);
  hc = hc * ch;
  
  // Calculate params for custom hue angle shift
  float h = cuh / 60.0f; // Convert degrees to 0-6 hue angle
  float s = scu * cuw; // Rotate only as much as the custom width
  // Calculate per-channel shift values based on hue angle
  float sc0 = h < 3.0f ? s - s*_fminf(1, _fabs(h - 2.0f)) : s*_fminf(1.0f, _fabs(h - 5.0f)) - s;
  float sc1 = h < 1.0f ? s - s*_fminf(1.0f, _fabs(h)) : h < 5.0f ? s*_fminf(1.0f, _fabs(h - 3.0f)) - s : s - s*_fminf(1.0f, _fabs(h - 6.0f));
  float sc2 = h < 2.0f ? s*_fminf(1.0f, _fabs(h - 1.0f)) - s : s - s*_fminf(1.0f, _fabs(h - 4.0f));

  // Hue shift custom
  r.x = r.x + hc*(sc2-sc1);
  r.y = r.y + hc*(sc0-sc2);
  r.z = r.z + hc*(sc1-sc0);
  
  rgb = r * n;

  // Zone extract
  if (ze == 1) rgb = zone_extract(in, rgb, zp, zr);

  return rgb;
}






/* Zone Grade
    v0.0.1
    Chromaticity-preserving grading tool.

*/


__DEVICE__ float3 ex_high(float3 rgb, float ex, float pv, float fa, int inv) {
  // Zoned highlight exposure with falloff : https://www.desmos.com/calculator/ylq5yvkhoq

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
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  float s;
  if (inv == 1)
    s = n < t0 ? 1.0f : n > y1 ? ((m * x1 - y1 + n) / m) / n : _powf((n - b) / a, 1.0f / p) / n;
  else
    s = n < t0 ? 1.0f : n > x1 ? (m * (n - x1) + y1) / n : (a * _powf(n, p) + b) / n;
  return rgb * s;
}

__DEVICE__ float3 ex_low(float3 rgb, float ex, float pv, float fa) {
  // Zoned shadow exposure with falloff : https://www.desmos.com/calculator/my116fpnix
  // https://colab.research.google.com/drive/1GAoiqR33U2zlW5fw1byUdZBw7eqJibjN

  // Parameter setup
  const float f = 6.0f - 5.0f * fa;
  const float p = _fminf(f / 2.0f, f / 2.0f * _powf(0.5, ex));
  const float t0 = 0.18f * _powf(2.0f, pv);
  const float _c = _powf(2.0f, ex);
  const float _a = p*(_c - 1.0f)/_powf(t0, p + 1.0f);
  const float _b = (1.0f - _c)*(p + 1.0f)/_powf(t0, p);
  
  // Calculate scale factor for rgb
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  float s = n > t0 || n < 0.0f ? 1.0f : _powf(n, p) * (_a * n + _b) + _c; // implicit divide by n here
  return rgb * s;
}


__DEVICE__ float3 grade(float3 rgb, float ex, float c, float pv, float off) {
  // Simple chromaticity-preserving grade operator: exposure, pivoted contrast, offset
  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  const float m = _powf(2.0f, ex);
  const float p = 0.18f * _powf(2.0f, pv);
  rgb += off;
  float s = c == 1.0f ? m : n < 0.0f ? 1.0f : _powf(n / p, c - 1.0f) * m;
  rgb *= s;
  return rgb;
}


__DEVICE__ float3 zone_grade(float3 rgb, 
    float ex, float c, float pv, float off, 
    float he, float hp, float hf, float le, float lp, float lf, 
    float he2, float hp2, float hf2, float le2, float lp2, float lf2) {
  
  float n;
  
  // Global grade
  rgb = grade(rgb, ex, c, pv, off);
  
  // Zone High
  rgb = ex_high(rgb, he, hp, hf, 0);
  
  // Zone Low
  rgb = ex_low(rgb, le, lp, lf);

  // Zone Higher
  rgb = ex_high(rgb, he2, hp2, hf2, 0);
  
  // Zone Lower
  rgb = ex_low(rgb, le2, lp2, lf2);

  return rgb;
}


/* Shadow Contrast
    Invertible cubic shadow exposure function
    https://www.desmos.com/calculator/ubgteikoke
    https://colab.research.google.com/drive/1JT_-S96RZyfHPkZ620QUPIRfxmS_rKlx
*/
__DEVICE__ float3 shd_con(float3 rgb, float ex, float str, int invert) {
  // Parameter setup
  const float m = _powf(2.0f, ex);
  const float w = _powf(str, 3.0f);

  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  float n2 = n*n;
  float s;
  if (invert == 0) {
    s = (n2 + m*w)/(n2 + w); // Implicit divide by n
  } else {
    float p0 = n2 - 3.0f*m*w;
    float p1 = 2.0f*n2 + 27.0f*w - 9.0f*m*w;
    float p2 = _powf(_sqrtf(n2*p1*p1 - 4*p0*p0*p0)/2.0f + n*p1/2.0f,1.0f/3.0f);
    s = (p0/(3.0f*p2) + p2/3.0f + n/3.0f) / n;
  }
  rgb *= s;
  return rgb;
}

/* Highlight Contrast
    Invertible quadratic highlight contrast function. Same as ex_high without lin ext
    https://www.desmos.com/calculator/p7j4udnwkm
*/
__DEVICE__ float3 hl_con(float3 rgb, float ex, float th, int invert) {
  // Parameter setup
  float p = _powf(2.0f, -ex);
  float t0 = 0.18f*_powf(2.0f, th);
  float a = _powf(t0, 1.0f - p)/p;
  float b = t0*(1.0f - 1.0f/p);

  float n = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z));
  float s;
  if (n == 0.0f || n < t0) {
    s = 1.0f;
  } else {
    if (invert == 1) 
      s = (a*_powf(n, p) + b)/n;
    else 
      s = _powf((n - b)/a, 1.0f/p)/n;
  }
  return rgb * s;
}



/* Saturation

*/

__DEVICE__ float3 saturation(float3 rgb, float sag, float sah, 
  float ho, float hw, float wr, float wb, int lg, int ze, float zp, int zr) {

  float wg = 1.0f - (wr + wb);
  
  float3 in = rgb;

  float hf = extract_hue_angle(calc_hue(rgb), ho, hw, 0);
  hf = _fmaxf(0.0f, hf);

  // If apply in log, expand gamut 20% then convert to log2
  if (lg == 1) {
    // Expand gamut 20%
    rgb = _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z))*0.2f + rgb*0.8f;

    rgb.x = lin_to_log_lx(rgb.x, -7.0f, 7.0f, -4.0f);
    rgb.y = lin_to_log_lx(rgb.y, -7.0f, 7.0f, -4.0f);
    rgb.z = lin_to_log_lx(rgb.z, -7.0f, 7.0f, -4.0f);
  }

  // "Luminance"
  float L = wr*rgb.x + wg*rgb.y + wb*rgb.z;

  // Apply saturation
  rgb = L - sag*(hf*sah - hf + 1.0f)*(L - rgb);

  if (lg == 1) {
    rgb.x = log_to_lin_lx(rgb.x, -7.0f, 7.0f, -4.0f);
    rgb.y = log_to_lin_lx(rgb.y, -7.0f, 7.0f, -4.0f);
    rgb.z = log_to_lin_lx(rgb.z, -7.0f, 7.0f, -4.0f);
    
    // Reduce gamut 20%
    rgb = rgb*1.25f - _fmaxf(rgb.x, _fmaxf(rgb.y, rgb.z))/4.0f;
  }

  // Zone extract
  if (ze == 1) rgb = zone_extract(in, rgb, zp, zr);

  return rgb;
}