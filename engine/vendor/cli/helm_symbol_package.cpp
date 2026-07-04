#include "helm_symbol_package.h"

#include <cerrno>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <map>
#include <sstream>

namespace helm {
namespace symbols {
namespace {

struct Json {
  enum Type { NIL, BOOL, NUMBER, STRING, ARRAY, OBJECT };
  Type type = NIL;
  bool boolean = false;
  double number = 0.0;
  std::string string;
  std::vector<Json> array;
  std::map<std::string, Json> object;
};

class Parser {
 public:
  explicit Parser(const std::string &text) : text_(text) {}

  bool Parse(Json *out, std::string *error) {
    SkipWs();
    if (!ParseValue(out, error)) return false;
    SkipWs();
    if (pos_ != text_.size()) {
      if (error) *error = "unexpected trailing JSON at byte " + ToString(pos_);
      return false;
    }
    return true;
  }

 private:
  static std::string ToString(size_t value) {
    std::ostringstream ss;
    ss << value;
    return ss.str();
  }

  void SkipWs() {
    while (pos_ < text_.size() &&
           std::isspace(static_cast<unsigned char>(text_[pos_]))) {
      ++pos_;
    }
  }

  bool Consume(char expected) {
    if (pos_ < text_.size() && text_[pos_] == expected) {
      ++pos_;
      return true;
    }
    return false;
  }

  bool ParseValue(Json *out, std::string *error) {
    SkipWs();
    if (pos_ >= text_.size()) {
      if (error) *error = "unexpected end of JSON";
      return false;
    }
    const char c = text_[pos_];
    if (c == '"') return ParseString(out, error);
    if (c == '{') return ParseObject(out, error);
    if (c == '[') return ParseArray(out, error);
    if (c == '-' || std::isdigit(static_cast<unsigned char>(c))) {
      return ParseNumber(out, error);
    }
    if (MatchLiteral("true")) {
      out->type = Json::BOOL;
      out->boolean = true;
      return true;
    }
    if (MatchLiteral("false")) {
      out->type = Json::BOOL;
      out->boolean = false;
      return true;
    }
    if (MatchLiteral("null")) {
      out->type = Json::NIL;
      return true;
    }
    if (error) *error = "unexpected JSON value at byte " + ToString(pos_);
    return false;
  }

  bool MatchLiteral(const char *literal) {
    size_t start = pos_;
    for (const char *p = literal; *p; ++p) {
      if (pos_ >= text_.size() || text_[pos_] != *p) {
        pos_ = start;
        return false;
      }
      ++pos_;
    }
    return true;
  }

  bool ParseString(Json *out, std::string *error) {
    if (!Consume('"')) return false;
    std::string value;
    while (pos_ < text_.size()) {
      char c = text_[pos_++];
      if (c == '"') {
        out->type = Json::STRING;
        out->string = value;
        return true;
      }
      if (c != '\\') {
        value += c;
        continue;
      }
      if (pos_ >= text_.size()) {
        if (error) *error = "unterminated JSON escape";
        return false;
      }
      char e = text_[pos_++];
      switch (e) {
        case '"': value += '"'; break;
        case '\\': value += '\\'; break;
        case '/': value += '/'; break;
        case 'b': value += '\b'; break;
        case 'f': value += '\f'; break;
        case 'n': value += '\n'; break;
        case 'r': value += '\r'; break;
        case 't': value += '\t'; break;
        case 'u':
          if (pos_ + 4 > text_.size()) {
            if (error) *error = "short JSON unicode escape";
            return false;
          }
          if (error) *error = "unicode JSON escape is not supported by symbol package loader";
          return false;
        default:
          if (error) *error = "unsupported JSON escape";
          return false;
      }
    }
    if (error) *error = "unterminated JSON string";
    return false;
  }

  bool ParseNumber(Json *out, std::string *error) {
    size_t start = pos_;
    if (text_[pos_] == '-') ++pos_;
    while (pos_ < text_.size() &&
           std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
      ++pos_;
    }
    if (pos_ < text_.size() && text_[pos_] == '.') {
      ++pos_;
      while (pos_ < text_.size() &&
             std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
        ++pos_;
      }
    }
    if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
      ++pos_;
      if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) {
        ++pos_;
      }
      while (pos_ < text_.size() &&
             std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
        ++pos_;
      }
    }
    errno = 0;
    char *end = nullptr;
    const std::string raw = text_.substr(start, pos_ - start);
    double value = std::strtod(raw.c_str(), &end);
    if (end == raw.c_str() || *end != '\0' || errno == ERANGE) {
      if (error) *error = "invalid JSON number at byte " + ToString(start);
      return false;
    }
    out->type = Json::NUMBER;
    out->number = value;
    return true;
  }

