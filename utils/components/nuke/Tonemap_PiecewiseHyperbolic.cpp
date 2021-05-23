/* Tonemap Piecewise Hyperbolic
    by Jed Smith - v0.0.1

    Desmos plot
    https://www.desmos.com/calculator/n2pkbijupz

  Presets
  -----------
    SDR - Dark Surround
    Lp 100 Lw 100 Lg 10.5 c 1.4 ps 1 t0 0.004
    SDR - Dim Surround
    Lp 100 Lw 100 Lg 10.5 c 1.4 ps .95 t0 0.005
    SDR - Average Surround
    Lp 100 Lw 100 Lg 10.5 c 1.4 ps .9 t0 0.006
    Rec.2100 PQ ST-2084 600 nit
    Lp 10000 Lw 600 Lg 15 c 1.2 ps 1 t0 0.002
    Rec.2100 PQ ST-2084 1000 nit
    Lp 10000 Lw 1000 Lg 15 c 1.2 ps 1 t0 0.001
    Rec.2100 PQ ST-2084 2000 nit
    Lp 10000 Lw 2000 Lg 15 c 1.2 ps 1 t0 0.0006
    Rec.2100 PQ ST-2084 4000 nit
    Lp 10000 Lw 4000 Lg 15 c 1.2 ps 1 t0 0.0002
*/

kernel Tonemap_PiecewiseHyperbolic : public ImageComputationKernel<ePixelWise> {
  Image<eRead, eAccessPoint, eEdgeClamped> src;
  Image<eWrite> dst;

  param:
    float Lp;
    float Lw;
    float Lg;
    float c;
    float ps;
    float t0;
    bool invert;

  local:
    float th;
    float p;
    float2 g;
    float w;
    float h;
    float2 s;

  void init() {
    th = Lg / Lw;
    p = c * ps;
    g = float2(0.18f, Lg / Lp);
    h = 0.048 * Lw / 1000 + 1.033;
    s.y = Lw / Lp * h;
    float gi = pow(g.y / s.y, 1.0f / c);
    w = th > gi ? gi / g.x : (2.0f * th * gi - gi - th * th) / (g.x * (gi - 1.0f));
    s.x = w * max(1.0f, pow(Lw / 1000.0f, 0.1f));
  }

  void process() {
    float3 rgb = float3(src().x, src().y, src().z);

    if (!invert) {
      // input scale -> shoulder compression -> contrast -> toe -> output scale
      rgb = rgb * s.x;
      rgb.x = rgb.x > th ? th + 1.0f / (1.0f / (rgb.x - th) + 1.0f / (1.0f - th)) : rgb.x;
      rgb.y = rgb.y > th ? th + 1.0f / (1.0f / (rgb.y - th) + 1.0f / (1.0f - th)) : rgb.y;
      rgb.z = rgb.z > th ? th + 1.0f / (1.0f / (rgb.z - th) + 1.0f / (1.0f - th)) : rgb.z;
      rgb = pow(rgb, (float3)p);
      rgb = (rgb * rgb) / (rgb + t0);
      rgb = rgb * s.y;
    } else {
      // inverse output scale -> inverse toe -> inverse contrast -> inverse shoulder -> inverse input scale
      rgb = rgb / s.y;
      rgb = (rgb + sqrt(rgb * (4.0f * t0 + rgb)))/2.0f;
      rgb = pow(rgb, (float3)1.0f/p);
      rgb.x = rgb.x > th ? th + 1.0f / (1.0f / (rgb.x - th) - 1.0f / (1.0f - th)) : rgb.x;
      rgb.y = rgb.y > th ? th + 1.0f / (1.0f / (rgb.y - th) - 1.0f / (1.0f - th)) : rgb.y;
      rgb.z = rgb.z > th ? th + 1.0f / (1.0f / (rgb.z - th) - 1.0f / (1.0f - th)) : rgb.z;
      rgb = rgb / s.x;
    }

    dst() = float4(rgb.x, rgb.y, rgb.z, src().w);
  }
};