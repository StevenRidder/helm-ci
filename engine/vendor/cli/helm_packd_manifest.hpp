// helm_packd_manifest.hpp - /layer-manifest (helm.layer.manifest.v1) builders for helm-packd.
//
// Implementation fragment #included exactly once by helm_packd.cpp, at the point where its
// dependencies are already defined (JsonValue/JsonAllocator aliases, add_string*, rj_string,
// rj_object, rj_int64, iso_from_epoch, epoch_from_iso, stat_file, load_json_document,
// load_sidecar_metadata, geojson_bbox, user_data_root). This is NOT a standalone header - it is
// split out only to keep helm_packd.cpp within the HELMC++ maintainability line budget
// (scripts/helmcxx-maintainability-audit.mjs).
#pragma once

JsonValue manifest_source_json(const JsonValue& doc, const JsonValue* sidecar,
                               const std::string& default_label, const std::string& default_license,
                               JsonAllocator& a) {
  JsonValue source(rapidjson::kObjectType);
  const JsonValue* sidecar_source = sidecar ? rj_object(*sidecar, "source") : nullptr;
  const JsonValue* metadata = rj_object(doc, "metadata");
  const JsonValue* meta_source = metadata ? rj_object(*metadata, "source") : nullptr;
  const JsonValue* candidates[] = {sidecar_source, meta_source};
  const char* allowed_keys[] = {"label", "license", "id"};
  for (const JsonValue* candidate : candidates) {
    if (!candidate || !candidate->IsObject()) continue;
    JsonValue allowed(rapidjson::kObjectType);
    for (const char* key : allowed_keys) {
      if (candidate->HasMember(key) && !(*candidate)[key].IsNull()) {
        copy_public_value(allowed, key, (*candidate)[key], a);
      }
    }
    if (allowed.MemberCount() > 0) return allowed;
  }
  if (metadata && metadata->HasMember("source") && (*metadata)["source"].IsString()) {
    const std::string label = (*metadata)["source"].GetString();
    add_string_allow_empty(source, "label", label, a);
    add_string_allow_empty(source, "license", label == "enc" ? "enc-local" : default_license, a);
    const std::string cell = rj_string(*metadata, "cell");
    if (!cell.empty()) add_string_allow_empty(source, "id", cell, a);
    return source;
  }
  add_string_allow_empty(source, "label", default_label, a);
  add_string_allow_empty(source, "license", default_license, a);
  return source;
}

JsonValue manifest_freshness_json(const std::string& path, const JsonValue* sidecar, JsonAllocator& a) {
  JsonValue freshness(rapidjson::kObjectType);
  const JsonValue* sidecar_freshness = sidecar ? rj_object(*sidecar, "freshness") : nullptr;
  std::string status = sidecar_freshness ? rj_string(*sidecar_freshness, "status", "ok") : "ok";

  const std::int64_t now = static_cast<std::int64_t>(std::time(nullptr));
  struct stat st {};
  const bool have_stat = stat_file(path, st);
  std::string updated;
  if (have_stat) updated = iso_from_epoch(static_cast<std::uint64_t>(st.st_mtime));

  // Age is measured from an explicit sidecar render_date when present, else the file mtime.
  const std::string render_date = sidecar_freshness ? rj_string(*sidecar_freshness, "render_date", "") : "";
  std::int64_t ref_epoch = 0;
  bool have_ref = !render_date.empty() && epoch_from_iso(render_date, ref_epoch);
  if (!have_ref && have_stat) { ref_epoch = static_cast<std::int64_t>(st.st_mtime); have_ref = true; }

  // A layer is "stale" only when its sidecar declares a window (stale_at, or
  // render_date + stale_after_days) and that deadline has passed. Otherwise the file
  // presence status ("ok"/sidecar override) stands — we never fabricate staleness.
  std::int64_t stale_at_epoch = 0;
  std::string stale_at;
  bool have_deadline = false;
  if (sidecar_freshness) {
    stale_at = rj_string(*sidecar_freshness, "stale_at", "");
    have_deadline = !stale_at.empty() && epoch_from_iso(stale_at, stale_at_epoch);
    std::int64_t stale_after = 0;
    if (!have_deadline && !render_date.empty() && rj_int64(*sidecar_freshness, "stale_after_days", stale_after) &&
        stale_after > 0 && epoch_from_iso(render_date, ref_epoch)) {
      stale_at_epoch = ref_epoch + stale_after * 86400;
      have_deadline = true;
      stale_at = iso_from_epoch(static_cast<std::uint64_t>(stale_at_epoch));
    }
  }
  const bool computed_stale = have_deadline && now >= stale_at_epoch;
  // An expired window is stale regardless of a non-forced sidecar status — matches the
  // /catalog staleness rule so the two surfaces never disagree for the same input.
  if (computed_stale) status = "stale";

  add_string_allow_empty(freshness, "status", status, a);
  add_string(freshness, "updated", updated, a);
  if (have_ref) {
    std::int64_t age_days = (now - ref_epoch) / 86400;
    if (age_days < 0) age_days = 0;
    freshness.AddMember("age_days", age_days, a);
  }
  add_string(freshness, "stale_at", stale_at, a);
  if (computed_stale) {
    add_string(freshness, "warning", "Layer render date is older than the configured freshness window.", a);
  }
  return freshness;
}

