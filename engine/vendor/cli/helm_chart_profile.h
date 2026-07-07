// ENC-3 — selective OpenCPN PNG profiles via ?profile=depth|aids|standard on /chart tiles.
#pragma once

#include <string>
#include <vector>

#include "s52plib.h"

enum class EncPngProfile { Standard, Depth, Aids };

static inline const char* enc_png_profile_name(EncPngProfile p) {
  switch (p) {
    case EncPngProfile::Depth: return "depth";
    case EncPngProfile::Aids: return "aids";
    default: return "standard";
  }
}

static inline EncPngProfile enc_png_profile_from_query(const std::string& uri) {
  const auto q = uri.find("profile=");
  if (q != std::string::npos) {
    std::string v = uri.substr(q + 8);
    const auto amp = v.find('&');
    if (amp != std::string::npos) v.erase(amp);
    if (v.rfind("depth", 0) == 0) return EncPngProfile::Depth;
    if (v.rfind("aids", 0) == 0) return EncPngProfile::Aids;
    if (v.rfind("standard", 0) == 0) return EncPngProfile::Standard;
  }
  return EncPngProfile::Standard;
}

struct EncPngProfileState {
  EncPngProfile applied = EncPngProfile::Standard;
  std::vector<std::string> noshow;
  bool soundings_off = false;
  bool lights_off = false;
};

static inline void enc_png_noshow(s52plib* lib, EncPngProfileState* st, const char* obj) {
  if (!lib || !st || !obj || !*obj) return;
  lib->AddObjNoshow(obj);
  st->noshow.emplace_back(obj);
}

static inline void enc_png_profile_clear(s52plib* lib, EncPngProfileState* st) {
  if (!lib || !st) return;
  for (const auto& obj : st->noshow) lib->RemoveObjNoshow(obj.c_str());
  st->noshow.clear();
  if (st->soundings_off) {
    lib->SetShowSoundings(true);
    st->soundings_off = false;
  }
  if (st->lights_off) {
    lib->m_lightsOff = false;
    st->lights_off = false;
  }
  st->applied = EncPngProfile::Standard;
}

static inline void enc_png_profile_apply(s52plib* lib, EncPngProfileState* st, EncPngProfile profile) {
  if (!lib || !st) return;
  if (profile == st->applied) return;
  enc_png_profile_clear(lib, st);
  if (profile == EncPngProfile::Depth) {
    static const char* kDepthHide[] = {
      "BOYLAT", "BOYSAW", "BOYSPP", "BOYISD", "BOYINB", "BOYCAR",
      "BCNLAT", "BCNSAW", "BCNSPP", "BCNISD", "BCNINB", "BCNCAR",
      "LIGHTS", "LITFLT", "LITVES", "TOPMAR", "DAYMAR", "FOGSIG", "OBSTRN"
    };
    for (const char* obj : kDepthHide) enc_png_noshow(lib, st, obj);
    lib->m_lightsOff = true;
    st->lights_off = true;
  } else if (profile == EncPngProfile::Aids) {
    static const char* kAidsHide[] = { "DEPARE", "DEPCNT", "SOUNDG", "DRGARE" };
    for (const char* obj : kAidsHide) enc_png_noshow(lib, st, obj);
    lib->SetShowSoundings(false);
    st->soundings_off = true;
  }
  st->applied = profile;
}