  bool ParseArray(Json *out, std::string *error) {
    if (!Consume('[')) return false;
    out->type = Json::ARRAY;
    SkipWs();
    if (Consume(']')) return true;
    while (true) {
      Json value;
      if (!ParseValue(&value, error)) return false;
      out->array.push_back(value);
      SkipWs();
      if (Consume(']')) return true;
      if (!Consume(',')) {
        if (error) *error = "expected comma in JSON array";
        return false;
      }
    }
  }

  bool ParseObject(Json *out, std::string *error) {
    if (!Consume('{')) return false;
    out->type = Json::OBJECT;
    SkipWs();
    if (Consume('}')) return true;
    while (true) {
      Json key;
      if (!ParseString(&key, error)) return false;
      SkipWs();
      if (!Consume(':')) {
        if (error) *error = "expected colon in JSON object";
        return false;
      }
      Json value;
      if (!ParseValue(&value, error)) return false;
      out->object[key.string] = value;
      SkipWs();
      if (Consume('}')) return true;
      if (!Consume(',')) {
        if (error) *error = "expected comma in JSON object";
        return false;
      }
      SkipWs();
    }
  }

  const std::string &text_;
  size_t pos_ = 0;
};

bool ReadFile(const std::string &path, std::string *body, std::string *error) {
  std::ifstream in(path, std::ios::binary);
  if (!in.good()) {
    if (error) *error = "could not read file: " + path;
    return false;
  }
  std::ostringstream ss;
  ss << in.rdbuf();
  *body = ss.str();
  return true;
}

bool LoadJson(const std::string &path, Json *out, std::string *error) {
  std::string body;
  if (!ReadFile(path, &body, error)) return false;
  Parser parser(body);
  if (!parser.Parse(out, error)) {
    if (error) *error = path + ": " + *error;
    return false;
  }
  return true;
}

const Json *Get(const Json &object, const std::string &key) {
  if (object.type != Json::OBJECT) return nullptr;
  std::map<std::string, Json>::const_iterator it = object.object.find(key);
  return it == object.object.end() ? nullptr : &it->second;
}

std::string StringValue(const Json *value, const std::string &default_value = "") {
  return value && value->type == Json::STRING ? value->string : default_value;
}

bool BoolValue(const Json *value, bool default_value = false) {
  return value && value->type == Json::BOOL ? value->boolean : default_value;
}

bool RequireString(const Json &object,
                   const std::string &key,
                   std::string *out,
                   std::string *error) {
  const Json *value = Get(object, key);
  if (!value || value->type != Json::STRING) {
    if (error) *error = "missing required string field: " + key;
    return false;
  }
  *out = value->string;
  return true;
}

bool RequireArray(const Json &object,
                  const std::string &key,
                  const Json **out,
                  std::string *error) {
  const Json *value = Get(object, key);
  if (!value || value->type != Json::ARRAY) {
    if (error) *error = "missing required array field: " + key;
    return false;
  }
  *out = value;
  return true;
}

bool RequireObject(const Json &object,
                   const std::string &key,
                   const Json **out,
                   std::string *error) {
  const Json *value = Get(object, key);
  if (!value || value->type != Json::OBJECT) {
    if (error) *error = "missing required object field: " + key;
    return false;
  }
  *out = value;
  return true;
}

bool RequireBool(const Json &object,
                 const std::string &key,
                 bool *out,
                 std::string *error) {
  const Json *value = Get(object, key);
  if (!value || value->type != Json::BOOL) {
    if (error) *error = "missing required boolean field: " + key;
    return false;
  }
  *out = value->boolean;
  return true;
}

bool RequireInt(const Json &object,
                const std::string &key,
                int *out,
                std::string *error) {
  const Json *value = Get(object, key);
  if (!value || value->type != Json::NUMBER) {
    if (error) *error = "missing required number field: " + key;
    return false;
  }
  *out = static_cast<int>(value->number);
  return true;
}

std::vector<std::string> StringArray(const Json *value) {
  std::vector<std::string> out;
  if (!value || value->type != Json::ARRAY) return out;
  for (const Json &item : value->array) {
    if (item.type == Json::STRING) out.push_back(item.string);
  }
  return out;
}

std::map<std::string, int> IntMap(const Json *value) {
  std::map<std::string, int> out;
  if (!value || value->type != Json::OBJECT) return out;
  for (std::map<std::string, Json>::const_iterator it = value->object.begin();
       it != value->object.end(); ++it) {
    if (it->second.type == Json::NUMBER) {
      out[it->first] = static_cast<int>(it->second.number);
    }
  }
  return out;
}

bool ProofIndex(const Json &manifest,
                std::map<std::string, const Json *> *out,
                std::string *error) {
  const Json *symbols = nullptr;
  if (!RequireArray(manifest, "symbols", &symbols, error)) return false;
  for (const Json &row : symbols->array) {
    if (row.type != Json::OBJECT) {
      if (error) *error = "proof manifest symbols must be objects";
      return false;
    }
    std::string symbol_id;
    if (!RequireString(row, "symbol_id", &symbol_id, error)) return false;
    if (!symbol_id.empty()) {
      if (out->find(symbol_id) != out->end()) {
        if (error) *error = "duplicate proof manifest symbol_id: " + symbol_id;
        return false;
      }
      (*out)[symbol_id] = &row;
    }
  }
  return true;
}

SourceEvidence ParseSourceEvidence(const Json &item) {
  SourceEvidence out;
  out.reason_code = StringValue(Get(item, "reason_code"));
  out.blocker_category = StringValue(Get(item, "blocker_category"));
  out.source_layer = StringValue(Get(item, "source_layer"));
  const Json *evidence = Get(item, "evidence");
  out.path = StringValue(Get(evidence ? *evidence : item, "path"));
  out.sha256 = StringValue(Get(evidence ? *evidence : item, "sha256"));
  out.parse_status = StringValue(Get(evidence ? *evidence : item, "parse_status"));
  out.feature_type = StringValue(Get(evidence ? *evidence : item, "feature_type"));
  out.rule_file = StringValue(Get(evidence ? *evidence : item, "rule_file"));
  out.gate_name = StringValue(Get(evidence ? *evidence : item, "gate_name"));
  out.gate_status = StringValue(Get(evidence ? *evidence : item, "gate_status"));
  return out;
}

const Json *ObjectChild(const Json *object, const std::string &key) {
  if (!object || object->type != Json::OBJECT) return nullptr;
  return Get(*object, key);
}

void ApplyProofMetadata(const Json *proof, SymbolRecord *record) {
  if (!proof) return;
  record->proof_manifest_present = true;
  record->kind = StringValue(Get(*proof, "kind"));
  record->name = StringValue(Get(*proof, "name"));
  record->family = StringValue(Get(*proof, "family"));
  record->package_status = StringValue(Get(*proof, "status"));
  const Json *qa = Get(*proof, "qa");
  record->proof_final_approved = BoolValue(ObjectChild(qa, "final_approved"));
  const Json *runtime = Get(*proof, "chartplotter_runtime");
  record->chartplotter_runtime_eligible = BoolValue(ObjectChild(runtime, "eligible"));
  const Json *standards = Get(*proof, "standards_mappings");
  const Json *crosswalk = ObjectChild(standards, "s101_crosswalk_classification");
  record->runtime_scope = StringValue(ObjectChild(crosswalk, "runtime_scope"));
  const Json *boundary = Get(*proof, "clean_room_boundary");
  if (boundary && boundary->type == Json::OBJECT) {
    record->clean_room_generated =
        BoolValue(Get(*boundary, "generated_owned_candidate"));
    record->comparison_refs_only =
        BoolValue(Get(*boundary, "comparison_refs_only"));
    record->third_party_artwork_not_source =
        BoolValue(Get(*boundary, "third_party_artwork_not_source"));
  }
}

std::vector<std::string> RuntimeApprovalBlockReasons(const SymbolRecord &record) {
  std::vector<std::string> reasons;
  if (!record.proof_manifest_present) {
    reasons.push_back("proof_manifest_missing");
  }
  if (record.package_status != "accepted") {
    reasons.push_back("package_status_not_accepted");
  }
  if (!record.proof_final_approved) {
    reasons.push_back("final_approved_false");
  }
  if (!record.chartplotter_runtime_eligible) {
    reasons.push_back("chartplotter_runtime_not_eligible");
  }
  if (record.runtime_state != "runtime_eligible") {
    reasons.push_back("runtime_state_not_eligible");
  }
  if (record.candidate_status != "runtime_eligible") {
    reasons.push_back("candidate_status_not_eligible");
  }
  if (!record.runtime_eligible_db) {
    reasons.push_back("runtime_eligible_db_false");
  }
  if (record.fail_closed) {
    reasons.push_back("fail_closed_true");
  }
  if (!record.clean_room_generated) {
    reasons.push_back("clean_room_generated_false");
  }
  if (!record.third_party_artwork_not_source) {
    reasons.push_back("third_party_artwork_boundary_missing");
  }
  if (record.runtime_scope.empty()) {
    reasons.push_back("runtime_scope_missing");
  }
  return reasons;
}

bool ParseSnapshotRow(const Json &row,
                      const Json *proof,
                      SymbolRecord *record,
                      std::string *error) {
  if (!RequireString(row, "symbol_id", &record->symbol_id, error)) return false;
  if (!RequireInt(row, "row_id", &record->row_id, error)) return false;
  if (!RequireString(row, "row_key", &record->row_key, error)) return false;
  record->helm_catalog_id = StringValue(Get(row, "helm_catalog_id"));
  if (!RequireString(row, "runtime_state", &record->runtime_state, error)) return false;
  if (!RequireString(row, "candidate_status", &record->candidate_status, error)) {
    return false;
  }
  if (!RequireBool(row, "runtime_eligible_db", &record->runtime_eligible_db, error)) {
    return false;
  }
  if (!RequireBool(row, "fail_closed", &record->fail_closed, error)) return false;

  const Json *s57 = nullptr;
  const Json *s52 = nullptr;
  const Json *s101 = nullptr;
  if (!RequireObject(row, "s57", &s57, error)) return false;
  if (!RequireObject(row, "s52", &s52, error)) return false;
  if (!RequireObject(row, "s101", &s101, error)) return false;
  if (!RequireString(*s57, "object_class", &record->s57_object_class, error)) return false;
  if (!RequireString(*s57, "geometry", &record->s57_geometry, error)) return false;
  if (!RequireString(*s52, "instruction", &record->s52_instruction, error)) return false;
  if (!RequireString(*s52, "ast_status", &record->s52_ast_status, error)) return false;
  record->s101_mapping_type = StringValue(Get(*s101, "mapping_type"));
  record->s101_crosswalk_class = StringValue(Get(*s101, "crosswalk_class"));
  record->s101_feature_type = StringValue(Get(*s101, "feature_type"));
  record->s101_rule_file = StringValue(Get(*s101, "rule_file"));

  const Json *blocker_categories = nullptr;
  const Json *runtime_effects = nullptr;
  const Json *reason_codes = nullptr;
  const Json *remediation_hints = nullptr;
  const Json *evidence = nullptr;
  if (!RequireObject(row, "blocker_categories", &blocker_categories, error)) return false;
  if (!RequireObject(row, "runtime_effects", &runtime_effects, error)) return false;
  if (!RequireArray(row, "runtime_gate_reason_codes", &reason_codes, error)) return false;
  if (!RequireArray(row, "remediation_hints", &remediation_hints, error)) return false;
  if (!RequireArray(row, "authority_source_evidence", &evidence, error)) return false;
  record->blocker_categories = IntMap(blocker_categories);
  record->runtime_effects = IntMap(runtime_effects);
  record->runtime_gate_reason_codes = StringArray(reason_codes);
  record->remediation_hints = StringArray(remediation_hints);
  for (const Json &item : evidence->array) {
    if (item.type == Json::OBJECT) {
      record->authority_source_evidence.push_back(ParseSourceEvidence(item));
    }
  }

  ApplyProofMetadata(proof, record);
  record->runtime_approval_block_reasons =
      RuntimeApprovalBlockReasons(*record);
  record->runtime_approved = record->runtime_approval_block_reasons.empty();
  record->runtime_eligible_default =
      record->runtime_approved &&
      record->runtime_scope == "chart_portrayal";
  return true;
}

}  // namespace