JsonValue manifest_inspection_json(const JsonValue* sidecar, JsonAllocator& a) {
  JsonValue inspection(rapidjson::kObjectType);
  const JsonValue* sidecar_inspection = sidecar ? rj_object(*sidecar, "inspection") : nullptr;
  if (sidecar_inspection) {
    copy_public_object(inspection, *sidecar_inspection, a);
  }
  if (!inspection.HasMember("mode")) add_string_allow_empty(inspection, "mode", "feature-properties", a);
  return inspection;
}

bool append_manifest_geojson_layer(JsonValue& layers, const std::string& root, const std::string& rel_path,
                                   const std::string& layer_id, const std::string& title,
                                   const std::string& kind, const std::string& tier,
                                   const std::string& default_label, const std::string& default_license,
                                   JsonAllocator& a) {
  const std::string path = root + "/" + rel_path;
  struct stat st {};
  if (!stat_file(path, st) || !S_ISREG(st.st_mode)) return false;
  auto doc = load_json_document(path);
  if (!doc) return false;
  auto sidecar = load_sidecar_metadata(path);
  const JsonValue* sidecar_obj = sidecar.get();
  const std::string stem = basename_no_ext(rel_path.substr(rel_path.find_last_of('/') + 1));
  JsonValue layer(rapidjson::kObjectType);
  add_string_allow_empty(layer, "id", sidecar_obj ? rj_string(*sidecar_obj, "id", layer_id.empty() ? stem : layer_id) : (layer_id.empty() ? stem : layer_id), a);
  add_string_allow_empty(layer, "title", sidecar_obj ? rj_string(*sidecar_obj, "title", title.empty() ? stem : title) : (title.empty() ? stem : title), a);
  add_string_allow_empty(layer, "kind", sidecar_obj ? rj_string(*sidecar_obj, "kind", kind.empty() ? "geojson" : kind) : (kind.empty() ? "geojson" : kind), a);
  add_string(layer, "format", "geojson", a);
  std::string resolved_tier = sidecar_obj ? rj_string(*sidecar_obj, "tier", tier.empty() ? "overlay" : tier) : (tier.empty() ? "overlay" : tier);
  if (resolved_tier != "basemap" && resolved_tier != "enc" && resolved_tier != "overlay" &&
      resolved_tier != "weather" && resolved_tier != "nav") {
    resolved_tier = "overlay";
  }
  add_string_allow_empty(layer, "tier", resolved_tier, a);
  add_string(layer, "url", "/user-data/" + rel_path, a);
  const std::vector<double> bbox = geojson_bbox(*doc, sidecar_obj);
  if (!bbox.empty()) {
    JsonValue bbox_json(rapidjson::kArrayType);
    for (double v : bbox) bbox_json.PushBack(v, a);
    layer.AddMember("bbox", bbox_json, a);
  }
  layer.AddMember("source", manifest_source_json(*doc, sidecar_obj, default_label, default_license, a), a);
  layer.AddMember("freshness", manifest_freshness_json(path, sidecar_obj, a), a);
  layer.AddMember("inspection", manifest_inspection_json(sidecar_obj, a), a);
  layers.PushBack(layer, a);
  return true;
}

JsonValue layer_manifest_value(JsonAllocator& a) {
  JsonValue manifest(rapidjson::kObjectType);
  add_string_allow_empty(manifest, "schema", "helm.layer.manifest.v1", a);
  JsonValue layers(rapidjson::kArrayType);
  const std::string root = user_data_root();
  struct EncLayerSpec {
    const char* stem;
    const char* kind;
    const char* tier;
    const char* title;
  };
  static const EncLayerSpec enc_layers[] = {
    {"depare", "polygons", "enc", "Depth areas"},
    {"depcnt", "lines", "enc", "Depth contours"},
    {"soundg", "points", "enc", "Soundings"},
  };
  JsonValue enc_expected(rapidjson::kArrayType);
  JsonValue enc_present(rapidjson::kArrayType);
  JsonValue enc_missing(rapidjson::kArrayType);
  for (const EncLayerSpec& spec : enc_layers) {
    const bool present = append_manifest_geojson_layer(layers, root, std::string(spec.stem) + ".geojson",
                                  spec.stem, spec.title, spec.kind, spec.tier, "enc", "enc-local", a);
    JsonValue e1(spec.stem, a);
    enc_expected.PushBack(e1, a);
    JsonValue e2(spec.stem, a);
    (present ? enc_present : enc_missing).PushBack(e2, a);
  }
  const std::string overlay_dir = root + "/layers";
  DIR* dir = ::opendir(overlay_dir.c_str());
  if (dir) {
    std::vector<std::string> names;
    while (dirent* ent = ::readdir(dir)) {
      const std::string filename = ent->d_name;
      if (filename.empty() || filename[0] == '.') continue;
      if (extension_of(filename) != ".geojson") continue;
      names.push_back(filename);
    }
    ::closedir(dir);
    std::sort(names.begin(), names.end());
    for (const std::string& filename : names) {
      append_manifest_geojson_layer(layers, root, "layers/" + filename, "", "", "", "overlay", "owned", "private-local", a);
    }
  }
  manifest.AddMember("layers", layers, a);
  // Honest coverage of the expected ENC layer set so CAT-2 can surface an "enc gap"
  // without inventing placeholder layers. present + missing partition expected.
  JsonValue enc(rapidjson::kObjectType);
  enc.AddMember("expected", enc_expected, a);
  enc.AddMember("present", enc_present, a);
  enc.AddMember("missing", enc_missing, a);
  manifest.AddMember("enc", enc, a);
  return manifest;
}
