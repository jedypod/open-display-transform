/* Electro-Optical Transfer Function 
    by Jed Smith - v0.0.1
    
    Calculates and applies a forward or inverse EOTF. Supported transfer functions:
      eotf settings
      0. Linear | No-op
      1. sRGB Display | Pure 2.2 power function
      2. Rec.1886 | Pure 2.4 power function
      3. DCI Cinema | Pure 2.6 power function
      4. Rec.2100 ST-2084 PQ | Perceptual quantizer EOTF
      5. Rec.2100 HLG | Hybrid Log-Gamma transfer function, including full surround compensation model

    References
    ------------------
    Image parameter values for high dynamic range television for use in production and international programme exchange  
      https://www.itu.int/rec/R-REC-BT.2100
    High dynamic range television for production and international programme exchange 
      https://www.itu.int/pub/R-REP-BT.2390
    Perceptual Quantiser (PQ) to Hybrid Log-Gamma (HLG) Transcoding
      https://www.bbc.co.uk/rd/sites/50335ff370b5c262af000004/assets/592eea8006d63e5e5200f90d/BBC_HDRTV_PQ_HLG_Transcode_v2.pdf
    Guidance for operational practices in HDR television production  
      https://www.itu.int/pub/R-REP-BT.2408
*/

kernel EOTF : public ImageComputationKernel<ePixelWise> {
  Image<eRead, eAccessPoint, eEdgeClamped> src;
  Image<eWrite> dst;

  param:
    int eotf;
    float PQ_Lw; // PQ_Lw should be set to 10,000
    float HLG_Lw; // HLG_Lw should be set to 1,000
    float HLG_Lb; // Assumed to be 0.0
    float HLG_Ls; // Ambient surround illuminantion in nits. Default for HLG is 5.0
    bool invert;
  
  local:
    float m1;
    float m2;
    float c1;
    float c2;
    float c3;
    float a;
    float b;
    float c;
    float g;


  void init() {
    // ST2084 Constants
    m1 = 2610.0f / 4096.0f * (1.0f / 4.0f);
    m2 = 2523.0f / 4096.0f * 128.0f;
    c1 = 107.0f / 128.0f;
    c2 = 2413.0f / 128.0f;
    c3 = 2392.0f / 128.0f;
    
    // HLG Constants
    a = 0.17883277f;
    b = 1.0f - 4.0f * a;
    c = 0.5f - a * log(4.0f * a);
    g = 1.2f * pow(1.111f, log2(HLG_Lw / 1000)) * pow(0.98f, log2(max(1e-6f, HLG_Ls) / 5.0f));
  }

  void process() {
    float3 rgb = float3(src().x, src().y, src().z);
    float p = 2.0f + (float)eotf * 0.2f;
    if ((eotf > 0) && (eotf < 4)) { // Power Function
      if (!invert) {
        rgb = pow(rgb, (float3)p);
      } else {
        rgb = pow(rgb, (float3)1.0f / p);
      }
    } else if (eotf == 4) { // ST2084 PQ
      if (!invert) {
        rgb = pow((pow(rgb, (float3)1.0f / m2) - c1) / (c2 - c3 * pow(rgb, (float3)1.0f / m2)), (float3) 1.0f / m1) * 10000.0f / PQ_Lw;
      } else {
        rgb = pow((c1 + c2 * pow(rgb * PQ_Lw / 10000.0f, (float3)m1))/(1.0f + c3 * pow(rgb * PQ_Lw / 10000.0f, (float3)m1)), (float3)m2);
      }
    } else if (eotf == 5) { // HLG
      float Ys = 0.2627f * rgb.x + 0.6780f * rgb.y + 0.0593f * rgb.z;
      if (!invert) {
        // HLG Inverse OETF
        rgb.x = rgb.x <= 0.5f ? (rgb.x * rgb.x) / 3.0f : (exp((rgb.x - c)/ a) + b) / 12.0f;
        rgb.y = rgb.y <= 0.5f ? (rgb.y * rgb.y) / 3.0f : (exp((rgb.y - c)/ a) + b) / 12.0f;
        rgb.z = rgb.z <= 0.5f ? (rgb.z * rgb.z) / 3.0f : (exp((rgb.z - c)/ a) + b) / 12.0f;
        // HLG OOTF
        rgb = rgb * pow(Ys, g - 1.0f);
      } else {
        // HLG Inverse OOTF
        rgb = rgb * pow(Ys, (1.0f - g) / g);
        // HLG OETF
        rgb.x = rgb.x <= 1.0f / 12.0f ? sqrt(3.0f * rgb.x) : a * log(12.0f * rgb.x - b) + c;
        rgb.y = rgb.y <= 1.0f / 12.0f ? sqrt(3.0f * rgb.y) : a * log(12.0f * rgb.y - b) + c;
        rgb.z = rgb.z <= 1.0f / 12.0f ? sqrt(3.0f * rgb.z) : a * log(12.0f * rgb.z - b) + c;
      }
    }

    dst() = float4(rgb.x, rgb.y, rgb.z, src().w);
  }
};