bool LoadSymbolPackage(const std::string &runtime_evidence_snapshot_path,
                       const std::string &proof_manifest_path,
                       SymbolPackage *package,
                       std::string *error) {
  if (!package) {
    if (error) *error = "package output is null";
    return false;
  }
  *package = SymbolPackage();
  Json snapshot;
  Json manifest;
  if (!LoadJson(runtime_evidence_snapshot_path, &snapshot, error)) return false;
  if (!LoadJson(proof_manifest_path, &manifest, error)) return false;

  if (!RequireString(snapshot, "schema", &package->snapshot_schema, error)) return false;
  if (!RequireString(snapshot, "status", &package->snapshot_status, error)) return false;
  if (!RequireString(manifest, "schema", &package->manifest_schema, error)) return false;
  if (!RequireString(manifest, "status", &package->manifest_status, error)) return false;
  if (package->snapshot_schema != "helm.iconforge.runtime_evidence_snapshot.v1") {
    if (error) *error = "unsupported runtime evidence schema: " + package->snapshot_schema;
    return false;
  }
  if (package->snapshot_status != "snapshot_ready") {
    if (error) *error = "runtime evidence snapshot is not ready: " + package->snapshot_status;
    return false;
  }
  if (package->manifest_schema != "helm.symbol.cleanroom-package.v1") {
    if (error) *error = "unsupported proof manifest schema: " + package->manifest_schema;
    return false;
  }

  const Json *summary = nullptr;
  if (!RequireObject(snapshot, "summary", &summary, error)) return false;
  if (!RequireInt(*summary, "snapshot_rows", &package->snapshot_rows, error)) return false;
  if (!RequireInt(*summary, "runtime_rows", &package->runtime_rows, error)) return false;
  if (!RequireInt(*summary, "hard_pile_rows", &package->hard_pile_rows, error)) return false;
  if (!RequireInt(*summary, "warning_only_rows", &package->warning_only_rows, error)) {
    return false;
  }
  if (!RequireBool(*summary,
                   "matches_runtime_promotion_gate",
                   &package->matches_runtime_promotion_gate,
                   error)) {
    return false;
  }
  if (!package->matches_runtime_promotion_gate) {
    if (error) *error = "runtime evidence snapshot does not match promotion gate";
    return false;
  }

  const Json *rows = nullptr;
  if (!RequireArray(snapshot, "rows", &rows, error)) return false;
  std::map<std::string, const Json *> proof;
  if (!ProofIndex(manifest, &proof, error)) return false;
  package->records.reserve(rows->array.size());
  for (const Json &row : rows->array) {
    if (row.type != Json::OBJECT) {
      if (error) *error = "runtime evidence rows must be objects";
      return false;
    }
    SymbolRecord record;
    const std::string symbol_id = StringValue(Get(row, "symbol_id"));
    std::map<std::string, const Json *>::const_iterator found = proof.find(symbol_id);
    if (!ParseSnapshotRow(row, found == proof.end() ? nullptr : found->second,
                          &record, error)) {
      return false;
    }
    package->records.push_back(record);
  }

  for (const SymbolRecord &record : package->records) {
    if (record.runtime_eligible_default) {
      package->default_render_records.push_back(&record);
    } else {
      package->diagnostic_records.push_back(&record);
    }
  }
  return true;
}

const SymbolRecord *FindSymbol(const SymbolPackage &package,
                               const std::string &symbol_id,
                               bool include_diagnostics) {
  for (const SymbolRecord &record : package.records) {
    if (record.symbol_id != symbol_id) continue;
    if (include_diagnostics || record.runtime_eligible_default) return &record;
  }
  return nullptr;
}

const SymbolRecord *FindSymbolForScope(const SymbolPackage &package,
                                       const std::string &symbol_id,
                                       const std::string &runtime_scope,
                                       bool include_diagnostics) {
  for (const SymbolRecord &record : package.records) {
    if (record.symbol_id != symbol_id) continue;
    if (record.runtime_scope != runtime_scope) continue;
    if (include_diagnostics || record.runtime_approved) return &record;
  }
  return nullptr;
}

}  // namespace symbols
}  // namespace helm
