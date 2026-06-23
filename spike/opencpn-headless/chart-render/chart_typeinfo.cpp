// /tmp/opencpn/cli/chart_typeinfo.cpp
//
// Emits ONLY `typeinfo for ChartPlugInWrapper` (Itanium ABI symbol
// __ZTI18ChartPlugInWrapper).
//
// Why this exists:
//   s57chart.cpp contains `dynamic_cast<ChartPlugInWrapper*>(...)` inside the
//   light-sector helper s57_GetVisibleLightSectors(). That helper is NEVER
//   reached on the headless wxDC render path, but the dynamic_cast still emits
//   an undefined reference to ChartPlugInWrapper's RTTI. The real class lives in
//   the BSB chart reader chain (ChartPlugInWrapper : ChartBaseBSB : ChartBase,
//   defined across pluginmanager.cpp + chartimg.cpp), none of which we compile
//   for this spike.
//
// How it works:
//   The mangled name of a class's type_info depends ONLY on the class's
//   unqualified name at global scope ("ChartPlugInWrapper" -> _ZTI18Chart...),
//   NOT on its base classes. So we declare a SAME-NAMED stand-in class here,
//   with a trivial polymorphic base we fully own, and give it an out-of-line
//   key function. The compiler then emits its vtable + `typeinfo for
//   ChartPlugInWrapper` in this TU. The real class is never linked, so there is
//   no duplicate-symbol clash; and the RTTI object is never dereferenced at
//   runtime on this path (the dynamic_cast never runs), so structural
//   divergence from the real class is irrelevant.
//
// This file deliberately includes NONE of the OpenCPN GUI headers so the real
// ChartPlugInWrapper definition cannot leak in and cause a redefinition.

namespace {
struct _PIWBase {
  virtual ~_PIWBase() {}
};
}  // namespace

// Same unqualified name + global scope => identical typeinfo mangling.
class ChartPlugInWrapper : public _PIWBase {
public:
  virtual void _emit_typeinfo_anchor();
};

// Out-of-line key function: forces emission of this TU's vtable + the
// `typeinfo for ChartPlugInWrapper` symbol the linker/loader needs.
void ChartPlugInWrapper::_emit_typeinfo_anchor() {}
