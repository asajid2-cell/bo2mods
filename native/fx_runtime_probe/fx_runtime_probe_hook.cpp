#define NOMINMAX
#define _CRT_SECURE_NO_WARNINGS

#include <windows.h>
#include <tlhelp32.h>
#include <intrin.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdlib>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "fx_runtime_probe_build_info.h"

namespace
{
constexpr DWORD kDispatchCallSiteRva = 0x0068E7FB;
constexpr DWORD kSpecialOpenMissContinueRva = 0x0068E802;
constexpr DWORD kSpecialOpenFlagBranchRva = 0x0068E83B;
constexpr DWORD kSpecialOpenSuccessBranchRva = 0x0068E872;
constexpr DWORD kSpecialOpenSuccessPostCallRva = 0x0068E87B;
constexpr DWORD kSpecialOpenSuccessContinueRva = 0x0068E8C3;
constexpr DWORD kSpecialOpenSuccessClass1ContinueRva = 0x0068E8D7;
constexpr DWORD kSpecialOpenSuccessClass1CallTargetRva = 0x0068FF78;
constexpr DWORD kSpecialOpenSuccessClass1PostCallRva = 0x0068E8E1;
constexpr DWORD kConsumerImageClassMapRva = 0x003446B6;
constexpr DWORD kConsumerAssetClassLookupRva = 0x00341C36;
constexpr DWORD kConsumerRenderTableRva = 0x0037C239;
constexpr DWORD kConsumerSubmitFlagsRva = 0x001F1C30;
constexpr DWORD kConsumerRenderTableZeroPathRva = 0x0037C245;
constexpr DWORD kConsumerRenderTableCompareRva = 0x0037C248;
constexpr DWORD kConsumerRenderTableMatchBranchRva = 0x0037C24A;
constexpr DWORD kConsumerRenderTableNonZeroBranchRva = 0x0037C2BB;
constexpr DWORD kConsumerUpstreamPreferredReturnSiteARva = 0x00349C3B;
constexpr DWORD kConsumerUpstreamPreferredReturnSiteBRva = 0x00349C95;
constexpr DWORD kConsumerUpstreamStarterReturnSiteCRva = 0x00349BE0;
constexpr DWORD kConsumerUpstreamStarterReturnSiteDRva = 0x02FF39D0;
constexpr DWORD kConsumerUpstreamStarterReturnSiteERva = 0x02FED240;
constexpr DWORD kConsumerUpstreamProbePreferredReturnSiteARva = 0x0037C68D;
constexpr DWORD kConsumerUpstreamProbePreferredReturnSiteBRva = 0x0037C6B7;
constexpr DWORD kConsumerUpstreamProbePreferredReturnSiteCRva = 0x0034EAA5;
constexpr DWORD kConsumerUpstreamProbeReturnSiteDRva = 0x0360D6A0;
constexpr DWORD kConsumerUpstreamProbeReturnSiteERva = 0x035F4864;
constexpr DWORD kConsumerUpstreamProbeReturnSiteFRva = 0x03606900;
constexpr DWORD kConsumerUpstreamProbeReturnSiteGRva = 0x03608380;
constexpr DWORD kConsumerUpstreamMaxCandidateRva = 0x01000000;
constexpr DWORD kXanimResolverCompareRva = 0x236D85DD;
constexpr DWORD kXanimResolverNullBranchFallthroughRva = 0x236D8640;
constexpr DWORD kXanimResolverNullBranchTakenRva = 0x236D869A;
constexpr DWORD kBootstrapHashNullGuardRva = 0x003FC590;
constexpr DWORD kBootstrapHashNullGuardResumeRva = 0x003FC599;
constexpr DWORD kCustomMapGuardStringRva = 0x22C86F76;
constexpr int kConsumerStepTraceInstructions = 12;
constexpr int kConsumerEntryStepTraceInstructions = 24;
constexpr int kBridgeToFirstProducerStepTraceInstructions = 96;
constexpr int kProducerClassStepTraceInstructions = 24;
constexpr int kXanimStepTraceInstructions = 24;
constexpr int kXanimFallthroughStepTraceInstructions = 96;
constexpr int kXanimPostFallthroughStepTraceInstructions = 96;
constexpr DWORD kTouchTraceDelayMs = 15000;
constexpr DWORD kTouchTraceDelayMsOpacityFocus = 2000;
constexpr DWORD kXanimResolverArmRetryDelayMs = 500;
constexpr int kXanimResolverArmMaxAttempts = 6;
constexpr DWORD kXanimAssetCensusDelayMs = 15000;
constexpr DWORD kXanimAssetCensusRepeatDelayMs = 15000;
constexpr int kXanimAssetCensusPasses = 4;
constexpr DWORD kGuardCopyScanDelayMs = 2000;
constexpr int kGuardCopyScanPasses = 24;
constexpr DWORD kLateTouchRescanDelayMs = 5000;
constexpr int kLateTouchRescanPasses = 18;
constexpr DWORD kConsumerArmInitialDelayMs = 5000;
constexpr DWORD kConsumerArmRetryDelayMs = 5000;
constexpr int kConsumerArmMaxAttempts = 4;
constexpr size_t kTouchTraceChunkSize = 0x10000;
constexpr size_t kTouchTraceMaxPages = 128;
constexpr int kNamedAssetRefLogMax = 20;

enum class ProbeMode
{
    Safe,
    BootstrapGuardOnly,
    RenderOpacityFocus,
    ViewmodelRenderFocus,
    XanimFocus,
    XanimConsumerFocus,
    XanimAssetLookupFocus,
    ProducerCompactOverrideFocus,
    ClassFamilyMaterializationWritepath,
};

struct SavedRegisters
{
    DWORD edi;
    DWORD esi;
    DWORD ebp;
    DWORD esp_saved;
    DWORD ebx;
    DWORD edx;
    DWORD ecx;
    DWORD eax;
    DWORD eflags;
};

struct ModuleInfoLite
{
    HMODULE base {};
    DWORD size {};
    std::string name;
    std::string path;
};

struct AssetTrace
{
    unsigned long long trace_id {};
    DWORD thread_id {};
    uintptr_t handle {};
    std::string image;
    std::string path;
    std::string resolved;
    uintptr_t return_addr {};
    size_t total_read {};
    int read_calls {};
    bool logged_first {};
    bool opacity_focus_armed {};
};

struct CallerSelection
{
    uintptr_t selected_return {};
    std::vector<uintptr_t> frames;
};

struct ReturnTraceState
{
    void** slot {};
    uintptr_t original_return {};
    unsigned long long trace_id {};
    std::string path;
};

enum class ConsumerUpstreamBucket
{
    Unknown,
    StarterOwned,
    ProbeOwned,
};

struct ConsumerUpstreamCandidate
{
    int slot {};
    uintptr_t addr {};
    unsigned long rva {};
    const char* module_name {"<unknown>"};
    int score {};
    int preferred {};
};

struct ExecTracePoint
{
    std::string label;
    uintptr_t addr {};
    BYTE original {};
    bool armed {};
    int hits {};
    int max_hits {8};
    unsigned long long trace_id {};
    std::string path;
};

struct TouchTraceTarget
{
    std::string label;
    std::string text;
    uintptr_t addr {};
    uintptr_t page_base {};
    DWORD original_protect {};
    bool armed {};
    bool hit {};
};

struct PolicyFieldWatch
{
    std::string label;
    std::string phase;
    uintptr_t selector_root {};
    int slot {};
    uintptr_t addr {};
    uintptr_t page_base {};
    DWORD original_protect {};
    bool armed {};
    bool active {true};
    unsigned write_hits {};
    uint32_t last_value {};
    DWORD arm_tick {};
};

struct PendingPolicyWriteTrace
{
    bool active {};
    uintptr_t page_base {};
    uintptr_t fault_addr {};
    uintptr_t pre_eip {};
    unsigned long access_type {};
    std::vector<size_t> watch_indices;
    std::vector<uint32_t> old_values;
};

struct MaterializationProducerSnapshot
{
    bool valid {};
    unsigned hit {};
    DWORD tick {};
    uintptr_t owner {};
    uintptr_t source {};
    uintptr_t class_ptr {};
    uintptr_t class_head {};
    uint16_t class_word {};
    uint8_t esi_nibble {};
    uint32_t class_slot2 {};
    uint32_t class_slot3 {};
    uint32_t class_slot4 {};
    uint32_t class_slot5 {};
    uint32_t class_slot6 {};
    uintptr_t selected_return {};
    std::string selected_signature;
};

struct TemporalSelectorRootObservation
{
    uintptr_t addr {};
    uintptr_t page_base {};
    DWORD first_tick {};
    DWORD last_tick {};
    unsigned sightings {};
    bool watch_armed {};
    uint32_t plus1 {};
    uint32_t plus2 {};
    uint32_t plus3 {};
    uint32_t plus4 {};
    uint32_t plus5 {};
    uint32_t plus6 {};
    uint32_t plus7 {};
    uint32_t plus8 {};
};

struct StepTraceState
{
    std::string label;
    unsigned long long trace_id {};
    std::string path;
    uintptr_t last_eip {};
    int steps_remaining {};
    int total_steps {};
    uintptr_t wrapper_base {};
    DWORD wrapper_arm_tick {};
    bool wrapper_initialized {};
    bool wrapper_prepopulated {};
    bool wrapper_any_change {};
    uint32_t wrapper_initial_values[3] {};
    uint32_t wrapper_last_values[3] {};
    bool wrapper_slot_changed[3] {};
    uintptr_t producer_class_ptr {};
    DWORD producer_arm_tick {};
    bool producer_initialized {};
    bool producer_any_change {};
    uint32_t producer_initial_values[6] {};
    uint32_t producer_last_values[6] {};
    bool producer_field_changed[6] {};
    bool force_complete {};
};

struct EntryWrapperOverrideConfig
{
    bool enabled {};
    bool patch_minus1 {};
    bool patch_plus3 {};
    bool use_minus1_rva {};
    bool use_plus3_rva {};
    uint32_t minus1_value {};
    uint32_t plus3_value {};
    uint32_t minus1_rva {};
    uint32_t plus3_rva {};
    unsigned target_hit {1};
    std::string label;
    std::string apply_label;
};

struct ProducerCompactOverrideConfig
{
    bool enabled {};
    bool patch_pointer_swap_34 {};
    bool patch_pointer_family_from_initial {};
    bool patch_class_head_from_initial {};
    bool patch_class_head {};
    bool patch_class_plus2_from_initial {};
    bool patch_class_plus2 {};
    bool patch_class_plus3_from_initial {};
    bool patch_class_plus3 {};
    bool patch_class_plus4_from_initial {};
    bool patch_class_plus4 {};
    bool patch_class_plus5_from_initial {};
    bool patch_class_plus5 {};
    bool patch_class_plus6 {};
    bool trace_target_family_steps {};
    bool trace_bridge_to_first_producer {};
    bool stop_after_bridge_candidate_birth {};
    bool arm_render_from_startup {true};
    bool follow_on_render {};
    unsigned target_hit {1};
    bool target_first_distinct_after_initial {};
    unsigned bridge_trace_steps {kBridgeToFirstProducerStepTraceInstructions};
    bool require_bridge_bucket {};
    uint32_t bridge_required_minus1 {};
    uint32_t bridge_required_plus3 {};
    uint32_t class_head_value {};
    uint32_t class_plus2_value {};
    uint32_t class_plus3_value {};
    uint32_t class_plus4_value {};
    uint32_t class_plus5_value {};
    uint32_t class_plus6_value {};
    uintptr_t initial_class_ptr {};
    uint32_t initial_class_head {};
    uint32_t initial_class_slot2 {};
    uint32_t initial_class_slot3 {};
    uint32_t initial_class_slot4 {};
    uint32_t initial_class_slot5 {};
    bool initial_family_seen {};
    std::string label;
};

struct XanimExpectationSection
{
    std::string asset_name;
    std::string section_name;
    size_t size {};
    uint32_t hash {};
    size_t prefix_offset {};
    size_t relative_offset {SIZE_MAX};
    std::vector<unsigned char> prefix;
};

struct XanimExpectedAssetVariant
{
    std::string asset_name;
    std::string variant_name;
    uint16_t numframes {};
    uint16_t data_byte_count {};
    uint16_t data_short_count {};
    uint16_t data_int_count {};
    uint8_t notify_count {};
    uint8_t total_bones {};
    float frequency {};
    uint8_t asset_type {};
    uint8_t is_default {};
    uint8_t b_loop {};
    uint8_t b_delta {};
    uint8_t b_delta3d {};
    uint8_t names_ptr_present {};
    uint8_t data_byte_ptr_present {};
    uint8_t data_short_ptr_present {};
    uint8_t data_int_ptr_present {};
    uint8_t notify_ptr_present {};
    uint8_t delta_part_ptr_present {};
};

struct XanimRuntimeSectionPatch
{
    std::string asset_name;
    std::string section_name;
    std::vector<unsigned char> data;
};

struct ObservedAssetAddress
{
    std::string kind;
    std::string asset_name;
    std::string source;
    uintptr_t addr {};
    uintptr_t related_addr {};
};

struct SeedNormalizationState
{
    bool active {};
    bool first_family_logged {};
    unsigned long long trace_id {};
    DWORD birth_tick {};
    uintptr_t seed_ptr {};
    uintptr_t birth_eip {};
    std::string birth_reg;
    uint32_t seed_slots[7] {};
};

struct ConsumerObjectState
{
    std::string context;
    uintptr_t base_addr {};
    int before_slots {};
    int after_slots {};
    DWORD first_tick {};
    DWORD last_tick {};
    unsigned hit_count {};
    std::vector<uint32_t> first_values;
    std::vector<uint32_t> last_values;
};

struct ConsumerAnchorSnapshot
{
    std::string context;
    uintptr_t base_addr {};
    int before_slots {4};
    int after_slots {8};
};

struct ConsumerDeferredSnapshotRequest
{
    std::string trigger_label;
    uintptr_t trigger_addr {};
    std::vector<ConsumerAnchorSnapshot> anchors;
};

HMODULE g_self = nullptr;
HMODULE g_main_module = nullptr;
uintptr_t g_main_base = 0;
SYSTEM_INFO g_system_info {};
std::mutex g_log_mutex;
std::mutex g_state_mutex;
std::mutex g_observed_assets_mutex;
std::mutex g_consumer_objects_mutex;
FILE* g_log_file = nullptr;
std::atomic<unsigned long> g_log_seq {0};
std::atomic<unsigned long long> g_next_trace_id {1};
std::atomic<bool> g_opacity_focus_consumers_armed {false};
std::atomic<bool> g_opacity_focus_rearm_pending {false};
std::atomic<bool> g_xanim_focus_rearm_pending {false};
std::atomic<bool> g_xanim_post_fallthrough_trace_started {false};
std::atomic<uintptr_t> g_last_consumer_render_lookup_addr {0};
std::atomic<uintptr_t> g_last_consumer_render_edi_addr {0};
std::atomic<uintptr_t> g_lookup_family_span_base {0};
std::atomic<int> g_lookup_family_span_dwords {0};
std::atomic<bool> g_xanim_asset_census_started {false};
std::atomic<bool> g_consumer_first_hit_logged {false};
std::atomic<bool> g_consumer_deferred_snapshots_started {false};
std::atomic<int> g_unhandled_breakpoint_logs {0};
std::atomic<bool> g_selector_root_temporal_started {false};

std::vector<ModuleInfoLite> g_modules;
std::unordered_set<std::string> g_watch_images;
std::unordered_set<std::string> g_watch_files;
std::unordered_set<std::string> g_watch_materials;
std::unordered_set<std::string> g_watch_techsets;
std::unordered_set<std::string> g_watch_xanims;
std::unordered_set<std::string> g_watch_xmodels;
std::unordered_map<std::string, std::string> g_xanim_aliases;
std::vector<XanimExpectedAssetVariant> g_xanim_expected_assets;
std::vector<XanimExpectationSection> g_xanim_expectations;
std::unordered_set<uintptr_t> g_xanim_cluster_logged;
std::vector<XanimRuntimeSectionPatch> g_xanim_runtime_patches;
std::unordered_set<uintptr_t> g_xanim_runtime_patched_headers;
std::unordered_set<uintptr_t> g_xanim_runtime_patched_sections;
std::unordered_set<std::string> g_immediate_live_scan_seen;
std::vector<ObservedAssetAddress> g_observed_asset_addresses;
std::unordered_set<std::string> g_observed_asset_address_keys;
std::unordered_map<std::string, ConsumerObjectState> g_consumer_object_states;
std::unordered_set<std::string> g_consumer_deferred_snapshot_keys;

std::unordered_map<uintptr_t, AssetTrace> g_active_handles;
std::unordered_map<DWORD, ReturnTraceState> g_return_states;
std::unordered_map<uintptr_t, ExecTracePoint> g_exec_traces;
std::unordered_map<DWORD, StepTraceState> g_step_traces;
std::vector<TouchTraceTarget> g_touch_targets;
std::unordered_map<uintptr_t, std::vector<size_t>> g_touch_pages;
std::vector<PolicyFieldWatch> g_policy_field_watches;
std::unordered_map<uintptr_t, std::vector<size_t>> g_policy_field_pages;
std::unordered_map<uintptr_t, TemporalSelectorRootObservation> g_temporal_selector_roots;

thread_local uintptr_t g_tls_rearm_addr = 0;
thread_local bool g_tls_in_veh = false;
thread_local PendingPolicyWriteTrace g_tls_policy_write_trace;
MaterializationProducerSnapshot g_latest_materialization_producer;
EntryWrapperOverrideConfig g_entry_wrapper_override;
std::atomic<bool> g_entry_wrapper_override_applied {false};
ProducerCompactOverrideConfig g_producer_compact_override;
std::atomic<bool> g_producer_compact_override_applied {false};
SeedNormalizationState g_seed_normalization;
std::atomic<bool> g_producer_follow_on_render_armed {false};
std::atomic<bool> g_producer_class_trace_started {false};

decltype(&CreateFileA) g_real_create_file_a = nullptr;
decltype(&CreateFileW) g_real_create_file_w = nullptr;
decltype(&ReadFile) g_real_read_file = nullptr;
decltype(&CloseHandle) g_real_close_handle = nullptr;

void* g_return_trace_thunk = nullptr;
std::atomic<bool> g_touch_trace_started {false};
std::atomic<bool> g_touch_trace_complete {false};
ProbeMode g_probe_mode = ProbeMode::Safe;

HANDLE WINAPI hook_create_file_a(LPCSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file);
HANDLE WINAPI hook_create_file_w(LPCWSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file);
BOOL WINAPI hook_read_file(HANDLE handle, LPVOID buffer, DWORD bytes_to_read, LPDWORD bytes_read, LPOVERLAPPED overlapped);
BOOL WINAPI hook_close_handle(HANDLE handle);
int arm_consumer_exec_traces();
void arm_exec_trace_locked(const char* label, uintptr_t addr, unsigned long long trace_id, const std::string& path, int max_hits);
void add_touch_target_locked(const std::string& label, const std::string& text, uintptr_t addr, DWORD original_protect);
void arm_touch_trace_pages();
void arm_selector_root_policy_watches_locked(const char* phase, uintptr_t selector_root);
void arm_policy_field_pages_locked();
void load_entry_wrapper_override();
void load_producer_compact_override();
bool capture_entry_wrapper_values(uintptr_t wrapper_base, uint32_t* minus3, uint32_t* minus1, uint32_t* plus3);
void log_entry_wrapper_snapshot(const char* reason, unsigned long long trace_id, uintptr_t eip, uintptr_t wrapper_base, uint32_t minus3, uint32_t minus1, uint32_t plus3, int step);
void maybe_apply_entry_wrapper_override(unsigned long long trace_id, uintptr_t eip, uintptr_t wrapper_base, const std::string& point_label, unsigned hit);
bool capture_producer_class_values(uintptr_t class_ptr, uint32_t* class_head, uint32_t* class_slot2, uint32_t* class_slot3, uint32_t* class_slot4, uint32_t* class_slot5, uint32_t* class_slot6);
void log_producer_class_snapshot(const char* reason, unsigned long long trace_id, uintptr_t eip, uintptr_t class_ptr, uint32_t class_head, uint32_t class_slot2, uint32_t class_slot3, uint32_t class_slot4, uint32_t class_slot5, uint32_t class_slot6, int step = -1);
void prime_producer_class_trace_state_locked(StepTraceState& state, unsigned long long trace_id, const CONTEXT& ctx, uintptr_t class_ptr);
void trace_producer_class_step_locked(StepTraceState& state, const CONTEXT& ctx, int step_number);
bool maybe_prime_bridge_producer_candidate_locked(StepTraceState& state, const CONTEXT& ctx, int step_number);
void maybe_apply_producer_compact_override(unsigned hit, unsigned long long trace_id, const std::string& path, CONTEXT& ctx, uintptr_t class_ptr, uint32_t class_head, uint32_t* class_slot2, uint32_t* class_slot3, uint32_t* class_slot4, uint32_t* class_slot5, uint32_t* class_slot6);
void maybe_arm_follow_on_render_trace_after_asset_lookup();
void begin_step_trace_locked(DWORD thread_id, const char* label, unsigned long long trace_id, const std::string& path, uintptr_t start_eip, int steps);
bool bytes_match(uintptr_t addr, const BYTE* expected, size_t size);
void prime_entry_wrapper_trace_state_locked(StepTraceState& state, const CONTEXT& ctx);
void trace_entry_wrapper_step_locked(StepTraceState& state, const CONTEXT& ctx, int step_number);
uintptr_t find_touch_target_addr_locked(const char* text);
bool region_is_readable(const MEMORY_BASIC_INFORMATION& mbi);
const char* module_name_for_addr(uintptr_t value, unsigned long* rva_out);
const ModuleInfoLite* module_info_for_addr(uintptr_t value);
uintptr_t rva_to_va(DWORD rva);
bool pointer_readable(uintptr_t addr, size_t size = 1);
std::string safe_read_ascii_string(uintptr_t addr, size_t max_chars);
uint32_t fnv1a_hash_bytes(const unsigned char* data, size_t size);
uint32_t hash_memory_fnv1a(uintptr_t addr, size_t size);
bool is_known_materialization_plus5_value(uint32_t value);
bool is_known_materialization_plus6_value(uint32_t value);
bool is_executable_address(uintptr_t addr);
void record_observed_asset_address(const char* kind, const char* asset_name, uintptr_t addr, const char* source, uintptr_t related_addr = 0);
std::vector<uint32_t> capture_dword_window_values(uintptr_t base_addr, int before_slots = 4, int after_slots = 8);
void log_consumer_dword_window_correlations(const char* context, uintptr_t base_addr, int before_slots, const std::vector<uint32_t>& values);
void track_consumer_object_window(const char* context, uintptr_t base_addr, int before_slots = 4, int after_slots = 8);
void log_consumer_typed_window(const char* context, const char* phase, uintptr_t base_addr, int before_slots = 4, int after_slots = 8);
void log_consumer_pointer_chases(const char* context, const char* phase, uintptr_t base_addr, int before_slots = 4, int after_slots = 8);
void log_consumer_anchor_snapshot(const char* context, const char* phase, uintptr_t base_addr, int before_slots = 4, int after_slots = 8);
void log_consumer_span_snapshot(const char* context, const char* phase, uintptr_t base_addr, int dword_count);
void arm_consumer_upstream_return_traces_from_stack_locked(const CONTEXT& ctx, unsigned long long trace_id, const std::string& path);
void log_consumer_upstream_hit_context(const std::string& label, unsigned hit, const CONTEXT& ctx);
void log_consumer_render_hit_context(unsigned hit, const CONTEXT& ctx);
void log_consumer_asset_lookup_hit_context(unsigned hit, unsigned long long trace_id, const std::string& path, CONTEXT& ctx);
void log_consumer_asset_lookup_entry_hit_context(unsigned hit, const CONTEXT& ctx, unsigned long long trace_id, const std::string& path);
void try_log_consumer_render_edi_family(const char* phase, uintptr_t edi, bool include_extended_children);
void log_materialization_producer_snapshot(const char* reason);
void log_selector_root_compact_snapshot(const char* reason, const char* phase, uintptr_t selector_root);
DWORD WINAPI selector_root_temporal_thread(void*);
bool start_consumer_deferred_snapshots_once(const char* trigger_key, const char* trigger_label, uintptr_t trigger_addr, const std::vector<ConsumerAnchorSnapshot>& anchors);
bool start_consumer_deferred_snapshots_once_locked(const char* trigger_key, const char* trigger_label, uintptr_t trigger_addr, const std::vector<ConsumerAnchorSnapshot>& anchors);
CallerSelection capture_relevant_caller();
void log_backtrace_selection(unsigned long long trace_id, const CallerSelection& sel, const std::string& image, const std::string& path);
void load_xanim_runtime_patches();
void apply_runtime_patches_via_expectations();
int apply_runtime_patches_near_name_addrs(const char* target_name, const std::vector<uintptr_t>& name_addrs);
void scan_live_named_asset_refs(const char* prefix, const char* target_name, uintptr_t target_name_addr);
void scan_live_xanim_asset_candidates(const char* target_name, uintptr_t target_name_addr);
bool maybe_arm_selector_root_from_pointer_family_locked(const char* phase, const char* label, uintptr_t base, int max_slots = 4);
void probe_entry_selector_root_candidates_locked(const char* phase, const CONTEXT& ctx);

std::string narrow_from_wide(const std::wstring& value)
{
    if (value.empty())
        return {};
    const int size = WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    std::string out(size, '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), out.data(), size, nullptr, nullptr);
    return out;
}

std::wstring wide_from_utf8(const std::string& value)
{
    if (value.empty())
        return {};
    const int size = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), nullptr, 0);
    std::wstring out(size, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.c_str(), static_cast<int>(value.size()), out.data(), size);
    return out;
}

std::string to_lower_copy(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return value;
}

std::string expectation_variant_prefix(const std::string& section_name)
{
    const size_t pos = section_name.rfind('_');
    if (pos == std::string::npos)
        return section_name;
    return section_name.substr(0, pos);
}

std::string join_compact_strings(const std::vector<std::string>& values)
{
    std::string out;
    for (size_t i = 0; i < values.size(); ++i)
    {
        if (i)
            out.push_back(',');
        out += values[i];
    }
    return out;
}

std::string classify_xanim_variant_values(const std::vector<std::string>& values)
{
    if (values.empty())
        return "unknown";
    std::vector<std::string> distinct;
    for (const auto& value : values)
    {
        if (value.empty())
            continue;
        if (std::find(distinct.begin(), distinct.end(), value) == distinct.end())
            distinct.push_back(value);
    }
    if (distinct.empty())
        return "unknown";
    if (distinct.size() == 1)
        return distinct.front();
    return "mixed";
}

std::vector<std::string> expected_section_variants_for_hash(const std::string& asset_name, const char* section_suffix, uint32_t hash)
{
    std::vector<std::string> variants;
    for (const auto& expectation : g_xanim_expectations)
    {
        if (expectation.asset_name != asset_name)
            continue;
        const size_t split = expectation.section_name.rfind('_');
        if (split == std::string::npos)
            continue;
        const std::string suffix = expectation.section_name.substr(split + 1);
        if (suffix != section_suffix)
            continue;
        if (expectation.hash != hash)
            continue;
        const std::string variant = expectation_variant_prefix(expectation.section_name);
        if (std::find(variants.begin(), variants.end(), variant) == variants.end())
            variants.push_back(variant);
    }
    return variants;
}

std::vector<std::string> expected_section_variants_for_memory(const std::string& asset_name, const char* section_suffix, uintptr_t addr)
{
    std::vector<std::string> variants;
    if (!addr)
        return variants;
    for (const auto& expectation : g_xanim_expectations)
    {
        if (expectation.asset_name != asset_name)
            continue;
        const size_t split = expectation.section_name.rfind('_');
        if (split == std::string::npos)
            continue;
        const std::string suffix = expectation.section_name.substr(split + 1);
        if (suffix != section_suffix)
            continue;
        if (!pointer_readable(addr, expectation.size))
            continue;
        const uint32_t hash = hash_memory_fnv1a(addr, expectation.size);
        if (hash != expectation.hash)
            continue;
        const std::string variant = expectation_variant_prefix(expectation.section_name);
        if (std::find(variants.begin(), variants.end(), variant) == variants.end())
            variants.push_back(variant);
    }
    return variants;
}

std::string xanim_header_variant_exact(
    const std::string& asset_name,
    uint16_t numframes,
    uint16_t data_byte_count,
    uint16_t data_short_count,
    uint16_t data_int_count,
    uint8_t notify_count,
    uint8_t total_bones,
    float frequency,
    uint8_t asset_type,
    uint8_t is_default,
    uint8_t b_loop,
    uint8_t b_delta,
    uint8_t b_delta3d,
    uint8_t names_ptr_present,
    uint8_t data_byte_ptr_present,
    uint8_t data_short_ptr_present,
    uint8_t data_int_ptr_present,
    uint8_t notify_ptr_present,
    uint8_t delta_part_ptr_present)
{
    std::vector<std::string> variants;
    for (const auto& expectation : g_xanim_expected_assets)
    {
        if (expectation.asset_name != asset_name)
            continue;
        if (expectation.numframes != numframes ||
            expectation.data_byte_count != data_byte_count ||
            expectation.data_short_count != data_short_count ||
            expectation.data_int_count != data_int_count ||
            expectation.notify_count != notify_count ||
            expectation.total_bones != total_bones ||
            std::fabs(expectation.frequency - frequency) > 0.01f ||
            expectation.asset_type != asset_type ||
            expectation.is_default != is_default ||
            expectation.b_loop != b_loop ||
            expectation.b_delta != b_delta ||
            expectation.b_delta3d != b_delta3d ||
            expectation.names_ptr_present != names_ptr_present ||
            expectation.data_byte_ptr_present != data_byte_ptr_present ||
            expectation.data_short_ptr_present != data_short_ptr_present ||
            expectation.data_int_ptr_present != data_int_ptr_present ||
            expectation.notify_ptr_present != notify_ptr_present ||
            expectation.delta_part_ptr_present != delta_part_ptr_present)
        {
            continue;
        }
        if (std::find(variants.begin(), variants.end(), expectation.variant_name) == variants.end())
            variants.push_back(expectation.variant_name);
    }
    return classify_xanim_variant_values(variants);
}

std::string xanim_best_header_variant_summary(
    const std::string& asset_name,
    uint16_t numframes,
    uint16_t data_byte_count,
    uint16_t data_short_count,
    uint16_t data_int_count,
    uint8_t notify_count,
    uint8_t total_bones,
    float frequency,
    uint8_t asset_type,
    uint8_t is_default,
    uint8_t b_loop,
    uint8_t b_delta,
    uint8_t b_delta3d,
    uint8_t names_ptr_present,
    uint8_t data_byte_ptr_present,
    uint8_t data_short_ptr_present,
    uint8_t data_int_ptr_present,
    uint8_t notify_ptr_present,
    uint8_t delta_part_ptr_present)
{
    int best_score = -1;
    const int total_fields = 19;
    std::vector<std::string> best_variants;
    for (const auto& expectation : g_xanim_expected_assets)
    {
        if (expectation.asset_name != asset_name)
            continue;
        int score = 0;
        score += expectation.numframes == numframes ? 1 : 0;
        score += expectation.data_byte_count == data_byte_count ? 1 : 0;
        score += expectation.data_short_count == data_short_count ? 1 : 0;
        score += expectation.data_int_count == data_int_count ? 1 : 0;
        score += expectation.notify_count == notify_count ? 1 : 0;
        score += expectation.total_bones == total_bones ? 1 : 0;
        score += std::fabs(expectation.frequency - frequency) <= 0.01f ? 1 : 0;
        score += expectation.asset_type == asset_type ? 1 : 0;
        score += expectation.is_default == is_default ? 1 : 0;
        score += expectation.b_loop == b_loop ? 1 : 0;
        score += expectation.b_delta == b_delta ? 1 : 0;
        score += expectation.b_delta3d == b_delta3d ? 1 : 0;
        score += expectation.names_ptr_present == names_ptr_present ? 1 : 0;
        score += expectation.data_byte_ptr_present == data_byte_ptr_present ? 1 : 0;
        score += expectation.data_short_ptr_present == data_short_ptr_present ? 1 : 0;
        score += expectation.data_int_ptr_present == data_int_ptr_present ? 1 : 0;
        score += expectation.notify_ptr_present == notify_ptr_present ? 1 : 0;
        score += expectation.delta_part_ptr_present == delta_part_ptr_present ? 1 : 0;
        score += 1; // asset_name match
        if (score > best_score)
        {
            best_score = score;
            best_variants.clear();
        }
        if (score == best_score &&
            std::find(best_variants.begin(), best_variants.end(), expectation.variant_name) == best_variants.end())
        {
            best_variants.push_back(expectation.variant_name);
        }
    }
    if (best_score < 0)
        return "unknown";
    char buffer[128] {};
    std::snprintf(
        buffer,
        sizeof(buffer),
        "%s:%d/%d",
        classify_xanim_variant_values(best_variants).c_str(),
        best_score,
        total_fields);
    return buffer;
}

std::string base_name_of(const std::string& path)
{
    const size_t slash = path.find_last_of("\\/");
    return slash == std::string::npos ? path : path.substr(slash + 1);
}

std::string remove_iwi_suffix(std::string file_name)
{
    const std::string lower = to_lower_copy(file_name);
    if (lower.size() >= 4 && lower.substr(lower.size() - 4) == ".iwi")
        file_name.resize(file_name.size() - 4);
    return file_name;
}

std::string normalize_image_token(const std::string& path)
{
    std::string file_name = base_name_of(path);
    if (!file_name.empty() && file_name[0] == ',')
        file_name.erase(file_name.begin());
    return remove_iwi_suffix(file_name);
}

bool is_in_main_module(uintptr_t addr)
{
    if (!g_main_base || !addr)
        return false;

    for (const auto& module : g_modules)
    {
        if (module.base != g_main_module)
            continue;
        const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
        return addr >= base && addr < base + module.size;
    }

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(g_main_base), &mbi, sizeof(mbi)))
        return false;
    const uintptr_t base = reinterpret_cast<uintptr_t>(mbi.AllocationBase ? mbi.AllocationBase : mbi.BaseAddress);
    const uintptr_t size = static_cast<uintptr_t>(mbi.RegionSize);
    return addr >= base && addr < base + size;
}

unsigned long main_module_rva(uintptr_t addr)
{
    if (!is_in_main_module(addr))
        return 0;
    return static_cast<unsigned long>(addr - g_main_base);
}

bool is_probe_module_addr(uintptr_t addr)
{
    if (!g_self)
        return false;
    for (const auto& module : g_modules)
    {
        if (module.base != g_self)
            continue;
        const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
        return addr >= base && addr < base + module.size;
    }

    const uintptr_t base = reinterpret_cast<uintptr_t>(g_self);
    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(base), &mbi, sizeof(mbi)))
        return false;
    return addr >= base && addr < base + mbi.RegionSize;
}

bool is_runtime_candidate_code_addr(uintptr_t addr)
{
    unsigned long rva = 0;
    const char* module_name = module_name_for_addr(addr, &rva);
    if (is_probe_module_addr(addr))
        return false;
    if (std::strcmp(module_name, "ntdll.dll") == 0)
        return false;
    if (std::strcmp(module_name, "kernel32.dll") == 0)
        return false;
    if (std::strcmp(module_name, "kernelbase.dll") == 0)
        return false;
    return true;
}

bool path_is_watched_file(const std::string& path)
{
    const std::string file_name = base_name_of(to_lower_copy(path));
    return g_watch_files.find(file_name) != g_watch_files.end();
}

bool try_match_watched_image(const std::string& path, std::string& image_out)
{
    const std::string image = to_lower_copy(normalize_image_token(path));
    if (image.empty())
        return false;
    if (g_watch_images.find(image) == g_watch_images.end())
        return false;
    image_out = image;
    return true;
}

std::string sanitize_comma_iwi_path(const std::string& path)
{
    const size_t slash = path.find_last_of("\\/");
    if (slash == std::string::npos)
        return path;
    std::string dir = path.substr(0, slash + 1);
    std::string file_name = path.substr(slash + 1);
    if (!file_name.empty() && file_name[0] == ',')
        file_name.erase(file_name.begin());
    return dir + file_name;
}

bool is_opacity_focus_target(const std::string& label, const std::string& text)
{
    const std::string l = to_lower_copy(label);
    const std::string t = to_lower_copy(text);
    if (l == "material" && t == "bo3rfx_gfx_light_phosphorous_em_i1024")
        return true;
    if (l == "image" && (t == "bo3rfx_fxt_light_phosphorous" || t == ",bo3rfx_fxt_light_phosphorous" || t == "fxt_light_phosphorous" || t == ",fxt_light_phosphorous"))
        return true;
    if (l == "techset" && t == "effect_26z423jf")
        return true;
    return false;
}

bool is_opacity_focus_image(const std::string& image)
{
    const std::string t = to_lower_copy(image);
    return t == "bo3rfx_fxt_light_phosphorous" || t == "fxt_light_phosphorous";
}

bool is_xanim_focus_target(const std::string& label, const std::string& text)
{
    const std::string l = to_lower_copy(label);
    return l == "xanim" || l == "xmodel" || l == "xanim_expected_section" || l == "xanim_runtime_dataint" || l == "xanim_runtime_delta";
}

void seed_default_xanim_watchlist()
{
    if (!g_watch_xanims.empty())
        return;

    g_watch_xanims.insert("viewmodel_zomb_mg08_idle");
    g_watch_xanims.insert("viewmodel_zomb_mg08_first_raise");
    g_watch_xanims.insert("viewmodel_zomb_mg08_fire");
    g_watch_xanims.insert("viewmodel_zomb_mg08_pullout");
    g_watch_xanims.insert("viewmodel_zomb_mg08_putaway");
    g_watch_xanims.insert("viewmodel_minigun_t6_idle");
    g_watch_xanims.insert("viewmodel_minigun_t6_fire");
    g_watch_xanims.insert("viewmodel_minigun_t6_pullout");
}

void seed_default_xanim_file_watchlist()
{
    g_watch_files.insert("mod_load.ff");
    g_watch_files.insert("so_zsurvival_zm_transit.ff");
}

std::string module_relative_path(const wchar_t* suffix)
{
    wchar_t self_path[MAX_PATH] {};
    GetModuleFileNameW(g_self, self_path, MAX_PATH);
    std::wstring path = self_path;
    const size_t slash = path.find_last_of(L"\\/");
    if (slash != std::wstring::npos)
        path.resize(slash + 1);
    path += suffix;
    return narrow_from_wide(path);
}

int hex_nibble(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return 10 + (c - 'a');
    if (c >= 'A' && c <= 'F')
        return 10 + (c - 'A');
    return -1;
}

std::vector<unsigned char> parse_hex_bytes(const std::string& value)
{
    std::vector<unsigned char> out;
    if (value.empty() || (value.size() % 2) != 0)
        return out;
    out.reserve(value.size() / 2);
    for (size_t i = 0; i < value.size(); i += 2)
    {
        const int hi = hex_nibble(value[i]);
        const int lo = hex_nibble(value[i + 1]);
        if (hi < 0 || lo < 0)
        {
            out.clear();
            return out;
        }
        out.push_back(static_cast<unsigned char>((hi << 4) | lo));
    }
    return out;
}

const char* probe_mode_name()
{
    switch (g_probe_mode)
    {
    case ProbeMode::BootstrapGuardOnly:
        return "bootstrap_guard_only";
    case ProbeMode::XanimFocus:
        return "xanim_focus";
    case ProbeMode::XanimConsumerFocus:
        return "xanim_consumer_focus";
    case ProbeMode::XanimAssetLookupFocus:
        return "xanim_asset_lookup_focus";
    case ProbeMode::ProducerCompactOverrideFocus:
        return "producer_compact_override_focus";
    case ProbeMode::ClassFamilyMaterializationWritepath:
        return "class_family_materialization_writepath";
    case ProbeMode::RenderOpacityFocus:
        return "render_opacity_focus";
    case ProbeMode::ViewmodelRenderFocus:
        return "viewmodel_render_focus";
    case ProbeMode::Safe:
    default:
        return "safe";
    }
}

bool is_render_only_focus_mode()
{
    return g_probe_mode == ProbeMode::RenderOpacityFocus ||
        g_probe_mode == ProbeMode::ViewmodelRenderFocus;
}

const char* producer_compact_target_mode_name()
{
    return g_producer_compact_override.target_first_distinct_after_initial
        ? "first_distinct_after_initial"
        : "exact_hit";
}

bool is_minimal_consumer_focus_mode()
{
    return g_probe_mode == ProbeMode::XanimConsumerFocus ||
        g_probe_mode == ProbeMode::XanimAssetLookupFocus ||
        g_probe_mode == ProbeMode::ProducerCompactOverrideFocus ||
        g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath;
}

bool is_asset_lookup_only_mode()
{
    return g_probe_mode == ProbeMode::XanimAssetLookupFocus;
}

bool is_materialization_writepath_mode()
{
    return g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath;
}

bool is_consumer_trace_label(const std::string& label)
{
    return label.rfind("consumer_", 0) == 0;
}

DWORD touch_trace_delay_ms()
{
    if (g_probe_mode == ProbeMode::RenderOpacityFocus)
        return kTouchTraceDelayMsOpacityFocus;
    if (g_probe_mode == ProbeMode::XanimFocus || is_minimal_consumer_focus_mode())
        return 2000;
    return 0;
}

DWORD xanim_asset_census_delay_ms()
{
    return g_probe_mode == ProbeMode::XanimFocus ? 3000 : kXanimAssetCensusDelayMs;
}

DWORD xanim_asset_census_repeat_delay_ms()
{
    return g_probe_mode == ProbeMode::XanimFocus ? 4000 : kXanimAssetCensusRepeatDelayMs;
}

int xanim_asset_census_passes()
{
    return g_probe_mode == ProbeMode::XanimFocus ? 3 : kXanimAssetCensusPasses;
}

DWORD consumer_arm_initial_delay_ms()
{
    if (g_probe_mode == ProbeMode::XanimFocus)
        return 12000;
    if (g_probe_mode == ProbeMode::XanimAssetLookupFocus)
        return 250;
    if (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus)
        return 250;
    if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath)
        return 0;
    if (is_minimal_consumer_focus_mode())
        return 1500;
    return g_probe_mode == ProbeMode::RenderOpacityFocus ? kTouchTraceDelayMsOpacityFocus : kConsumerArmInitialDelayMs;
}

void log_line(const char* fmt, ...)
{
    std::lock_guard<std::mutex> lock(g_log_mutex);
    if (!g_log_file)
        return;

    SYSTEMTIME st {};
    GetLocalTime(&st);
    const unsigned long seq = ++g_log_seq;
    std::fprintf(g_log_file, "[%06lu][%02u:%02u:%02u.%03u] ", seq, st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);

    va_list args;
    va_start(args, fmt);
    std::vfprintf(g_log_file, fmt, args);
    va_end(args);

    std::fputc('\n', g_log_file);
    std::fflush(g_log_file);
}

bool safe_copy_memory(uintptr_t addr, void* out, size_t size)
{
    __try
    {
        std::memcpy(out, reinterpret_cast<const void*>(addr), size);
        return true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return false;
    }
}

bool pointer_readable(uintptr_t addr, size_t size)
{
    if (!addr || size == 0)
        return false;
    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<const void*>(addr), &mbi, sizeof(mbi)))
        return false;
    if (!region_is_readable(mbi))
        return false;
    const uintptr_t base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
    const uintptr_t end = base + mbi.RegionSize;
    if (addr < base || addr + size > end || addr + size < addr)
        return false;
    return true;
}

bool rewrite_ascii_string_in_place(uintptr_t addr, const std::string& replacement, size_t capacity)
{
    if (!addr || replacement.empty() || capacity == 0)
        return false;
    if (replacement.size() + 1 > capacity)
        return false;

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(addr), &mbi, sizeof(mbi)))
        return false;
    if (mbi.State != MEM_COMMIT)
        return false;
    if ((mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
        return false;
    const uintptr_t base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
    const uintptr_t end = base + mbi.RegionSize;
    if (addr < base || addr + capacity > end || addr + capacity < addr)
        return false;
    if (mbi.Type != MEM_PRIVATE)
        return false;

    DWORD old_protect = 0;
    if (!VirtualProtect(reinterpret_cast<void*>(addr), capacity, PAGE_READWRITE, &old_protect))
        return false;

    bool ok = false;
    __try
    {
        std::memset(reinterpret_cast<void*>(addr), 0, capacity);
        std::memcpy(reinterpret_cast<void*>(addr), replacement.c_str(), replacement.size());
        ok = true;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        ok = false;
    }

    DWORD restore = 0;
    VirtualProtect(reinterpret_cast<void*>(addr), capacity, old_protect, &restore);
    return ok;
}

std::string xanim_alias_for_name(const std::string& value)
{
    const std::string key = to_lower_copy(value);
    const auto it = g_xanim_aliases.find(key);
    if (it == g_xanim_aliases.end())
        return {};
    return it->second;
}

std::string hex_prefix(const void* data, size_t size, size_t max_bytes = 32)
{
    const unsigned char* bytes = static_cast<const unsigned char*>(data);
    const size_t count = std::min(size, max_bytes);
    char buffer[4] {};
    std::string out;
    for (size_t i = 0; i < count; ++i)
    {
        if (i)
            out.push_back(' ');
        std::snprintf(buffer, sizeof(buffer), "%02X", bytes[i]);
        out += buffer;
    }
    return out;
}

void log_bytes_around(const char* label, uintptr_t addr, size_t before = 16, size_t after = 24)
{
    uintptr_t start = addr > before ? addr - before : addr;
    unsigned char bytes[64] {};
    const size_t want = std::min(sizeof(bytes), before + after);
    if (!safe_copy_memory(start, bytes, want))
        return;
    log_line("%s around=0x%08lX start=0x%08lX data=%s", label, static_cast<unsigned long>(addr), static_cast<unsigned long>(start), hex_prefix(bytes, want, want).c_str());
}

std::string format_dword_window(uintptr_t addr, size_t before_dwords = 4, size_t after_dwords = 8)
{
    const size_t total_dwords = before_dwords + after_dwords + 1;
    const size_t total_bytes = total_dwords * sizeof(uint32_t);
    const uintptr_t start = addr > (before_dwords * sizeof(uint32_t)) ? (addr - (before_dwords * sizeof(uint32_t))) : addr;
    std::vector<uint32_t> values(total_dwords, 0);
    if (!safe_copy_memory(start, values.data(), total_bytes))
        return {};

    std::string out;
    char buffer[64] {};
    for (size_t i = 0; i < total_dwords; ++i)
    {
        const long relative = static_cast<long>(i * sizeof(uint32_t)) - static_cast<long>(before_dwords * sizeof(uint32_t));
        std::snprintf(
            buffer,
            sizeof(buffer),
            "%s%+ld=0x%08lX",
            out.empty() ? "" : " ",
            relative,
            static_cast<unsigned long>(values[i]));
        out += buffer;
    }
    return out;
}

void log_xanim_name_reference_detail(const char* target_name, uintptr_t name_addr, uintptr_t ref_addr)
{
    unsigned long rva = 0;
    const char* module_name = module_name_for_addr(ref_addr, &rva);
    const std::string dwords = format_dword_window(ref_addr, 4, 10);
    log_line(
        "xanim_name_ref_detail asset=%s nameAddr=0x%08lX refAddr=0x%08lX module=%s rva=0x%08lX dwords=%s",
        target_name ? target_name : "<null>",
        static_cast<unsigned long>(name_addr),
        static_cast<unsigned long>(ref_addr),
        module_name,
        rva,
        dwords.empty() ? "<unreadable>" : dwords.c_str());
    log_bytes_around("xanim_name_ref_bytes", ref_addr, 16, 48);
}

void log_named_asset_reference_detail(const char* prefix, const char* target_name, uintptr_t name_addr, uintptr_t ref_addr)
{
    unsigned long rva = 0;
    const char* module_name = module_name_for_addr(ref_addr, &rva);
    const std::string dwords = format_dword_window(ref_addr, 4, 10);
    log_line(
        "%s_name_ref_detail asset=%s nameAddr=0x%08lX refAddr=0x%08lX module=%s rva=0x%08lX dwords=%s",
        prefix ? prefix : "asset",
        target_name ? target_name : "<null>",
        static_cast<unsigned long>(name_addr),
        static_cast<unsigned long>(ref_addr),
        module_name,
        rva,
        dwords.empty() ? "<unreadable>" : dwords.c_str());
    char bytes_prefix[64] {};
    std::snprintf(bytes_prefix, sizeof(bytes_prefix), "%s_name_ref_bytes", prefix ? prefix : "asset");
    log_bytes_around(bytes_prefix, ref_addr, 16, 48);

    int pointer_logs = 0;
    for (int slot = -4; slot <= 12; ++slot)
    {
        const intptr_t signed_slot_addr = static_cast<intptr_t>(ref_addr) + static_cast<intptr_t>(slot * static_cast<int>(sizeof(DWORD)));
        if (signed_slot_addr <= 0)
            continue;
        const uintptr_t slot_addr = static_cast<uintptr_t>(signed_slot_addr);
        DWORD value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)))
            continue;
        if (!value || !pointer_readable(value))
            continue;

        unsigned long value_rva = 0;
        const char* value_module = module_name_for_addr(static_cast<uintptr_t>(value), &value_rva);
        const std::string value_text = safe_read_ascii_string(static_cast<uintptr_t>(value), 48);
        if (std::strcmp(value_module, "<unknown>") == 0 && value_text.empty())
            continue;

        log_line(
            "%s_name_ref_ptr asset=%s refAddr=0x%08lX slot=%+d slotAddr=0x%08lX value=0x%08lX module=%s rva=0x%08lX text=%s",
            prefix ? prefix : "asset",
            target_name ? target_name : "<null>",
            static_cast<unsigned long>(ref_addr),
            slot,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(value),
            value_module,
            value_rva,
            value_text.empty() ? "<none>" : value_text.c_str());

        ++pointer_logs;
        if (prefix && std::strcmp(prefix, "xmodel") == 0 && pointer_logs <= 4)
        {
            const std::string value_dwords = format_dword_window(static_cast<uintptr_t>(value), 4, 10);
            log_line(
                "%s_name_ref_deref asset=%s refAddr=0x%08lX slot=%+d value=0x%08lX dwords=%s",
                prefix,
                target_name ? target_name : "<null>",
                static_cast<unsigned long>(ref_addr),
                slot,
                static_cast<unsigned long>(value),
                value_dwords.empty() ? "<unreadable>" : value_dwords.c_str());

            char deref_bytes_prefix[64] {};
            std::snprintf(deref_bytes_prefix, sizeof(deref_bytes_prefix), "%s_name_ref_deref_bytes", prefix);
            log_bytes_around(deref_bytes_prefix, static_cast<uintptr_t>(value), 16, 48);

            int nested_logs = 0;
            for (int nested_slot = -4; nested_slot <= 12; ++nested_slot)
            {
                const intptr_t nested_slot_addr_signed = static_cast<intptr_t>(value) + static_cast<intptr_t>(nested_slot * static_cast<int>(sizeof(DWORD)));
                if (nested_slot_addr_signed <= 0)
                    continue;

                const uintptr_t nested_slot_addr = static_cast<uintptr_t>(nested_slot_addr_signed);
                DWORD nested_value = 0;
                if (!safe_copy_memory(nested_slot_addr, &nested_value, sizeof(nested_value)))
                    continue;
                if (!nested_value || !pointer_readable(nested_value))
                    continue;

                unsigned long nested_rva = 0;
                const char* nested_module = module_name_for_addr(static_cast<uintptr_t>(nested_value), &nested_rva);
                const std::string nested_text = safe_read_ascii_string(static_cast<uintptr_t>(nested_value), 48);
                if (std::strcmp(nested_module, "<unknown>") == 0 && nested_text.empty())
                    continue;

                log_line(
                    "%s_name_ref_deref_ptr asset=%s refAddr=0x%08lX slot=%+d value=0x%08lX nestedSlot=%+d nestedAddr=0x%08lX nestedValue=0x%08lX module=%s rva=0x%08lX text=%s",
                    prefix,
                    target_name ? target_name : "<null>",
                    static_cast<unsigned long>(ref_addr),
                    slot,
                    static_cast<unsigned long>(value),
                    nested_slot,
                    static_cast<unsigned long>(nested_slot_addr),
                    static_cast<unsigned long>(nested_value),
                    nested_module,
                    nested_rva,
                    nested_text.empty() ? "<none>" : nested_text.c_str());

                ++nested_logs;
                if (nested_logs >= 8)
                    break;
            }
        }
        if (pointer_logs >= 10)
            break;
    }

    if (prefix && std::strcmp(prefix, "xmodel") == 0)
    {
        struct XmodelCandidate
        {
            uintptr_t candidate_addr {};
            size_t name_field_offset {};
            uint32_t struct_hash {};
            int readable_ptr_slots {};
            int module_ptr_slots {};
            int string_ptr_slots {};
            int nonzero_dwords {};
            int zero_dwords {};
        };

        std::vector<XmodelCandidate> candidates;
        std::unordered_set<uintptr_t> seen_candidate_addrs;
        constexpr size_t kCandidateWindow = 0x80;
        constexpr size_t kCandidateBacktrack = 0x40;

        for (size_t name_field_offset = 0; name_field_offset <= kCandidateBacktrack; name_field_offset += sizeof(DWORD))
        {
            if (ref_addr < name_field_offset)
                continue;

            const uintptr_t candidate_addr = ref_addr - name_field_offset;
            if (!seen_candidate_addrs.insert(candidate_addr).second)
                continue;
            if (!pointer_readable(candidate_addr, kCandidateWindow))
                continue;

            unsigned char candidate_bytes[kCandidateWindow] {};
            if (!safe_copy_memory(candidate_addr, candidate_bytes, sizeof(candidate_bytes)))
                continue;

            DWORD observed_name_addr = 0;
            std::memcpy(&observed_name_addr, candidate_bytes + name_field_offset, sizeof(observed_name_addr));
            if (observed_name_addr != static_cast<DWORD>(name_addr))
                continue;

            XmodelCandidate candidate;
            candidate.candidate_addr = candidate_addr;
            candidate.name_field_offset = name_field_offset;
            candidate.struct_hash = fnv1a_hash_bytes(candidate_bytes, sizeof(candidate_bytes));
            for (size_t offset = 0; offset + sizeof(DWORD) <= sizeof(candidate_bytes); offset += sizeof(DWORD))
            {
                DWORD value = 0;
                std::memcpy(&value, candidate_bytes + offset, sizeof(value));
                if (!value)
                {
                    ++candidate.zero_dwords;
                    continue;
                }
                ++candidate.nonzero_dwords;
                if (!pointer_readable(static_cast<uintptr_t>(value)))
                    continue;

                ++candidate.readable_ptr_slots;
                unsigned long value_rva = 0;
                const char* value_module = module_name_for_addr(static_cast<uintptr_t>(value), &value_rva);
                const std::string value_text = safe_read_ascii_string(static_cast<uintptr_t>(value), 64);
                if (std::strcmp(value_module, "<unknown>") != 0)
                    ++candidate.module_ptr_slots;
                if (!value_text.empty())
                    ++candidate.string_ptr_slots;
            }

            if (candidate.readable_ptr_slots < 2 && candidate.string_ptr_slots == 0)
                continue;
            candidates.push_back(candidate);
        }

        std::sort(candidates.begin(), candidates.end(), [](const XmodelCandidate& a, const XmodelCandidate& b)
        {
            if (a.readable_ptr_slots != b.readable_ptr_slots)
                return a.readable_ptr_slots > b.readable_ptr_slots;
            if (a.module_ptr_slots != b.module_ptr_slots)
                return a.module_ptr_slots > b.module_ptr_slots;
            if (a.string_ptr_slots != b.string_ptr_slots)
                return a.string_ptr_slots > b.string_ptr_slots;
            return a.name_field_offset < b.name_field_offset;
        });

        const size_t max_candidates = std::min<size_t>(3, candidates.size());
        for (size_t candidate_index = 0; candidate_index < max_candidates; ++candidate_index)
        {
            const XmodelCandidate& candidate = candidates[candidate_index];
            unsigned long candidate_rva = 0;
            const char* candidate_module = module_name_for_addr(candidate.candidate_addr, &candidate_rva);
            log_line(
                "xmodel_candidate asset=%s refAddr=0x%08lX candidate=0x%08lX module=%s rva=0x%08lX nameFieldOff=0x%02lX structHash=0x%08lX readablePtrs=%d modulePtrs=%d stringPtrs=%d nonzeroDwords=%d zeroDwords=%d",
                target_name ? target_name : "<null>",
                static_cast<unsigned long>(ref_addr),
                static_cast<unsigned long>(candidate.candidate_addr),
                candidate_module,
                candidate_rva,
                static_cast<unsigned long>(candidate.name_field_offset),
                static_cast<unsigned long>(candidate.struct_hash),
                candidate.readable_ptr_slots,
                candidate.module_ptr_slots,
                candidate.string_ptr_slots,
                candidate.nonzero_dwords,
                candidate.zero_dwords);

            log_bytes_around("xmodel_candidate_bytes", candidate.candidate_addr, 0, kCandidateWindow);

            int detail_logs = 0;
            for (size_t slot_offset = 0; slot_offset < kCandidateWindow; slot_offset += sizeof(DWORD))
            {
                DWORD value = 0;
                if (!safe_copy_memory(candidate.candidate_addr + slot_offset, &value, sizeof(value)))
                    continue;
                if (!value || !pointer_readable(static_cast<uintptr_t>(value)))
                    continue;

                unsigned long value_rva = 0;
                const char* value_module = module_name_for_addr(static_cast<uintptr_t>(value), &value_rva);
                const std::string value_text = safe_read_ascii_string(static_cast<uintptr_t>(value), 64);
                if (std::strcmp(value_module, "<unknown>") == 0 && value_text.empty())
                    continue;

                log_line(
                    "xmodel_candidate_ptr asset=%s candidate=0x%08lX slotOff=0x%02lX value=0x%08lX module=%s rva=0x%08lX text=%s",
                    target_name ? target_name : "<null>",
                    static_cast<unsigned long>(candidate.candidate_addr),
                    static_cast<unsigned long>(slot_offset),
                    static_cast<unsigned long>(value),
                    value_module,
                    value_rva,
                    value_text.empty() ? "<none>" : value_text.c_str());

                if (detail_logs < 4)
                {
                    const std::string value_dwords = format_dword_window(static_cast<uintptr_t>(value), 2, 8);
                    log_line(
                        "xmodel_candidate_ptr_deref asset=%s candidate=0x%08lX slotOff=0x%02lX value=0x%08lX dwords=%s",
                        target_name ? target_name : "<null>",
                        static_cast<unsigned long>(candidate.candidate_addr),
                        static_cast<unsigned long>(slot_offset),
                        static_cast<unsigned long>(value),
                        value_dwords.empty() ? "<unreadable>" : value_dwords.c_str());
                }

                ++detail_logs;
                if (detail_logs >= 8)
                    break;
            }
        }
    }
}

void log_register_block(const CONTEXT& ctx)
{
    log_line("regs eip=0x%08lX eax=0x%08lX ebx=0x%08lX ecx=0x%08lX edx=0x%08lX esi=0x%08lX edi=0x%08lX ebp=0x%08lX esp=0x%08lX",
        ctx.Eip, ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx, ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp);
}

void log_pointer_info(const char* name, uintptr_t value)
{
    __try
    {
        MEMORY_BASIC_INFORMATION mbi {};
        const SIZE_T q = VirtualQuery(reinterpret_cast<void*>(value), &mbi, sizeof(mbi));
        const char* module_name = "<unknown>";
        unsigned long rva = 0;
        for (const auto& module : g_modules)
        {
            const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
            if (value >= base && value < base + module.size)
            {
                module_name = module.name.c_str();
                rva = static_cast<unsigned long>(value - base);
                break;
            }
        }
        log_line("%s addr=0x%08lX module=%s%s%08lX", name, static_cast<unsigned long>(value), module_name, std::strcmp(module_name, "<unknown>") ? " rva=0x" : "", rva);
        if (!q || !mbi.BaseAddress)
            return;
        log_line("%s mem base=0x%08lX size=0x%08lX protect=0x%08lX type=0x%08lX state=0x%08lX",
            name,
            static_cast<unsigned long>(reinterpret_cast<uintptr_t>(mbi.BaseAddress)),
            static_cast<unsigned long>(mbi.RegionSize),
            static_cast<unsigned long>(mbi.Protect),
            static_cast<unsigned long>(mbi.Type),
            static_cast<unsigned long>(mbi.State));
        if (mbi.State != MEM_COMMIT)
            return;
        if ((mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
            return;
        DWORD dword = 0;
        if (safe_copy_memory(value, &dword, sizeof(dword)))
            log_line("%s dword=0x%08lX", name, dword);
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        log_line("%s pointer_info_fault addr=0x%08lX", name, static_cast<unsigned long>(value));
    }
}

const char* module_name_for_addr(uintptr_t value, unsigned long* rva_out = nullptr)
{
    for (const auto& module : g_modules)
    {
        const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
        if (value >= base && value < base + module.size)
        {
            if (rva_out)
                *rva_out = static_cast<unsigned long>(value - base);
            return module.name.c_str();
        }
    }
    if (rva_out)
        *rva_out = 0;
    return "<unknown>";
}

const ModuleInfoLite* module_info_for_addr(uintptr_t value)
{
    for (const auto& module : g_modules)
    {
        const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
        const uintptr_t end = base + static_cast<uintptr_t>(module.size);
        if (value >= base && value < end)
            return &module;
    }
    return nullptr;
}

std::string safe_read_ascii_string(uintptr_t addr, size_t max_chars = 96)
{
    if (!addr || max_chars == 0)
        return {};

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(addr), &mbi, sizeof(mbi)))
        return {};
    if (!region_is_readable(mbi))
        return {};

    std::string out;
    out.reserve(max_chars);
    for (size_t i = 0; i < max_chars; ++i)
    {
        char c = 0;
        if (!safe_copy_memory(addr + i, &c, sizeof(c)))
            break;
        if (c == '\0')
            break;
        const unsigned char uc = static_cast<unsigned char>(c);
        if (uc < 0x20 || uc > 0x7E)
            return {};
        out.push_back(c);
    }

    if (out.size() < 3)
        return {};
    return out;
}

const char* watched_asset_kind(const std::string& text)
{
    const std::string lower = to_lower_copy(text);
    if (g_watch_xmodels.find(lower) != g_watch_xmodels.end())
        return "xmodel";
    if (g_watch_xanims.find(lower) != g_watch_xanims.end())
        return "xanim";
    return nullptr;
}

void log_watched_asset_pointers_near(const char* context, uintptr_t base_addr, int before_slots = 8, int after_slots = 16)
{
    if (!context || !base_addr)
        return;

    int hit_count = 0;
    for (int slot = -before_slots; slot <= after_slots; ++slot)
    {
        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(slot * static_cast<int>(sizeof(uint32_t)));
        uint32_t value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)) || !value)
            continue;

        const std::string text = safe_read_ascii_string(static_cast<uintptr_t>(value), 64);
        const char* kind = watched_asset_kind(text);
        if (!kind)
            continue;

        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(static_cast<uintptr_t>(value), &rva);
        log_line(
            "consumer_watch_hit context=%s base=0x%08lX slot=%+d slotAddr=0x%08lX value=0x%08lX kind=%s module=%s%s%08lX text=%s",
            context,
            static_cast<unsigned long>(base_addr),
            slot,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(value),
            kind,
            module_name,
            std::strcmp(module_name, "<unknown>") ? " rva=0x" : "",
            rva,
            text.c_str());

        if (++hit_count >= 12)
            break;
    }
}

void log_dword_window(const char* context, uintptr_t base_addr, int before_slots = 4, int after_slots = 8)
{
    if (!context || !base_addr)
        return;

    for (int slot = -before_slots; slot <= after_slots; ++slot)
    {
        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(slot * static_cast<int>(sizeof(uint32_t)));
        uint32_t value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)))
            continue;

        log_line(
            "consumer_dword context=%s base=0x%08lX slot=%+d slotAddr=0x%08lX value=0x%08lX",
            context,
            static_cast<unsigned long>(base_addr),
            slot,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(value));
    }
}

std::string consumer_ascii4(uint32_t value)
{
    std::string out;
    out.reserve(4);
    for (int i = 0; i < 4; ++i)
    {
        const unsigned char c = static_cast<unsigned char>((value >> (i * 8)) & 0xFF);
        if (c < 0x20 || c > 0x7E)
            return {};
        out.push_back(static_cast<char>(c));
    }
    return out;
}

bool classify_consumer_module_pointer(uintptr_t value, std::string* detail_out)
{
    if (detail_out)
        detail_out->clear();

    unsigned long rva = 0;
    const char* module_name = module_name_for_addr(value, &rva);
    if (std::strcmp(module_name, "<unknown>") == 0)
        return false;

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(value), &mbi, sizeof(mbi)))
        return false;
    if (mbi.State != MEM_COMMIT || mbi.Type != MEM_IMAGE)
        return false;
    if ((mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
        return false;

    if (detail_out)
    {
        char buffer[128] {};
        std::snprintf(
            buffer,
            sizeof(buffer),
            "%s:rva=0x%08lX memBase=0x%08lX protect=0x%08lX",
            module_name,
            rva,
            static_cast<unsigned long>(reinterpret_cast<uintptr_t>(mbi.BaseAddress)),
            static_cast<unsigned long>(mbi.Protect));
        *detail_out = buffer;
    }
    return true;
}

std::string classify_consumer_value(uint32_t value, std::string* detail_out = nullptr)
{
    if (detail_out)
        detail_out->clear();
    if (!value)
        return "zero";

    float as_float = 0.0f;
    std::memcpy(&as_float, &value, sizeof(as_float));
    if (std::isfinite(as_float) && std::fabs(as_float) >= 0.0001f && std::fabs(as_float) <= 100000.0f)
    {
        if (detail_out)
        {
            char buffer[64] {};
            std::snprintf(buffer, sizeof(buffer), "float=%0.6f", static_cast<double>(as_float));
            *detail_out = buffer;
        }
        return "float";
    }

    const std::string ascii = consumer_ascii4(value);
    if (!ascii.empty())
    {
        if (detail_out)
            *detail_out = ascii;
        return "ascii4";
    }

    if (value <= 0xFFFFu)
    {
        if (detail_out)
        {
            char buffer[32] {};
            std::snprintf(buffer, sizeof(buffer), "u=%lu", static_cast<unsigned long>(value));
            *detail_out = buffer;
        }
        return "small_int";
    }

    if (classify_consumer_module_pointer(static_cast<uintptr_t>(value), detail_out))
        return "ptr_module";

    MEMORY_BASIC_INFORMATION mbi {};
    if (VirtualQuery(reinterpret_cast<void*>(static_cast<uintptr_t>(value)), &mbi, sizeof(mbi)) &&
        region_is_readable(mbi))
    {
        if (detail_out)
        {
            char buffer[128] {};
            std::snprintf(
                buffer,
                sizeof(buffer),
                "memBase=0x%08lX protect=0x%08lX type=0x%08lX",
                static_cast<unsigned long>(reinterpret_cast<uintptr_t>(mbi.BaseAddress)),
                static_cast<unsigned long>(mbi.Protect),
                static_cast<unsigned long>(mbi.Type));
            *detail_out = buffer;
        }
        return mbi.Type == MEM_PRIVATE ? "ptr_heap" : "ptr_region";
    }

    if (detail_out)
    {
        char buffer[32] {};
        std::snprintf(buffer, sizeof(buffer), "u=%lu", static_cast<unsigned long>(value));
        *detail_out = buffer;
    }
    return "int_or_flags";
}

bool classify_consumer_pointer_target(uint32_t value, std::string* kind_out, std::string* detail_out = nullptr)
{
    if (kind_out)
        kind_out->clear();
    if (detail_out)
        detail_out->clear();
    if (!value)
        return false;

    std::string detail;
    if (classify_consumer_module_pointer(static_cast<uintptr_t>(value), &detail))
    {
        if (kind_out)
            *kind_out = "ptr_module";
        if (detail_out)
            *detail_out = detail;
        return true;
    }

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(static_cast<uintptr_t>(value)), &mbi, sizeof(mbi)) ||
        !region_is_readable(mbi))
    {
        return false;
    }

    if (detail_out)
    {
        char buffer[128] {};
        std::snprintf(
            buffer,
            sizeof(buffer),
            "memBase=0x%08lX protect=0x%08lX type=0x%08lX",
            static_cast<unsigned long>(reinterpret_cast<uintptr_t>(mbi.BaseAddress)),
            static_cast<unsigned long>(mbi.Protect),
            static_cast<unsigned long>(mbi.Type));
        *detail_out = buffer;
    }
    if (kind_out)
        *kind_out = mbi.Type == MEM_PRIVATE ? "ptr_heap" : "ptr_region";
    return true;
}

bool is_pointer_like_value(uint32_t value)
{
    std::string kind;
    if (!classify_consumer_pointer_target(value, &kind))
        return false;
    return kind == "ptr_heap" || kind == "ptr_region" || kind == "ptr_module";
}

bool is_selector_root_pointer_value(uint32_t value)
{
    std::string kind;
    if (!classify_consumer_pointer_target(value, &kind))
        return false;
    return kind == "ptr_heap" || kind == "ptr_module";
}

bool looks_like_selector_root(uintptr_t base)
{
    if (!base)
        return false;

    uint32_t slots[8] {};
    if (!safe_copy_memory(base, slots, sizeof(slots)))
        return false;

    if (!is_selector_root_pointer_value(slots[2]) || !is_selector_root_pointer_value(slots[3]))
        return false;
    if (slots[4] && !is_selector_root_pointer_value(slots[4]))
        return false;
    if (slots[5] && !is_known_materialization_plus5_value(slots[5]))
        return false;
    if (slots[6] && !is_known_materialization_plus6_value(slots[6]))
        return false;

    std::string kind5;
    std::string kind6;
    classify_consumer_value(slots[5], &kind5);
    classify_consumer_value(slots[6], &kind6);
    if (kind5.rfind("ptr_", 0) == 0 || kind6.rfind("ptr_", 0) == 0)
        return false;

    return true;
}

bool is_known_materialization_plus5_value(uint32_t value)
{
    switch (value)
    {
    case 0x00070101:
    case 0x01030105:
    case 0x01070105:
    case 0x00010101:
    case 0x00020101:
    case 0x00120105:
    case 0x01150105:
        return true;
    default:
        return false;
    }
}

bool is_known_materialization_plus6_value(uint32_t value)
{
    return value == 0x00000201 || value == 0x00000203;
}

bool has_known_class_head_prefix(uintptr_t addr)
{
    if (!addr || !pointer_readable(addr, 4 * sizeof(uint32_t)))
        return false;

    uint32_t dwords[4] {};
    if (!safe_copy_memory(addr, dwords, sizeof(dwords)))
        return false;

    if (dwords[0] != 0x706D6970 ||  // "pimp"
        dwords[1] != 0x6365745F ||  // "_tec"
        dwords[2] != 0x71696E68)    // "hinq"
    {
        return false;
    }

    return dwords[3] == 0x735F6575 || // "ue_s"
           dwords[3] == 0x6C5F6575;   // "ue_l"
}

uintptr_t find_function_prologue_near(uintptr_t addr, size_t max_back)
{
    if (!addr || max_back < 3)
        return 0;

    const uintptr_t start = addr > max_back ? addr - max_back : 0;
    const size_t span = addr - start;
    if (span < 3)
        return 0;

    std::vector<unsigned char> buffer(span, 0);
    if (!safe_copy_memory(start, buffer.data(), span))
        return 0;

    for (size_t i = span - 3; i > 0; --i)
    {
        if (buffer[i] == 0x55 && buffer[i + 1] == 0x8B && buffer[i + 2] == 0xEC)
            return start + i;
    }

    return 0;
}

bool looks_like_temporal_selector_root_candidate(
    uintptr_t base,
    uint32_t* plus1_out = nullptr,
    uint32_t* plus2_out = nullptr,
    uint32_t* plus3_out = nullptr,
    uint32_t* plus4_out = nullptr,
    uint32_t* plus5_out = nullptr,
    uint32_t* plus6_out = nullptr,
    uint32_t* plus7_out = nullptr,
    uint32_t* plus8_out = nullptr)
{
    if (!base)
        return false;

    uint32_t slots[9] {};
    if (!safe_copy_memory(base, slots, sizeof(slots)))
        return false;

    const uint32_t plus1 = slots[1];
    const uint32_t plus2 = slots[2];
    const uint32_t plus3 = slots[3];
    const uint32_t plus4 = slots[4];
    const uint32_t plus5 = slots[5];
    const uint32_t plus6 = slots[6];
    const uint32_t plus7 = slots[7];
    const uint32_t plus8 = slots[8];
    const uint32_t self_plus_0x20 = static_cast<uint32_t>(base + 0x20);
    const uint32_t self_plus_0x30 = static_cast<uint32_t>(base + 0x30);
    const bool slot3_self = plus3 == self_plus_0x20;
    const bool slot4_self = plus4 == self_plus_0x20;

    if (!is_pointer_like_value(slots[0]))
        return false;
    if (!has_known_class_head_prefix(slots[0]))
        return false;
    if (plus1 != 0x00010080)
        return false;
    if (!is_pointer_like_value(plus2))
        return false;
    if (!slot3_self && plus3 != 0 && !is_pointer_like_value(plus3))
        return false;
    if (!slot4_self && plus4 != 0 && !is_pointer_like_value(plus4))
        return false;
    if (!slot3_self && !slot4_self)
        return false;
    if (plus5 != 0 && !is_known_materialization_plus5_value(plus5))
        return false;
    if (plus6 != 0 && !is_known_materialization_plus6_value(plus6))
        return false;
    if (plus7 && !is_pointer_like_value(plus7))
        return false;
    if (plus8 && plus8 != self_plus_0x30)
        return false;

    std::string kind5;
    std::string kind6;
    classify_consumer_value(plus5, &kind5);
    classify_consumer_value(plus6, &kind6);
    if (kind5.rfind("ptr_", 0) == 0 || kind6.rfind("ptr_", 0) == 0)
        return false;

    if (plus1_out)
        *plus1_out = plus1;
    if (plus2_out)
        *plus2_out = plus2;
    if (plus3_out)
        *plus3_out = plus3;
    if (plus4_out)
        *plus4_out = plus4;
    if (plus5_out)
        *plus5_out = plus5;
    if (plus6_out)
        *plus6_out = plus6;
    if (plus7_out)
        *plus7_out = plus7;
    if (plus8_out)
        *plus8_out = plus8;
    return true;
}

void record_temporal_selector_root_candidate_locked(uintptr_t addr, const char* reason)
{
    uint32_t plus1 = 0;
    uint32_t plus2 = 0;
    uint32_t plus3 = 0;
    uint32_t plus4 = 0;
    uint32_t plus5 = 0;
    uint32_t plus6 = 0;
    uint32_t plus7 = 0;
    uint32_t plus8 = 0;
    if (!looks_like_temporal_selector_root_candidate(addr, &plus1, &plus2, &plus3, &plus4, &plus5, &plus6, &plus7, &plus8))
        return;

    const DWORD now = GetTickCount();
    auto& obs = g_temporal_selector_roots[addr];
    const bool first_seen = obs.addr == 0;
    if (first_seen)
    {
        obs.addr = addr;
        obs.page_base = addr & ~(static_cast<uintptr_t>(g_system_info.dwPageSize) - 1u);
        obs.first_tick = now;
    }
    obs.last_tick = now;
    obs.sightings += 1;
    obs.plus1 = plus1;
    obs.plus2 = plus2;
    obs.plus3 = plus3;
    obs.plus4 = plus4;
    obs.plus5 = plus5;
    obs.plus6 = plus6;
    obs.plus7 = plus7;
    obs.plus8 = plus8;

    if (first_seen)
    {
        log_line("selector_root_temporal_first_seen reason=%s addr=0x%08lX page=0x%08lX tick=%lu plus3=0x%08lX plus4=0x%08lX plus5=0x%08lX plus6=0x%08lX plus8=0x%08lX",
            reason ? reason : "scan",
            static_cast<unsigned long>(addr),
            static_cast<unsigned long>(obs.page_base),
            static_cast<unsigned long>(now),
            static_cast<unsigned long>(plus3),
            static_cast<unsigned long>(plus4),
            static_cast<unsigned long>(plus5),
            static_cast<unsigned long>(plus6),
            static_cast<unsigned long>(plus8));
        log_line("selector_root_temporal_shape reason=%s addr=0x%08lX plus1=0x%08lX plus2=0x%08lX plus3=0x%08lX plus4=0x%08lX plus5=0x%08lX plus6=0x%08lX plus7=0x%08lX plus8=0x%08lX",
            reason ? reason : "scan",
            static_cast<unsigned long>(addr),
            static_cast<unsigned long>(plus1),
            static_cast<unsigned long>(plus2),
            static_cast<unsigned long>(plus3),
            static_cast<unsigned long>(plus4),
            static_cast<unsigned long>(plus5),
            static_cast<unsigned long>(plus6),
            static_cast<unsigned long>(plus7),
            static_cast<unsigned long>(plus8));
        log_selector_root_compact_snapshot("temporal_first_seen", reason ? reason : "scan", addr);
    }

    if (!obs.watch_armed && !g_consumer_first_hit_logged.load())
    {
        arm_selector_root_policy_watches_locked("temporal_pre_hit", addr);
        obs.watch_armed = true;
        log_line("selector_root_temporal_watch_armed reason=%s addr=0x%08lX tick=%lu",
            reason ? reason : "scan",
            static_cast<unsigned long>(addr),
            static_cast<unsigned long>(now));
    }
}

bool maybe_arm_selector_root_from_candidate(const char* phase, const char* label, uintptr_t candidate)
{
    if (!candidate)
        return false;
    if (!looks_like_selector_root(candidate))
        return false;

    arm_selector_root_policy_watches_locked(phase ? phase : "candidate", candidate);
    log_selector_root_compact_snapshot("asset_lookup_candidate", phase ? phase : "candidate", candidate);
    log_line("policy_write_candidate label=%s phase=%s selector_root=0x%08lX",
        label ? label : "unknown",
        phase ? phase : "candidate",
        static_cast<unsigned long>(candidate));
    return true;
}

bool maybe_arm_selector_root_from_pointer_family_locked(const char* phase, const char* label, uintptr_t base, int max_slots)
{
    if (!base || max_slots < 0)
        return false;

    bool armed = false;
    const size_t bytes = static_cast<size_t>(max_slots + 1) * sizeof(uint32_t);
    if (!pointer_readable(base, bytes))
        return false;

    for (int slot = 0; slot <= max_slots; ++slot)
    {
        uint32_t value = 0;
        if (!safe_copy_memory(base + (slot * sizeof(uint32_t)), &value, sizeof(value)))
            continue;

        char reason[96] {};
        if (label && *label)
            std::snprintf(reason, sizeof(reason), "%s_slot%d", label, slot);
        else
            std::snprintf(reason, sizeof(reason), "slot%d", slot);

        record_temporal_selector_root_candidate_locked(value, reason);
        armed = maybe_arm_selector_root_from_candidate(phase, reason, value) || armed;
    }
    return armed;
}

void probe_entry_selector_root_candidates_locked(const char* phase, const CONTEXT& ctx)
{
    const char* resolved_phase = phase ? phase : "asset_lookup_entry";
    bool armed = false;

    const struct RegisterCandidate
    {
        const char* label;
        uintptr_t value;
    } candidates[] = {
        {"edi", ctx.Edi},
        {"esi", ctx.Esi},
        {"eax", ctx.Eax},
        {"ecx", ctx.Ecx},
        {"edx", ctx.Edx},
    };

    for (const auto& candidate : candidates)
    {
        if (!candidate.value)
            continue;
        record_temporal_selector_root_candidate_locked(candidate.value, candidate.label);
        armed = maybe_arm_selector_root_from_candidate(resolved_phase, candidate.label, candidate.value) || armed;
    }

    for (const auto& candidate : candidates)
    {
        if (!candidate.value)
            continue;
        armed = maybe_arm_selector_root_from_pointer_family_locked(resolved_phase, candidate.label, candidate.value, 4) || armed;
    }

    if (!armed && g_latest_materialization_producer.class_head)
    {
        record_temporal_selector_root_candidate_locked(g_latest_materialization_producer.class_head, "class_head");
        maybe_arm_selector_root_from_candidate(resolved_phase, "class_head", g_latest_materialization_producer.class_head);
        maybe_arm_selector_root_from_pointer_family_locked(resolved_phase, "class_head", g_latest_materialization_producer.class_head, 4);
    }
}

void arm_asset_lookup_callsite_traces_locked()
{
    const uintptr_t target = rva_to_va(kConsumerAssetClassLookupRva);
    unsigned armed = 0;
    const unsigned max_callsites = 8;
    for (const auto& module : g_modules)
    {
        const uintptr_t base = reinterpret_cast<uintptr_t>(module.base);
        const size_t size = static_cast<size_t>(module.size);
        if (!base || size < 5)
            continue;
        const uintptr_t end = base + size;
        uintptr_t cursor = base;
        const size_t chunk_size = 0x20000;
        while (cursor + 5 <= end)
        {
            MEMORY_BASIC_INFORMATION mbi {};
            if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
                break;

            const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
            const uintptr_t region_end = region_base + mbi.RegionSize;
            const bool readable = region_is_readable(mbi);
            const bool executable = (mbi.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY)) != 0;
            if (!readable || !executable)
            {
                cursor = region_end;
                continue;
            }

            uintptr_t scan_cursor = cursor;
            const uintptr_t scan_end = std::min<uintptr_t>(region_end, end);
            while (scan_cursor + 5 <= scan_end)
            {
                const size_t bytes_to_copy = static_cast<size_t>(std::min<uintptr_t>(scan_end - scan_cursor, chunk_size));
                std::vector<unsigned char> buffer(bytes_to_copy, 0);
                if (!safe_copy_memory(scan_cursor, buffer.data(), bytes_to_copy))
                {
                    scan_cursor += chunk_size;
                    continue;
                }

                for (size_t offset = 0; offset + 5 <= bytes_to_copy; ++offset)
                {
                    if (buffer[offset] != 0xE8)
                        continue;
                    const int32_t rel = *reinterpret_cast<const int32_t*>(buffer.data() + offset + 1);
                    const uintptr_t callsite = scan_cursor + offset;
                    const uintptr_t dest = callsite + 5 + static_cast<int64_t>(rel);
                    if (dest != target)
                        continue;

                    arm_exec_trace_locked("consumer_asset_lookup_callsite", callsite, 0, "consumer_probe", 2);
                    log_line("asset_lookup_callsite_found addr=0x%08lX rel=0x%08lX target=0x%08lX module=%s",
                        static_cast<unsigned long>(callsite),
                        static_cast<unsigned long>(rel),
                        static_cast<unsigned long>(dest),
                        module.name.c_str());
                    if (++armed >= max_callsites)
                        return;
                }
                scan_cursor += bytes_to_copy;
            }
            cursor = region_end;
        }
    }

    log_line("asset_lookup_callsite_scan_empty target=0x%08lX modules=%u",
        static_cast<unsigned long>(target),
        static_cast<unsigned>(g_modules.size()));
}

void log_consumer_typed_window(const char* context, const char* phase, uintptr_t base_addr, int before_slots, int after_slots)
{
    if (!context || !phase || !base_addr)
        return;

    for (int slot = -before_slots; slot <= after_slots; ++slot)
    {
        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(slot * static_cast<int>(sizeof(uint32_t)));
        uint32_t value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)))
            continue;

        std::string detail;
        const std::string kind = classify_consumer_value(value, &detail);
        log_line(
            "consumer_slot_typed context=%s phase=%s base=0x%08lX slot=%+d slotAddr=0x%08lX value=0x%08lX kind=%s detail=%s",
            context,
            phase,
            static_cast<unsigned long>(base_addr),
            slot,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(value),
            kind.c_str(),
            detail.empty() ? "-" : detail.c_str());
    }
}

void log_consumer_pointer_chases(const char* context, const char* phase, uintptr_t base_addr, int before_slots, int after_slots)
{
    if (!context || !phase || !base_addr)
        return;

    int logged = 0;
    for (int slot = -before_slots; slot <= after_slots; ++slot)
    {
        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(slot * static_cast<int>(sizeof(uint32_t)));
        uint32_t value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)) || !value)
            continue;

        std::string detail;
        std::string kind;
        if (!classify_consumer_pointer_target(value, &kind, &detail))
            continue;
        if (!pointer_readable(static_cast<uintptr_t>(value), sizeof(uint32_t) * 4))
            continue;

        const uintptr_t target = static_cast<uintptr_t>(value);
        const std::vector<uint32_t> target_values = capture_dword_window_values(target, 0, 3);
        if (target_values.empty())
            continue;

        const uint32_t hash = fnv1a_hash_bytes(
            reinterpret_cast<const unsigned char*>(target_values.data()),
            target_values.size() * sizeof(uint32_t));

        log_line(
            "consumer_pointer_chase context=%s phase=%s slot=%+d slotAddr=0x%08lX target=0x%08lX kind=%s detail=%s hash=0x%08lX dword0=0x%08lX dword1=0x%08lX dword2=0x%08lX dword3=0x%08lX",
            context,
            phase,
            slot,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(target),
            kind.c_str(),
            detail.empty() ? "-" : detail.c_str(),
            static_cast<unsigned long>(hash),
            static_cast<unsigned long>(target_values.size() > 0 ? target_values[0] : 0),
            static_cast<unsigned long>(target_values.size() > 1 ? target_values[1] : 0),
            static_cast<unsigned long>(target_values.size() > 2 ? target_values[2] : 0),
            static_cast<unsigned long>(target_values.size() > 3 ? target_values[3] : 0));

        if (++logged >= 4)
            break;
    }
}

void log_consumer_pointer_chase_value(const char* context, const char* phase, int slot, uintptr_t slot_addr, uint32_t value)
{
    if (!context || !phase || !slot_addr || !value)
        return;

    std::string detail;
    std::string kind;
    if (!classify_consumer_pointer_target(value, &kind, &detail))
        return;
    if (!pointer_readable(static_cast<uintptr_t>(value), sizeof(uint32_t) * 4))
        return;

    const uintptr_t target = static_cast<uintptr_t>(value);
    const std::vector<uint32_t> target_values = capture_dword_window_values(target, 0, 3);
    if (target_values.empty())
        return;

    const uint32_t hash = fnv1a_hash_bytes(
        reinterpret_cast<const unsigned char*>(target_values.data()),
        target_values.size() * sizeof(uint32_t));

    log_line(
        "consumer_pointer_chase context=%s phase=%s slot=%+d slotAddr=0x%08lX target=0x%08lX kind=%s detail=%s hash=0x%08lX dword0=0x%08lX dword1=0x%08lX dword2=0x%08lX dword3=0x%08lX",
        context,
        phase,
        slot,
        static_cast<unsigned long>(slot_addr),
        static_cast<unsigned long>(target),
        kind.c_str(),
        detail.empty() ? "-" : detail.c_str(),
        static_cast<unsigned long>(hash),
        static_cast<unsigned long>(target_values.size() > 0 ? target_values[0] : 0),
        static_cast<unsigned long>(target_values.size() > 1 ? target_values[1] : 0),
        static_cast<unsigned long>(target_values.size() > 2 ? target_values[2] : 0),
        static_cast<unsigned long>(target_values.size() > 3 ? target_values[3] : 0));
}

void log_consumer_anchor_snapshot(const char* context, const char* phase, uintptr_t base_addr, int before_slots, int after_slots)
{
    if (!context || !phase || !base_addr)
        return;

    const bool minimal_consumer_focus = is_minimal_consumer_focus_mode();
    log_line(
        "consumer_anchor_snapshot context=%s phase=%s base=0x%08lX before=%d after=%d",
        context,
        phase,
        static_cast<unsigned long>(base_addr),
        before_slots,
        after_slots);
    log_pointer_info(context, base_addr);
    const std::string bytes_label = std::string(context) + "_snapshot_bytes";
    log_bytes_around(bytes_label.c_str(), base_addr, 16, 48);
    const std::vector<uint32_t> values = capture_dword_window_values(base_addr, before_slots, after_slots);
    log_dword_window(context, base_addr, before_slots, after_slots);
    log_consumer_typed_window(context, phase, base_addr, before_slots, after_slots);
    if (!values.empty())
    {
        const uint32_t hash = fnv1a_hash_bytes(
            reinterpret_cast<const unsigned char*>(values.data()),
            values.size() * sizeof(uint32_t));
        log_line(
            "consumer_anchor_hash context=%s phase=%s base=0x%08lX slots=%u hash=0x%08lX",
            context,
            phase,
            static_cast<unsigned long>(base_addr),
            static_cast<unsigned>(values.size()),
            static_cast<unsigned long>(hash));
    }
    if (!minimal_consumer_focus)
    {
        track_consumer_object_window(context, base_addr, before_slots, after_slots);
        log_consumer_dword_window_correlations(context, base_addr, before_slots, values);
        log_watched_asset_pointers_near(context, base_addr);
    }
    else
    {
        log_consumer_pointer_chases(context, phase, base_addr, before_slots, after_slots);
    }
    log_line(
        "consumer_anchor_snapshot_complete context=%s phase=%s base=0x%08lX",
        context,
        phase,
        static_cast<unsigned long>(base_addr));
}

void log_consumer_span_snapshot(const char* context, const char* phase, uintptr_t base_addr, int dword_count)
{
    if (!context || !phase || !base_addr || dword_count <= 0)
        return;

    log_line(
        "consumer_span_snapshot context=%s phase=%s base=0x%08lX dwords=%d",
        context,
        phase,
        static_cast<unsigned long>(base_addr),
        dword_count);

    log_pointer_info(context, base_addr);

    const size_t byte_count = static_cast<size_t>(dword_count) * sizeof(uint32_t);
    std::vector<uint32_t> values(static_cast<size_t>(dword_count), 0);
    const bool copied = safe_copy_memory(base_addr, values.data(), byte_count);
    if (!copied)
    {
        log_line(
            "consumer_span_snapshot_unreadable context=%s phase=%s base=0x%08lX dwords=%d",
            context,
            phase,
            static_cast<unsigned long>(base_addr),
            dword_count);
        return;
    }

    log_bytes_around((std::string(context) + "_span_bytes").c_str(), base_addr, 16, static_cast<int>(std::min<size_t>(byte_count, 96)));
    for (int i = 0; i < dword_count; ++i)
    {
        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(i * sizeof(uint32_t));
        const uint32_t value = values[static_cast<size_t>(i)];
        std::string detail;
        const std::string kind = classify_consumer_value(value, &detail);
        log_line(
            "consumer_slot_typed context=%s phase=%s base=0x%08lX slot=+%d slotAddr=0x%08lX value=0x%08lX kind=%s detail=%s",
            context,
            phase,
            static_cast<unsigned long>(base_addr),
            i,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(value),
            kind.c_str(),
            detail.empty() ? "-" : detail.c_str());
    }

    const uint32_t hash = fnv1a_hash_bytes(reinterpret_cast<const unsigned char*>(values.data()), byte_count);
    log_line(
        "consumer_anchor_hash context=%s phase=%s base=0x%08lX slots=%u hash=0x%08lX",
        context,
        phase,
        static_cast<unsigned long>(base_addr),
        static_cast<unsigned>(values.size()),
        static_cast<unsigned long>(hash));

    unsigned pointer_logs = 0;
    for (int i = 0; i < dword_count && pointer_logs < 8; ++i)
    {
        const uint32_t value = values[static_cast<size_t>(i)];
        std::string detail;
        const std::string kind = classify_consumer_value(value, &detail);
        if (kind != "ptr_heap" && kind != "ptr_region")
            continue;

        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(i * sizeof(uint32_t));
        log_consumer_pointer_chase_value(context, phase, i, slot_addr, value);
        ++pointer_logs;
    }

    log_line(
        "consumer_span_snapshot_complete context=%s phase=%s base=0x%08lX dwords=%d",
        context,
        phase,
        static_cast<unsigned long>(base_addr),
        dword_count);
}

void try_log_consumer_render_edi_family(const char* phase, uintptr_t edi, bool include_extended_children)
{
    if (!phase || !edi)
        return;

    log_line("consumer_render_edi_capture_attempt phase=%s edi=0x%08lX", phase, static_cast<unsigned long>(edi));

    __try
    {
        log_consumer_anchor_snapshot("render_state_edi_policy", phase, edi, 16, 8);
        log_consumer_anchor_snapshot("render_state_edi", phase, edi);
        DWORD child2_value = 0;
        DWORD child3_value = 0;
        DWORD child4_value = 0;
        DWORD child7_value = 0;

        if (safe_copy_memory(edi + (2 * sizeof(DWORD)), &child2_value, sizeof(child2_value)) && child2_value)
            log_consumer_anchor_snapshot("render_state_edi_child_2", phase, child2_value);
        if (safe_copy_memory(edi + (3 * sizeof(DWORD)), &child3_value, sizeof(child3_value)) && child3_value)
            log_consumer_anchor_snapshot("render_state_edi_child_3", phase, child3_value);
        if (include_extended_children)
        {
            if (safe_copy_memory(edi + (4 * sizeof(DWORD)), &child4_value, sizeof(child4_value)) && child4_value)
                log_consumer_anchor_snapshot("render_state_edi_child_4", phase, child4_value);
            if (safe_copy_memory(edi + (7 * sizeof(DWORD)), &child7_value, sizeof(child7_value)) && child7_value)
                log_consumer_anchor_snapshot("render_state_edi_child_7", phase, child7_value);
        }

        if (include_extended_children)
        {
            log_line(
                "consumer_joined_surface_materialized phase=%s edi=0x%08lX child2=0x%08lX child3=0x%08lX child4=0x%08lX child7=0x%08lX",
                phase,
                static_cast<unsigned long>(edi),
                static_cast<unsigned long>(child2_value),
                static_cast<unsigned long>(child3_value),
                static_cast<unsigned long>(child4_value),
                static_cast<unsigned long>(child7_value));
        }
        else
        {
            log_line(
                "consumer_joined_surface_materialized phase=%s edi=0x%08lX child2=0x%08lX child3=0x%08lX",
                phase,
                static_cast<unsigned long>(edi),
                static_cast<unsigned long>(child2_value),
                static_cast<unsigned long>(child3_value));
        }
    }
    __except(EXCEPTION_EXECUTE_HANDLER)
    {
        log_line(
            "consumer_render_edi_capture_exception phase=%s code=0x%08lX edi=0x%08lX",
            phase,
            static_cast<unsigned long>(GetExceptionCode()),
            static_cast<unsigned long>(edi));
    }
}

std::string observed_asset_key(const char* kind, const char* asset_name, uintptr_t addr, const char* source, uintptr_t related_addr)
{
    char buffer[4096] {};
    std::snprintf(
        buffer,
        sizeof(buffer),
        "%s|%s|0x%08lX|%s|0x%08lX",
        kind ? kind : "",
        asset_name ? asset_name : "",
        static_cast<unsigned long>(addr),
        source ? source : "",
        static_cast<unsigned long>(related_addr));
    return to_lower_copy(buffer);
}

void record_observed_asset_address(const char* kind, const char* asset_name, uintptr_t addr, const char* source, uintptr_t related_addr)
{
    if (!kind || !*kind || !asset_name || !*asset_name || !addr)
        return;

    const std::string key = observed_asset_key(kind, asset_name, addr, source, related_addr);
    bool inserted = false;
    {
        std::lock_guard<std::mutex> lock(g_observed_assets_mutex);
        if (g_observed_asset_address_keys.insert(key).second)
        {
            ObservedAssetAddress entry;
            entry.kind = kind;
            entry.asset_name = to_lower_copy(asset_name);
            entry.source = source ? source : "";
            entry.addr = addr;
            entry.related_addr = related_addr;
            g_observed_asset_addresses.push_back(std::move(entry));
            inserted = true;
        }
    }

    if (inserted)
    {
        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(addr, &rva);
        log_line(
            "observed_asset_addr kind=%s asset=%s addr=0x%08lX module=%s%s%08lX source=%s related=0x%08lX",
            kind,
            asset_name,
            static_cast<unsigned long>(addr),
            module_name,
            std::strcmp(module_name, "<unknown>") ? " rva=0x" : "",
            rva,
            source ? source : "",
            static_cast<unsigned long>(related_addr));
    }
}

std::vector<uint32_t> capture_dword_window_values(uintptr_t base_addr, int before_slots, int after_slots)
{
    std::vector<uint32_t> values;
    if (!base_addr)
        return values;

    const int total_slots = (after_slots - before_slots) + 1;
    if (total_slots <= 0)
        return values;

    values.resize(static_cast<size_t>(total_slots), 0);
    for (int slot = -before_slots; slot <= after_slots; ++slot)
    {
        const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(slot * static_cast<int>(sizeof(uint32_t)));
        uint32_t value = 0;
        safe_copy_memory(slot_addr, &value, sizeof(value));
        values[static_cast<size_t>(slot + before_slots)] = value;
    }
    return values;
}

void log_consumer_dword_window_correlations(const char* context, uintptr_t base_addr, int before_slots, const std::vector<uint32_t>& values)
{
    if (!context || !base_addr || values.empty())
        return;

    std::vector<ObservedAssetAddress> observed;
    {
        std::lock_guard<std::mutex> lock(g_observed_assets_mutex);
        observed = g_observed_asset_addresses;
    }
    if (observed.empty())
        return;

    int logged = 0;
    for (size_t index = 0; index < values.size(); ++index)
    {
        const uint32_t value = values[index];
        if (!value)
            continue;

        const int slot = static_cast<int>(index) - before_slots;
        for (const auto& observed_entry : observed)
        {
            const intptr_t delta = static_cast<intptr_t>(static_cast<uintptr_t>(value)) - static_cast<intptr_t>(observed_entry.addr);
            const bool exact = value == static_cast<uint32_t>(observed_entry.addr);
            const bool is_near = !exact && std::llabs(static_cast<long long>(delta)) <= 0x80;
            const bool same_page = !exact && !is_near && ((static_cast<uintptr_t>(value) & ~static_cast<uintptr_t>(0xFFF)) == (observed_entry.addr & ~static_cast<uintptr_t>(0xFFF)));
            if (!exact && !is_near && !same_page)
                continue;

            const char* relation = exact ? "exact" : (is_near ? "near" : "same_page");
            log_line(
                "consumer_value_match context=%s base=0x%08lX slot=%+d value=0x%08lX relation=%s delta=%ld observedKind=%s asset=%s observedAddr=0x%08lX source=%s related=0x%08lX",
                context,
                static_cast<unsigned long>(base_addr),
                slot,
                static_cast<unsigned long>(value),
                relation,
                static_cast<long>(delta),
                observed_entry.kind.c_str(),
                observed_entry.asset_name.c_str(),
                static_cast<unsigned long>(observed_entry.addr),
                observed_entry.source.c_str(),
                static_cast<unsigned long>(observed_entry.related_addr));
            if (++logged >= 24)
                return;
        }

        uint32_t deref = 0;
        if (!pointer_readable(value, sizeof(uint32_t)) || !safe_copy_memory(value, &deref, sizeof(deref)) || !deref)
            continue;

        for (const auto& observed_entry : observed)
        {
            const intptr_t delta = static_cast<intptr_t>(static_cast<uintptr_t>(deref)) - static_cast<intptr_t>(observed_entry.addr);
            const bool exact = deref == static_cast<uint32_t>(observed_entry.addr);
            const bool is_near = !exact && std::llabs(static_cast<long long>(delta)) <= 0x80;
            if (!exact && !is_near)
                continue;

            log_line(
                "consumer_value_deref_match context=%s base=0x%08lX slot=%+d value=0x%08lX deref=0x%08lX relation=%s delta=%ld observedKind=%s asset=%s observedAddr=0x%08lX source=%s related=0x%08lX",
                context,
                static_cast<unsigned long>(base_addr),
                slot,
                static_cast<unsigned long>(value),
                static_cast<unsigned long>(deref),
                exact ? "exact" : "near",
                static_cast<long>(delta),
                observed_entry.kind.c_str(),
                observed_entry.asset_name.c_str(),
                static_cast<unsigned long>(observed_entry.addr),
                observed_entry.source.c_str(),
                static_cast<unsigned long>(observed_entry.related_addr));
            if (++logged >= 24)
                return;
        }
    }
}

void track_consumer_object_window(const char* context, uintptr_t base_addr, int before_slots, int after_slots)
{
    if (!context || !base_addr)
        return;

    std::vector<uint32_t> values = capture_dword_window_values(base_addr, before_slots, after_slots);
    if (values.empty())
        return;

    char key_buffer[128] {};
    std::snprintf(key_buffer, sizeof(key_buffer), "%s|0x%08lX", context, static_cast<unsigned long>(base_addr));
    const std::string key = key_buffer;
    const DWORD now = GetTickCount();

    bool first_seen = false;
    std::vector<std::string> changes;
    DWORD first_tick = now;
    DWORD last_tick = now;
    unsigned hit_count = 0;

    {
        std::lock_guard<std::mutex> lock(g_consumer_objects_mutex);
        auto it = g_consumer_object_states.find(key);
        if (it == g_consumer_object_states.end())
        {
            ConsumerObjectState state;
            state.context = context;
            state.base_addr = base_addr;
            state.before_slots = before_slots;
            state.after_slots = after_slots;
            state.first_tick = now;
            state.last_tick = now;
            state.hit_count = 1;
            state.first_values = values;
            state.last_values = values;
            g_consumer_object_states.emplace(key, std::move(state));
            first_seen = true;
            hit_count = 1;
        }
        else
        {
            ConsumerObjectState& state = it->second;
            first_tick = state.first_tick;
            last_tick = state.last_tick;
            hit_count = state.hit_count + 1;
            const size_t compare_count = std::min(state.last_values.size(), values.size());
            for (size_t i = 0; i < compare_count; ++i)
            {
                if (state.last_values[i] == values[i])
                    continue;
                char change[96] {};
                std::snprintf(
                    change,
                    sizeof(change),
                    "%+d:0x%08lX->0x%08lX",
                    static_cast<int>(i) - before_slots,
                    static_cast<unsigned long>(state.last_values[i]),
                    static_cast<unsigned long>(values[i]));
                changes.emplace_back(change);
            }
            state.last_tick = now;
            state.hit_count += 1;
            state.last_values = values;
        }
    }

    if (first_seen)
    {
        log_line(
            "consumer_object_new context=%s base=0x%08lX slots=%d firstTick=%lu hitCount=%u",
            context,
            static_cast<unsigned long>(base_addr),
            static_cast<int>(values.size()),
            static_cast<unsigned long>(now),
            hit_count);
        return;
    }

    if (!changes.empty())
    {
        log_line(
            "consumer_object_delta context=%s base=0x%08lX hitCount=%u sinceFirstMs=%lu sincePrevMs=%lu changedSlots=%s",
            context,
            static_cast<unsigned long>(base_addr),
            hit_count,
            static_cast<unsigned long>(now - first_tick),
            static_cast<unsigned long>(now - last_tick),
            join_compact_strings(changes).c_str());
    }
}

bool query_page_protect(uintptr_t addr, DWORD* protect_out)
{
    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(addr), &mbi, sizeof(mbi)))
        return false;
    if (protect_out)
        *protect_out = mbi.Protect & ~PAGE_GUARD;
    return true;
}

uint32_t fnv1a_hash_bytes(const unsigned char* data, size_t size)
{
    uint32_t hash = 2166136261u;
    if (!data || size == 0)
        return hash;
    for (size_t i = 0; i < size; ++i)
    {
        hash ^= static_cast<uint32_t>(data[i]);
        hash *= 16777619u;
    }
    return hash;
}

uint32_t hash_memory_fnv1a(uintptr_t addr, size_t size)
{
    if (!addr || size == 0)
        return 2166136261u;
    std::vector<unsigned char> buffer(size);
    if (!safe_copy_memory(addr, buffer.data(), size))
        return 0;
    return fnv1a_hash_bytes(buffer.data(), buffer.size());
}

std::vector<unsigned char> load_binary_file(const std::string& path)
{
    std::vector<unsigned char> data;
    FILE* file = std::fopen(path.c_str(), "rb");
    if (!file)
        return data;
    std::fseek(file, 0, SEEK_END);
    const long size = std::ftell(file);
    std::fseek(file, 0, SEEK_SET);
    if (size > 0)
    {
        data.resize(static_cast<size_t>(size));
        if (std::fread(data.data(), 1, data.size(), file) != data.size())
            data.clear();
    }
    std::fclose(file);
    return data;
}

bool write_memory_bytes(uintptr_t addr, const void* src, size_t size)
{
    if (!addr || !src || size == 0)
        return false;
    DWORD old = 0;
    if (!VirtualProtect(reinterpret_cast<void*>(addr), size, PAGE_READWRITE, &old))
        return false;
    std::memcpy(reinterpret_cast<void*>(addr), src, size);
    DWORD restored = 0;
    VirtualProtect(reinterpret_cast<void*>(addr), size, old, &restored);
    FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(addr), size);
    return true;
}

bool apply_bootstrap_hash_null_guard()
{
    if (!g_main_base)
        return false;

    const uintptr_t target = g_main_base + kBootstrapHashNullGuardRva;
    const uintptr_t resume = g_main_base + kBootstrapHashNullGuardResumeRva;
    const unsigned char expected[] = {
        0x56, 0x8B, 0xF0, 0x80, 0x3E, 0x00, 0x57, 0x8B, 0xF9
    };

    unsigned char current[sizeof(expected)] {};
    if (!safe_copy_memory(target, current, sizeof(current)))
    {
        log_line("bootstrap_hash_null_guard_copy_failed addr=0x%08lX", static_cast<unsigned long>(target));
        return false;
    }

    if (std::memcmp(current, expected, sizeof(expected)) != 0)
    {
        log_line("bootstrap_hash_null_guard_signature_mismatch addr=0x%08lX", static_cast<unsigned long>(target));
        log_bytes_around("bootstrap_hash_null_guard_mismatch", target, 8, 24);
        return false;
    }

    unsigned char* stub = reinterpret_cast<unsigned char*>(
        VirtualAlloc(nullptr, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    if (!stub)
    {
        log_line("bootstrap_hash_null_guard_alloc_failed gle=%lu", GetLastError());
        return false;
    }

    size_t cursor = 0;
    auto emit8 = [&](unsigned char value)
    {
        stub[cursor++] = value;
    };
    auto emit32 = [&](uintptr_t target_addr, uintptr_t next_ip)
    {
        const int32_t rel = static_cast<int32_t>(target_addr - next_ip);
        std::memcpy(stub + cursor, &rel, sizeof(rel));
        cursor += sizeof(rel);
    };

    emit8(0x85); emit8(0xC0);             // test eax, eax
    emit8(0x75); emit8(0x03);             // jne +3
    emit8(0x8B); emit8(0xC1);             // mov eax, ecx
    emit8(0xC3);                          // ret
    emit8(0x56);                          // push esi
    emit8(0x8B); emit8(0xF0);             // mov esi, eax
    emit8(0x80); emit8(0x3E); emit8(0x00);// cmp byte ptr [esi], 0
    emit8(0x57);                          // push edi
    emit8(0x8B); emit8(0xF9);             // mov edi, ecx
    emit8(0xE9);                          // jmp resume
    emit32(resume, reinterpret_cast<uintptr_t>(stub) + cursor + 4);

    unsigned char patch[sizeof(expected)] {};
    patch[0] = 0xE9;
    const int32_t rel = static_cast<int32_t>(reinterpret_cast<uintptr_t>(stub) - (target + 5));
    std::memcpy(patch + 1, &rel, sizeof(rel));
    for (size_t i = 5; i < sizeof(patch); ++i)
        patch[i] = 0x90;

    if (!write_memory_bytes(target, patch, sizeof(patch)))
    {
        log_line("bootstrap_hash_null_guard_patch_failed addr=0x%08lX stub=0x%08lX",
            static_cast<unsigned long>(target),
            static_cast<unsigned long>(reinterpret_cast<uintptr_t>(stub)));
        return false;
    }

    log_line("bootstrap_hash_null_guard_applied target=0x%08lX resume=0x%08lX stub=0x%08lX",
        static_cast<unsigned long>(target),
        static_cast<unsigned long>(resume),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(stub)));
    return true;
}

DWORD WINAPI bootstrap_hash_null_guard_retry_thread(LPVOID)
{
    constexpr int kMaxAttempts = 120;
    constexpr DWORD kSleepMs = 250;
    for (int attempt = 1; attempt <= kMaxAttempts; ++attempt)
    {
        Sleep(kSleepMs);
        if (apply_bootstrap_hash_null_guard())
        {
            log_line("bootstrap_hash_null_guard_retry_success attempt=%d", attempt);
            return 0;
        }
        log_line("bootstrap_hash_null_guard_retry_pending attempt=%d", attempt);
    }

    log_line("bootstrap_hash_null_guard_retry_exhausted attempts=%d", kMaxAttempts);
    return 0;
}

void load_xanim_runtime_patches()
{
    g_xanim_runtime_patches.clear();

    const std::string manifest_path = module_relative_path(L"xanim_runtime_patches.txt");
    FILE* file = std::fopen(manifest_path.c_str(), "rb");
    if (!file)
    {
        log_line("xanim_runtime_patches_missing path=%s", manifest_path.c_str());
        return;
    }

    char line[1024] {};
    unsigned count = 0;
    while (std::fgets(line, sizeof(line), file))
    {
        std::string text = line;
        while (!text.empty() && (text.back() == '\r' || text.back() == '\n'))
            text.pop_back();
        if (text.empty())
            continue;
        if (text.rfind("patch|", 0) != 0)
            continue;

        std::vector<std::string> parts;
        size_t start = 0;
        while (start <= text.size())
        {
            const size_t sep = text.find('|', start);
            if (sep == std::string::npos)
            {
                parts.push_back(text.substr(start));
                break;
            }
            parts.push_back(text.substr(start, sep - start));
            start = sep + 1;
        }
        if (parts.size() < 4)
            continue;

        const std::string asset_name = to_lower_copy(parts[1]);
        const std::string section_name = parts[2];
        const std::string relative_path = parts[3];
        if (asset_name.empty() || section_name.empty() || relative_path.empty())
            continue;

        std::wstring rel_w = wide_from_utf8(relative_path);
        const std::string patch_path = module_relative_path(rel_w.c_str());
        std::vector<unsigned char> data = load_binary_file(patch_path);
        if (data.empty())
        {
            log_line("xanim_runtime_patch_file_missing asset=%s section=%s path=%s",
                asset_name.c_str(),
                section_name.c_str(),
                patch_path.c_str());
            continue;
        }

        XanimRuntimeSectionPatch patch;
        patch.asset_name = asset_name;
        patch.section_name = section_name;
        patch.data = std::move(data);
        g_xanim_runtime_patches.push_back(std::move(patch));
        ++count;
    }
    std::fclose(file);
    log_line("xanim_runtime_patches_loaded path=%s sections=%u", manifest_path.c_str(), count);
}

void apply_runtime_section_patches_for_asset(
    const char* target_name,
    uintptr_t header_addr,
    uintptr_t data_byte_ptr,
    size_t data_byte_size,
    uintptr_t data_short_ptr,
    size_t data_short_size,
    uintptr_t data_int_ptr,
    size_t data_int_size,
    uintptr_t notify_ptr,
    size_t notify_size,
    uintptr_t delta_part_ptr)
{
    if (!target_name || !*target_name || g_xanim_runtime_patches.empty())
        return;
    if (g_xanim_runtime_patched_headers.find(header_addr) != g_xanim_runtime_patched_headers.end())
        return;

    const std::string wanted = to_lower_copy(target_name);
    bool patched_any = false;

    for (const auto& patch : g_xanim_runtime_patches)
    {
        if (patch.asset_name != wanted)
            continue;

        uintptr_t section_addr = 0;
        size_t section_size = 0;
        if (patch.section_name == "dataByte")
        {
            section_addr = data_byte_ptr;
            section_size = data_byte_size;
        }
        else if (patch.section_name == "dataShort")
        {
            section_addr = data_short_ptr;
            section_size = data_short_size;
        }
        else if (patch.section_name == "dataInt")
        {
            section_addr = data_int_ptr;
            section_size = data_int_size;
        }
        else if (patch.section_name == "notify")
        {
            section_addr = notify_ptr;
            section_size = notify_size;
        }
        else if (patch.section_name == "deltaPart")
        {
            section_addr = delta_part_ptr;
            section_size = patch.data.size();
        }
        else
        {
            log_line("xanim_runtime_patch_skip asset=%s header=0x%08lX section=%s reason=unsupported_section",
                target_name,
                static_cast<unsigned long>(header_addr),
                patch.section_name.c_str());
            continue;
        }

        if (!section_addr || section_size == 0)
        {
            log_line("xanim_runtime_patch_skip asset=%s header=0x%08lX section=%s reason=missing_live_section",
                target_name,
                static_cast<unsigned long>(header_addr),
                patch.section_name.c_str());
            continue;
        }
        if (patch.data.size() != section_size)
        {
            log_line("xanim_runtime_patch_skip asset=%s header=0x%08lX section=%s reason=size_mismatch live=%lu patch=%lu",
                target_name,
                static_cast<unsigned long>(header_addr),
                patch.section_name.c_str(),
                static_cast<unsigned long>(section_size),
                static_cast<unsigned long>(patch.data.size()));
            continue;
        }

        const uint32_t before_hash = hash_memory_fnv1a(section_addr, section_size);
        const bool wrote = write_memory_bytes(section_addr, patch.data.data(), patch.data.size());
        const uint32_t after_hash = hash_memory_fnv1a(section_addr, section_size);
        log_line("xanim_runtime_patch asset=%s header=0x%08lX section=%s addr=0x%08lX wrote=%d before=0x%08lX after=0x%08lX expected=0x%08lX size=%lu",
            target_name,
            static_cast<unsigned long>(header_addr),
            patch.section_name.c_str(),
            static_cast<unsigned long>(section_addr),
            wrote ? 1 : 0,
            static_cast<unsigned long>(before_hash),
            static_cast<unsigned long>(after_hash),
            static_cast<unsigned long>(fnv1a_hash_bytes(patch.data.data(), patch.data.size())),
            static_cast<unsigned long>(section_size));
        patched_any = patched_any || wrote;
    }

    if (patched_any)
        g_xanim_runtime_patched_headers.insert(header_addr);
}

void arm_xanim_runtime_touch_targets(
    const char* target_name,
    uintptr_t header_addr,
    uintptr_t data_int_ptr,
    uint32_t data_int_hash,
    uint32_t names_hash,
    uintptr_t delta_part_ptr)
{
    if (g_probe_mode != ProbeMode::XanimFocus)
        return;

    DWORD data_int_protect = 0;
    if (data_int_ptr && query_page_protect(data_int_ptr, &data_int_protect))
    {
        char label[256] {};
        std::snprintf(
            label,
            sizeof(label),
            "%s|header=0x%08lX|dataIntHash=0x%08lX|namesHash=0x%08lX",
            target_name,
            static_cast<unsigned long>(header_addr),
            static_cast<unsigned long>(data_int_hash),
            static_cast<unsigned long>(names_hash));
        add_touch_target_locked("xanim_runtime_dataInt", label, data_int_ptr, data_int_protect);
    }

    DWORD delta_protect = 0;
    if (delta_part_ptr && query_page_protect(delta_part_ptr, &delta_protect))
    {
        char label[256] {};
        std::snprintf(
            label,
            sizeof(label),
            "%s|header=0x%08lX|delta=0x%08lX|dataIntHash=0x%08lX",
            target_name,
            static_cast<unsigned long>(header_addr),
            static_cast<unsigned long>(delta_part_ptr),
            static_cast<unsigned long>(data_int_hash));
        add_touch_target_locked("xanim_runtime_delta", label, delta_part_ptr, delta_protect);
    }
}

bool process_xanim_header_candidate(const char* target_name, uintptr_t header_addr, const unsigned char* header, const char* source_tag)
{
    if (!target_name || !*target_name || !header_addr || !header)
        return false;

    const DWORD name_ptr = *reinterpret_cast<const DWORD*>(header + 0x00);
    const WORD data_byte_count = *reinterpret_cast<const WORD*>(header + 0x04);
    const WORD data_short_count = *reinterpret_cast<const WORD*>(header + 0x06);
    const WORD data_int_count = *reinterpret_cast<const WORD*>(header + 0x08);
    const WORD numframes = *reinterpret_cast<const WORD*>(header + 0x0E);
    const BYTE b_loop = header[0x10];
    const BYTE b_delta = header[0x11];
    const BYTE b_delta3d = header[0x12];
    const BYTE total_bones = header[0x18 + 9];
    const BYTE notify_count = header[0x22];
    const BYTE asset_type = header[0x23];
    const BYTE is_default = header[0x24];
    const DWORD random_data_short_count = *reinterpret_cast<const DWORD*>(header + 0x28);
    const float framerate = *reinterpret_cast<const float*>(header + 0x30);
    const float frequency = *reinterpret_cast<const float*>(header + 0x34);
    const DWORD names_ptr = *reinterpret_cast<const DWORD*>(header + 0x40);
    const DWORD data_byte_ptr = *reinterpret_cast<const DWORD*>(header + 0x44);
    const DWORD data_short_ptr = *reinterpret_cast<const DWORD*>(header + 0x48);
    const DWORD data_int_ptr = *reinterpret_cast<const DWORD*>(header + 0x4C);
    const DWORD random_data_short_ptr = *reinterpret_cast<const DWORD*>(header + 0x50);
    const DWORD notify_ptr = *reinterpret_cast<const DWORD*>(header + 0x60);
    const DWORD delta_part_ptr = *reinterpret_cast<const DWORD*>(header + 0x64);
    const BYTE names_ptr_present = names_ptr ? 1 : 0;
    const BYTE data_byte_ptr_present = data_byte_ptr ? 1 : 0;
    const BYTE data_short_ptr_present = data_short_ptr ? 1 : 0;
    const BYTE data_int_ptr_present = data_int_ptr ? 1 : 0;
    const BYTE notify_ptr_present = notify_ptr ? 1 : 0;
    const BYTE delta_part_ptr_present = delta_part_ptr ? 1 : 0;
    const std::string asset_key = to_lower_copy(target_name);

    record_observed_asset_address("xanim_header", target_name, header_addr, source_tag ? source_tag : "unknown");
    if (name_ptr)
        record_observed_asset_address("xanim_nameptr", target_name, name_ptr, source_tag ? source_tag : "unknown", header_addr);
    if (names_ptr)
        record_observed_asset_address("xanim_names", target_name, names_ptr, source_tag ? source_tag : "unknown", header_addr);
    if (data_int_ptr)
        record_observed_asset_address("xanim_dataInt", target_name, data_int_ptr, source_tag ? source_tag : "unknown", header_addr);
    if (delta_part_ptr)
        record_observed_asset_address("xanim_delta", target_name, delta_part_ptr, source_tag ? source_tag : "unknown", header_addr);

    if (!name_ptr || total_bones == 0 || total_bones > 128)
        return false;
    if (numframes == 0 || numframes > 4096)
        return false;
    if (asset_type > 8)
        return false;
    if (notify_count > 128)
        return false;
    if (data_byte_count > 16384 || data_short_count > 65535 || data_int_count > 65535 || random_data_short_count > 16384)
        return false;
    if (!(framerate >= 0.0f && framerate <= 1000.0f) || !(frequency >= 0.0f && frequency <= 1000.0f))
        return false;
    if (names_ptr && !pointer_readable(names_ptr))
        return false;
    if (data_byte_ptr && !pointer_readable(data_byte_ptr, data_byte_count ? data_byte_count : 1))
        return false;
    if (data_short_ptr && !pointer_readable(data_short_ptr, data_short_count ? data_short_count * sizeof(short) : sizeof(short)))
        return false;
    if (data_int_ptr && !pointer_readable(data_int_ptr, data_int_count ? data_int_count * sizeof(float) : sizeof(float)))
        return false;
    if (random_data_short_ptr && !pointer_readable(random_data_short_ptr))
        return false;
    if (notify_ptr && !pointer_readable(notify_ptr, notify_count ? notify_count * 8u : 1u))
        return false;
    if (delta_part_ptr && !pointer_readable(delta_part_ptr))
        return false;

    const uint32_t names_hash = hash_memory_fnv1a(names_ptr, static_cast<size_t>(total_bones) * sizeof(uint16_t));
    const uint32_t notify_hash = hash_memory_fnv1a(notify_ptr, static_cast<size_t>(notify_count) * 8u);
    const uint32_t data_byte_hash = hash_memory_fnv1a(data_byte_ptr, static_cast<size_t>(data_byte_count));
    const uint32_t data_short_hash = hash_memory_fnv1a(data_short_ptr, static_cast<size_t>(data_short_count) * sizeof(uint16_t));
    const uint32_t data_int_hash = hash_memory_fnv1a(data_int_ptr, static_cast<size_t>(data_int_count) * sizeof(float));
    const std::string header_variant_exact = xanim_header_variant_exact(
        asset_key,
        numframes,
        data_byte_count,
        data_short_count,
        data_int_count,
        notify_count,
        total_bones,
        frequency,
        asset_type,
        is_default,
        b_loop,
        b_delta,
        b_delta3d,
        names_ptr_present,
        data_byte_ptr_present,
        data_short_ptr_present,
        data_int_ptr_present,
        notify_ptr_present,
        delta_part_ptr_present);
    const std::string header_variant_best = xanim_best_header_variant_summary(
        asset_key,
        numframes,
        data_byte_count,
        data_short_count,
        data_int_count,
        notify_count,
        total_bones,
        frequency,
        asset_type,
        is_default,
        b_loop,
        b_delta,
        b_delta3d,
        names_ptr_present,
        data_byte_ptr_present,
        data_short_ptr_present,
        data_int_ptr_present,
        notify_ptr_present,
        delta_part_ptr_present);
    const std::vector<std::string> data_short_variants = expected_section_variants_for_hash(asset_key, "dataShort", data_short_hash);
    const std::vector<std::string> data_int_variants = expected_section_variants_for_hash(asset_key, "dataInt", data_int_hash);
    const std::vector<std::string> delta_variants = expected_section_variants_for_memory(asset_key, "deltaPart", delta_part_ptr);
    const std::string data_short_variant = classify_xanim_variant_values(data_short_variants);
    const std::string data_int_variant = classify_xanim_variant_values(data_int_variants);
    const std::string delta_variant = delta_part_ptr ? classify_xanim_variant_values(delta_variants) : "absent";
    std::vector<std::string> section_family;
    if (data_short_variant != "unknown")
        section_family.push_back(data_short_variant);
    if (data_int_variant != "unknown")
        section_family.push_back(data_int_variant);
    if (delta_variant != "unknown" && delta_variant != "absent")
        section_family.push_back(delta_variant);
    const std::string section_variant = classify_xanim_variant_values(section_family);

    float floats[12] {};
    const size_t float_count = std::min<size_t>(12, data_int_count);
    if (float_count > 0 && !safe_copy_memory(data_int_ptr, floats, float_count * sizeof(float)))
        return false;

    bool zero_prefix = true;
    for (size_t fi = 0; fi < float_count; ++fi)
    {
        if (std::fabs(floats[fi]) > 0.0005f)
        {
            zero_prefix = false;
            break;
        }
    }

    unsigned long header_rva = 0;
    const char* header_module = module_name_for_addr(header_addr, &header_rva);
    log_line(
        "xanim_candidate source=%s name=%s header=0x%08lX module=%s rva=0x%08lX totalBones=%u numframes=%u assetType=%u isDefault=%u bLoop=%u bDelta=%u bDelta3D=%u frequency=%.6f dataByteCount=%u dataShortCount=%u dataIntCount=%u notifyCount=%u randomDataShortCount=%lu namesHash=0x%08lX notifyHash=0x%08lX dataByteHash=0x%08lX dataShortHash=0x%08lX dataIntHash=0x%08lX deltaPart=0x%08lX zeroPrefix=%d firstFloats=%.6f,%.6f,%.6f,%.6f,%.6f,%.6f",
        source_tag ? source_tag : "unknown",
        target_name,
        static_cast<unsigned long>(header_addr),
        header_module,
        header_rva,
        static_cast<unsigned>(total_bones),
        static_cast<unsigned>(numframes),
        static_cast<unsigned>(asset_type),
        static_cast<unsigned>(is_default),
        static_cast<unsigned>(b_loop),
        static_cast<unsigned>(b_delta),
        static_cast<unsigned>(b_delta3d),
        frequency,
        static_cast<unsigned>(data_byte_count),
        static_cast<unsigned>(data_short_count),
        static_cast<unsigned>(data_int_count),
        static_cast<unsigned>(notify_count),
        static_cast<unsigned long>(random_data_short_count),
        static_cast<unsigned long>(names_hash),
        static_cast<unsigned long>(notify_hash),
        static_cast<unsigned long>(data_byte_hash),
        static_cast<unsigned long>(data_short_hash),
        static_cast<unsigned long>(data_int_hash),
        static_cast<unsigned long>(delta_part_ptr),
        zero_prefix ? 1 : 0,
        float_count > 0 ? floats[0] : 0.0f,
        float_count > 1 ? floats[1] : 0.0f,
        float_count > 2 ? floats[2] : 0.0f,
        float_count > 3 ? floats[3] : 0.0f,
        float_count > 4 ? floats[4] : 0.0f,
        float_count > 5 ? floats[5] : 0.0f);
    log_line(
        "xanim_live_asset_map source=%s asset=%s header=0x%08lX module=%s rva=0x%08lX namePtr=0x%08lX namesPtr=0x%08lX dataBytePtr=0x%08lX dataShortPtr=0x%08lX dataIntPtr=0x%08lX notifyPtr=0x%08lX deltaPartPtr=0x%08lX totalBones=%u numframes=%u assetType=%u isDefault=%u bLoop=%u bDelta=%u bDelta3D=%u frequency=%.6f dataByteCount=%u dataShortCount=%u dataIntCount=%u notifyCount=%u namesHash=0x%08lX notifyHash=0x%08lX dataByteHash=0x%08lX dataShortHash=0x%08lX dataIntHash=0x%08lX headerVariant=%s bestHeaderVariant=%s dataShortVariant=%s dataIntVariant=%s deltaPartVariant=%s sectionVariant=%s",
        source_tag ? source_tag : "unknown",
        target_name,
        static_cast<unsigned long>(header_addr),
        header_module,
        header_rva,
        static_cast<unsigned long>(name_ptr),
        static_cast<unsigned long>(names_ptr),
        static_cast<unsigned long>(data_byte_ptr),
        static_cast<unsigned long>(data_short_ptr),
        static_cast<unsigned long>(data_int_ptr),
        static_cast<unsigned long>(notify_ptr),
        static_cast<unsigned long>(delta_part_ptr),
        static_cast<unsigned>(total_bones),
        static_cast<unsigned>(numframes),
        static_cast<unsigned>(asset_type),
        static_cast<unsigned>(is_default),
        static_cast<unsigned>(b_loop),
        static_cast<unsigned>(b_delta),
        static_cast<unsigned>(b_delta3d),
        frequency,
        static_cast<unsigned>(data_byte_count),
        static_cast<unsigned>(data_short_count),
        static_cast<unsigned>(data_int_count),
        static_cast<unsigned>(notify_count),
        static_cast<unsigned long>(names_hash),
        static_cast<unsigned long>(notify_hash),
        static_cast<unsigned long>(data_byte_hash),
        static_cast<unsigned long>(data_short_hash),
        static_cast<unsigned long>(data_int_hash),
        header_variant_exact.c_str(),
        header_variant_best.c_str(),
        data_short_variant.c_str(),
        data_int_variant.c_str(),
        delta_variant.c_str(),
        section_variant.c_str());

    apply_runtime_section_patches_for_asset(
        target_name,
        header_addr,
        data_byte_ptr,
        static_cast<size_t>(data_byte_count),
        data_short_ptr,
        static_cast<size_t>(data_short_count) * sizeof(uint16_t),
        data_int_ptr,
        static_cast<size_t>(data_int_count) * sizeof(float),
        notify_ptr,
        static_cast<size_t>(notify_count) * 8u,
        delta_part_ptr);

    arm_xanim_runtime_touch_targets(
        target_name,
        header_addr,
        data_int_ptr,
        data_int_hash,
        names_hash,
        delta_part_ptr);

    return true;
}

int scan_live_xanim_asset_headers_near_name_addrs(const char* target_name, const std::vector<uintptr_t>& name_addrs)
{
    if (!target_name || !*target_name || name_addrs.empty())
        return 0;

    constexpr uintptr_t kNearWindow = 0x400000;
    std::unordered_set<uintptr_t> seen_headers;
    int candidates = 0;
    int raw_refs = 0;
    int ref_logs = 0;

    for (const uintptr_t name_addr : name_addrs)
    {
        if (!name_addr)
            continue;

        const uintptr_t scan_start = (name_addr > kNearWindow) ? (name_addr - kNearWindow) : 0;
        const uintptr_t scan_end = name_addr + kNearWindow;
        uintptr_t cursor = scan_start;
        while (cursor < scan_end)
        {
            MEMORY_BASIC_INFORMATION mbi {};
            if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
                break;

            const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
            const uintptr_t next = region_base + mbi.RegionSize;
            if (region_is_readable(mbi) && mbi.RegionSize >= sizeof(DWORD) + 104)
            {
                constexpr size_t kScanChunk = 0x10000;
                std::vector<unsigned char> chunk;
                chunk.reserve(kScanChunk + sizeof(DWORD));
                size_t region_offset = 0;
                while (region_offset < mbi.RegionSize)
                {
                    const size_t to_copy = std::min<size_t>(kScanChunk + sizeof(DWORD), mbi.RegionSize - region_offset);
                    chunk.assign(to_copy, 0);
                    if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                    {
                        region_offset += kScanChunk;
                        continue;
                    }

                    for (size_t i = 0; i + sizeof(DWORD) <= to_copy; ++i)
                    {
                        DWORD value = 0;
                        std::memcpy(&value, chunk.data() + i, sizeof(value));
                        if (value != static_cast<DWORD>(name_addr))
                            continue;

                        const uintptr_t header_addr = region_base + region_offset + i;
                        ++raw_refs;
                        if (ref_logs < kNamedAssetRefLogMax)
                        {
                            log_xanim_name_reference_detail(target_name, name_addr, header_addr);
                            ++ref_logs;
                        }
                        record_observed_asset_address("xanim_ref", target_name, header_addr, "near_name_ref", name_addr);
                        if (!seen_headers.insert(header_addr).second)
                            continue;

                        unsigned char header[104] {};
                        if (!safe_copy_memory(header_addr, header, sizeof(header)))
                            continue;
                        if (*reinterpret_cast<const DWORD*>(header + 0x00) != value)
                            continue;
                        if (process_xanim_header_candidate(target_name, header_addr, header, "near_name_scan"))
                            ++candidates;
                    }

                    if (to_copy <= sizeof(DWORD))
                        break;
                    region_offset += (kScanChunk > sizeof(DWORD)) ? (kScanChunk - sizeof(DWORD)) : to_copy;
                }
            }

            if (next <= cursor)
                break;
            cursor = next;
        }
    }

    log_line("xanim_near_name_scan_complete name=%s stringCopies=%u rawRefs=%d candidates=%d",
        target_name,
        static_cast<unsigned>(name_addrs.size()),
        raw_refs,
        candidates);
    return candidates;
}

int apply_runtime_patches_near_name_addrs(const char* target_name, const std::vector<uintptr_t>& name_addrs)
{
    if (!target_name || !*target_name || name_addrs.empty() || g_xanim_runtime_patches.empty() || g_xanim_expectations.empty())
        return 0;

    constexpr uintptr_t kPatchNearWindow = 0x800000;
    int patch_matches = 0;
    const std::string wanted = to_lower_copy(target_name);

    for (const auto& patch : g_xanim_runtime_patches)
    {
        if (patch.asset_name != wanted)
            continue;

        const std::string stock_section_name = "stock_" + patch.section_name;
        for (const auto& expectation : g_xanim_expectations)
        {
            if (expectation.asset_name != wanted)
                continue;
            if (expectation.section_name != patch.section_name && expectation.section_name != stock_section_name)
                continue;
            if (patch.data.size() != expectation.size)
                continue;

            const uint32_t patch_hash = fnv1a_hash_bytes(patch.data.data(), patch.data.size());
            bool matched_this_expectation = false;

            for (const uintptr_t name_addr : name_addrs)
            {
                if (!name_addr)
                    continue;

                const uintptr_t scan_start = (name_addr > kPatchNearWindow) ? (name_addr - kPatchNearWindow) : 0;
                const uintptr_t scan_end = name_addr + kPatchNearWindow;
                uintptr_t cursor = scan_start;
                while (cursor < scan_end)
                {
                    MEMORY_BASIC_INFORMATION mbi {};
                    if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
                        break;

                    const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
                    const uintptr_t next = region_base + mbi.RegionSize;
                    if (!region_is_readable(mbi) || mbi.RegionSize < expectation.prefix.size())
                    {
                        if (next <= cursor)
                            break;
                        cursor = next;
                        continue;
                    }

                    constexpr size_t kScanChunk = 0x10000;
                    std::vector<unsigned char> chunk;
                    chunk.reserve(kScanChunk + expectation.prefix.size());
                    size_t region_offset = 0;
                    while (region_offset < mbi.RegionSize)
                    {
                        const size_t to_copy = std::min<size_t>(kScanChunk + expectation.prefix.size(), mbi.RegionSize - region_offset);
                        chunk.assign(to_copy, 0);
                        if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                        {
                            region_offset += kScanChunk;
                            continue;
                        }

                        auto it = std::search(chunk.begin(), chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                        while (it != chunk.end())
                        {
                            const uintptr_t found_addr = region_base + region_offset + static_cast<size_t>(std::distance(chunk.begin(), it));
                            if (found_addr < expectation.prefix_offset)
                            {
                                it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                                continue;
                            }

                            const uintptr_t section_addr = found_addr - expectation.prefix_offset;
                            if (!pointer_readable(section_addr, expectation.size))
                            {
                                it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                                continue;
                            }

                            const uint32_t before_hash = hash_memory_fnv1a(section_addr, expectation.size);
                            if (before_hash != expectation.hash)
                            {
                                it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                                continue;
                            }

                            if (g_xanim_runtime_patched_sections.insert(section_addr).second)
                            {
                                const bool wrote = write_memory_bytes(section_addr, patch.data.data(), patch.data.size());
                                const uint32_t after_hash = hash_memory_fnv1a(section_addr, expectation.size);
                                unsigned long rva = 0;
                                const char* module_name = module_name_for_addr(section_addr, &rva);
                                log_line("xanim_near_name_patch asset=%s section=%s addr=0x%08lX module=%s rva=0x%08lX wrote=%d before=0x%08lX after=0x%08lX patch=0x%08lX size=%lu",
                                    patch.asset_name.c_str(),
                                    expectation.section_name.c_str(),
                                    static_cast<unsigned long>(section_addr),
                                    module_name,
                                    rva,
                                    wrote ? 1 : 0,
                                    static_cast<unsigned long>(before_hash),
                                    static_cast<unsigned long>(after_hash),
                                    static_cast<unsigned long>(patch_hash),
                                    static_cast<unsigned long>(expectation.size));
                                ++patch_matches;
                            }
                            matched_this_expectation = true;
                            break;
                        }

                        if (matched_this_expectation)
                            break;
                        if (to_copy <= expectation.prefix.size())
                            break;
                        region_offset += (kScanChunk > expectation.prefix.size()) ? (kScanChunk - expectation.prefix.size()) : to_copy;
                    }

                    if (matched_this_expectation)
                        break;
                    if (next <= cursor)
                        break;
                    cursor = next;
                }

                if (matched_this_expectation)
                    break;
            }
        }
    }

    if (patch_matches > 0)
        log_line("xanim_near_name_patch_complete name=%s patches=%d", target_name, patch_matches);
    return patch_matches;
}

void scan_expected_xanim_sections()
{
    if (g_xanim_expectations.empty())
    {
        log_line("xanim_expected_scan skipped reason=no_expectations");
        return;
    }

    const uintptr_t start_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMinimumApplicationAddress);
    const uintptr_t end_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMaximumApplicationAddress);
    int match_count = 0;

    for (const auto& expectation : g_xanim_expectations)
    {
        if (g_watch_xanims.find(expectation.asset_name) == g_watch_xanims.end())
            continue;
        std::vector<uintptr_t> matched_section_addrs;
        uintptr_t target_name_addr = 0;
        {
            std::lock_guard<std::mutex> lock(g_state_mutex);
            target_name_addr = find_touch_target_addr_locked(expectation.asset_name.c_str());
        }

        const uintptr_t bounded_scan_window = 0x00200000;
        const uintptr_t bounded_start = target_name_addr
            ? ((target_name_addr > bounded_scan_window) ? (target_name_addr - bounded_scan_window) : 0)
            : start_addr;
        const uintptr_t bounded_end = target_name_addr
            ? std::min<uintptr_t>(end_addr, target_name_addr + bounded_scan_window)
            : end_addr;

        uintptr_t cursor = bounded_start;
        while (cursor < bounded_end)
        {
            MEMORY_BASIC_INFORMATION mbi {};
            if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
                break;
            const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
            const uintptr_t next = region_base + mbi.RegionSize;
            if (target_name_addr)
            {
                if (next <= bounded_start)
                {
                    if (next <= cursor)
                        break;
                    cursor = next;
                    continue;
                }
                if (region_base >= bounded_end)
                    break;
            }
            if (!region_is_readable(mbi) || (mbi.Type != MEM_PRIVATE && mbi.Type != MEM_MAPPED) || mbi.RegionSize < expectation.prefix.size())
            {
                if (next <= cursor)
                    break;
                cursor = next;
                continue;
            }

            constexpr size_t kScanChunk = 0x10000;
            std::vector<unsigned char> chunk;
            chunk.reserve(kScanChunk + expectation.prefix.size());
            size_t region_offset = 0;
            while (region_offset < mbi.RegionSize)
            {
                const size_t to_copy = std::min<size_t>(kScanChunk + expectation.prefix.size(), mbi.RegionSize - region_offset);
                chunk.assign(to_copy, 0);
                if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                {
                    region_offset += kScanChunk;
                    continue;
                }

                auto it = std::search(chunk.begin(), chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                while (it != chunk.end())
                {
                    const uintptr_t found_addr = region_base + region_offset + static_cast<size_t>(std::distance(chunk.begin(), it));
                    if (found_addr < expectation.prefix_offset)
                    {
                        it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                        continue;
                    }
                    const uintptr_t section_addr = found_addr - expectation.prefix_offset;
                    if (pointer_readable(section_addr, expectation.size))
                    {
                        const uint32_t hash = hash_memory_fnv1a(section_addr, expectation.size);
                        if (hash == expectation.hash)
                        {
                            bool duplicate = false;
                            const uintptr_t dedupe_span = std::max<uintptr_t>(0x40, expectation.prefix.size());
                            for (uintptr_t seen_addr : matched_section_addrs)
                            {
                                const uintptr_t delta = (seen_addr > section_addr) ? (seen_addr - section_addr) : (section_addr - seen_addr);
                                if (delta < dedupe_span)
                                {
                                    duplicate = true;
                                    break;
                                }
                            }
                            if (duplicate)
                            {
                                it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                                continue;
                            }
                            matched_section_addrs.push_back(section_addr);
                            bool accepted_match = true;
                            uintptr_t accepted_asset_base = 0;
                            std::string cluster_summary;
                            unsigned long rva = 0;
                            const char* module_name = module_name_for_addr(section_addr, &rva);
                            if (expectation.relative_offset != SIZE_MAX && section_addr >= expectation.relative_offset)
                            {
                                const std::string variant_prefix = expectation_variant_prefix(expectation.section_name);
                                const uintptr_t asset_base = section_addr - expectation.relative_offset;
                                accepted_asset_base = asset_base;
                                int sibling_total = 0;
                                int sibling_matches = 0;
                                std::string summary = "xanim_expected_cluster asset=" + expectation.asset_name;
                                char base_buf[64] {};
                                std::snprintf(base_buf, sizeof(base_buf), " base=0x%08lX", static_cast<unsigned long>(asset_base));
                                summary += base_buf;
                                for (const auto& sibling : g_xanim_expectations)
                                {
                                    if (sibling.asset_name != expectation.asset_name || sibling.relative_offset == SIZE_MAX)
                                        continue;
                                    if (expectation_variant_prefix(sibling.section_name) != variant_prefix)
                                        continue;
                                    ++sibling_total;
                                    const uintptr_t sibling_addr = asset_base + sibling.relative_offset;
                                    const uint32_t sibling_hash = pointer_readable(sibling_addr, sibling.size)
                                        ? hash_memory_fnv1a(sibling_addr, sibling.size)
                                        : 0;
                                    const bool sibling_match = (sibling_hash == sibling.hash);
                                    if (sibling_match)
                                        ++sibling_matches;
                                    char sibling_buf[160] {};
                                    std::snprintf(
                                        sibling_buf,
                                        sizeof(sibling_buf),
                                        " %s=0x%08lX%s",
                                        sibling.section_name.c_str(),
                                        static_cast<unsigned long>(sibling_hash),
                                        sibling_match ? "[match]" : "");
                                    summary += sibling_buf;
                                }
                                char counts_buf[64] {};
                                std::snprintf(counts_buf, sizeof(counts_buf), " cluster=%d/%d", sibling_matches, sibling_total);
                                summary += counts_buf;
                                cluster_summary = summary;
                                if (asset_base < 0x00100000 || sibling_matches < 2)
                                    accepted_match = false;
                                else if (g_xanim_cluster_logged.insert(asset_base).second)
                                    log_line("%s", cluster_summary.c_str());
                            }
                            else
                            {
                                accepted_match = false;
                            }
                            if (!accepted_match)
                            {
                                it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                                continue;
                            }
                            log_line(
                                "xanim_expected_section_match asset=%s section=%s addr=0x%08lX module=%s rva=0x%08lX size=%lu hash=0x%08lX prefixOffset=%lu assetBase=0x%08lX",
                                expectation.asset_name.c_str(),
                                expectation.section_name.c_str(),
                                static_cast<unsigned long>(section_addr),
                                module_name,
                                rva,
                                static_cast<unsigned long>(expectation.size),
                                static_cast<unsigned long>(hash),
                                static_cast<unsigned long>(expectation.prefix_offset),
                                static_cast<unsigned long>(accepted_asset_base));
                            if (g_probe_mode == ProbeMode::XanimFocus)
                            {
                                DWORD protect = 0;
                                if (query_page_protect(section_addr, &protect))
                                {
                                    char label[256] {};
                                    std::snprintf(
                                        label,
                                        sizeof(label),
                                        "%s|section=%s|hash=0x%08lX",
                                        expectation.asset_name.c_str(),
                                        expectation.section_name.c_str(),
                                        static_cast<unsigned long>(hash));
                                    add_touch_target_locked("xanim_expected_section", label, section_addr, protect);
                                }
                            }
                            ++match_count;
                        }
                    }
                    it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                }

                if (to_copy <= expectation.prefix.size())
                    break;
                region_offset += (kScanChunk > expectation.prefix.size()) ? (kScanChunk - expectation.prefix.size()) : to_copy;
            }

            if (next <= cursor)
                break;
            cursor = next;
        }
    }

    log_line("xanim_expected_scan_complete matches=%d", match_count);
}

void apply_runtime_patches_via_expectations()
{
    if (g_xanim_runtime_patches.empty() || g_xanim_expectations.empty())
    {
        log_line("xanim_expectation_patch_scan skipped reason=no_patch_inputs");
        return;
    }

    const uintptr_t start_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMinimumApplicationAddress);
    const uintptr_t end_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMaximumApplicationAddress);
    int patch_matches = 0;

    for (const auto& patch : g_xanim_runtime_patches)
    {
        const std::string stock_section_name = "stock_" + patch.section_name;
        for (const auto& expectation : g_xanim_expectations)
        {
            if (expectation.asset_name != patch.asset_name)
                continue;
            if (expectation.section_name != patch.section_name && expectation.section_name != stock_section_name)
                continue;
            if (patch.data.size() != expectation.size)
            {
                log_line("xanim_expectation_patch_skip asset=%s section=%s reason=size_mismatch expect=%lu patch=%lu",
                    patch.asset_name.c_str(),
                    expectation.section_name.c_str(),
                    static_cast<unsigned long>(expectation.size),
                    static_cast<unsigned long>(patch.data.size()));
                continue;
            }

            const uint32_t patch_hash = fnv1a_hash_bytes(patch.data.data(), patch.data.size());
            uintptr_t cursor = start_addr;
            bool matched_this_expectation = false;
            while (cursor < end_addr)
            {
                MEMORY_BASIC_INFORMATION mbi {};
                if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
                    break;
                const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
                const uintptr_t next = region_base + mbi.RegionSize;
                if (!region_is_readable(mbi) || mbi.RegionSize < expectation.prefix.size())
                {
                    if (next <= cursor)
                        break;
                    cursor = next;
                    continue;
                }

                constexpr size_t kScanChunk = 0x10000;
                std::vector<unsigned char> chunk;
                chunk.reserve(kScanChunk + expectation.prefix.size());
                size_t region_offset = 0;
                while (region_offset < mbi.RegionSize)
                {
                    const size_t to_copy = std::min<size_t>(kScanChunk + expectation.prefix.size(), mbi.RegionSize - region_offset);
                    chunk.assign(to_copy, 0);
                    if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                    {
                        region_offset += kScanChunk;
                        continue;
                    }

                    auto it = std::search(chunk.begin(), chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                    while (it != chunk.end())
                    {
                        const uintptr_t found_addr = region_base + region_offset + static_cast<size_t>(std::distance(chunk.begin(), it));
                        if (found_addr < expectation.prefix_offset)
                        {
                            it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                            continue;
                        }

                        const uintptr_t section_addr = found_addr - expectation.prefix_offset;
                        if (!pointer_readable(section_addr, expectation.size))
                        {
                            it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                            continue;
                        }

                        const uint32_t before_hash = hash_memory_fnv1a(section_addr, expectation.size);
                        if (before_hash != expectation.hash)
                        {
                            it = std::search(it + 1, chunk.end(), expectation.prefix.begin(), expectation.prefix.end());
                            continue;
                        }

                        if (g_xanim_runtime_patched_sections.insert(section_addr).second)
                        {
                            const bool wrote = write_memory_bytes(section_addr, patch.data.data(), patch.data.size());
                            const uint32_t after_hash = hash_memory_fnv1a(section_addr, expectation.size);
                            unsigned long rva = 0;
                            const char* module_name = module_name_for_addr(section_addr, &rva);
                            log_line("xanim_expectation_patch asset=%s section=%s addr=0x%08lX module=%s rva=0x%08lX wrote=%d before=0x%08lX after=0x%08lX patch=0x%08lX size=%lu",
                                patch.asset_name.c_str(),
                                expectation.section_name.c_str(),
                                static_cast<unsigned long>(section_addr),
                                module_name,
                                rva,
                                wrote ? 1 : 0,
                                static_cast<unsigned long>(before_hash),
                                static_cast<unsigned long>(after_hash),
                                static_cast<unsigned long>(patch_hash),
                                static_cast<unsigned long>(expectation.size));
                            ++patch_matches;
                        }
                        matched_this_expectation = true;
                        break;
                    }

                    if (matched_this_expectation)
                        break;
                    if (to_copy <= expectation.prefix.size())
                        break;
                    region_offset += (kScanChunk > expectation.prefix.size()) ? (kScanChunk - expectation.prefix.size()) : to_copy;
                }

                if (matched_this_expectation)
                    break;
                if (next <= cursor)
                    break;
                cursor = next;
            }
        }
    }

    log_line("xanim_expectation_patch_scan_complete matches=%d", patch_matches);
}

void log_string_if_present(const char* name, uintptr_t addr)
{
    const std::string text = safe_read_ascii_string(addr);
    if (!text.empty())
        log_line("%s str=%s", name, text.c_str());
}

void log_stack_string_candidates(const CONTEXT& ctx, int slots = 8)
{
    if (!ctx.Esp)
        return;

    for (int i = 0; i < slots; ++i)
    {
        const uintptr_t slot_addr = ctx.Esp + static_cast<uintptr_t>(i * sizeof(DWORD));
        DWORD value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)))
            continue;
        const std::string text = safe_read_ascii_string(value);
        if (text.empty())
            continue;
        log_line("stack_str slot=%d stack=0x%08lX ptr=0x%08lX text=%s",
            i,
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(value),
            text.c_str());
    }
}

void log_stack_return_candidates(const char* prefix, const CONTEXT& ctx, int slots = 12)
{
    if (!prefix || !ctx.Esp)
        return;

    if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath)
    {
        log_line("%s stack_scan esp=0x%08lX slots=%d", prefix, static_cast<unsigned long>(ctx.Esp), slots);
    }

    for (int i = 0; i < slots; ++i)
    {
        const uintptr_t slot_addr = ctx.Esp + static_cast<uintptr_t>(i * sizeof(DWORD));
        DWORD value = 0;
        if (!safe_copy_memory(slot_addr, &value, sizeof(value)) || !value)
            continue;

        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(static_cast<uintptr_t>(value), &rva);
        if (std::strcmp(module_name, "<unknown>") != 0)
        {
            log_line(
                "%s stack_ret slot=%d stack=0x%08lX value=0x%08lX module=%s rva=0x%08lX in_main=%d",
                prefix,
                i,
                static_cast<unsigned long>(slot_addr),
                static_cast<unsigned long>(value),
                module_name,
                rva,
                is_in_main_module(static_cast<uintptr_t>(value)) ? 1 : 0);
            continue;
        }

        std::string detail;
        const std::string kind = classify_consumer_value(value, &detail);
        if (kind == "ptr_heap" || kind == "ptr_region")
        {
            log_line(
                "%s stack_ptr slot=%d stack=0x%08lX value=0x%08lX kind=%s detail=%s",
                prefix,
                i,
                static_cast<unsigned long>(slot_addr),
                static_cast<unsigned long>(value),
                kind.c_str(),
                detail.empty() ? "-" : detail.c_str());
        }
    }
}

bool is_consumer_upstream_candidate_rva(unsigned long rva)
{
    if (!rva || rva >= kConsumerUpstreamMaxCandidateRva)
        return false;

    switch (rva)
    {
    case kConsumerImageClassMapRva:
    case kConsumerAssetClassLookupRva:
    case kConsumerRenderTableRva:
    case kConsumerSubmitFlagsRva:
    case kConsumerRenderTableZeroPathRva:
    case kConsumerRenderTableCompareRva:
    case kConsumerRenderTableMatchBranchRva:
    case kConsumerRenderTableNonZeroBranchRva:
        return false;
    default:
        return true;
    }
}

bool is_consumer_upstream_candidate_rva_relaxed(unsigned long rva)
{
    if (!rva)
        return false;

    switch (rva)
    {
    case kConsumerImageClassMapRva:
    case kConsumerAssetClassLookupRva:
    case kConsumerRenderTableRva:
    case kConsumerSubmitFlagsRva:
    case kConsumerRenderTableZeroPathRva:
    case kConsumerRenderTableCompareRva:
    case kConsumerRenderTableMatchBranchRva:
    case kConsumerRenderTableNonZeroBranchRva:
        return false;
    default:
        return true;
    }
}

bool read_stack_dword(const CONTEXT& ctx, int slot, DWORD* out_value);

bool is_consumer_upstream_starter_rva(unsigned long rva)
{
    switch (rva)
    {
    case kConsumerUpstreamPreferredReturnSiteARva:
    case kConsumerUpstreamPreferredReturnSiteBRva:
    case kConsumerUpstreamStarterReturnSiteCRva:
    case kConsumerUpstreamStarterReturnSiteDRva:
    case kConsumerUpstreamStarterReturnSiteERva:
        return true;
    default:
        return false;
    }
}

bool is_consumer_upstream_probe_rva(unsigned long rva)
{
    switch (rva)
    {
    case kConsumerUpstreamProbePreferredReturnSiteARva:
    case kConsumerUpstreamProbePreferredReturnSiteBRva:
    case kConsumerUpstreamProbePreferredReturnSiteCRva:
    case kConsumerUpstreamProbeReturnSiteDRva:
    case kConsumerUpstreamProbeReturnSiteERva:
    case kConsumerUpstreamProbeReturnSiteFRva:
    case kConsumerUpstreamProbeReturnSiteGRva:
        return true;
    default:
        return false;
    }
}

const char* consumer_upstream_bucket_name(ConsumerUpstreamBucket bucket)
{
    switch (bucket)
    {
    case ConsumerUpstreamBucket::StarterOwned:
        return "starter_owned";
    case ConsumerUpstreamBucket::ProbeOwned:
        return "probe_owned";
    default:
        return "unknown";
    }
}

ConsumerUpstreamBucket classify_consumer_upstream_bucket_from_stack(const CONTEXT& ctx, int slots = 16)
{
    int starter_hits = 0;
    int probe_hits = 0;
    for (int slot = 0; slot < slots; ++slot)
    {
        DWORD value = 0;
        if (!read_stack_dword(ctx, slot, &value) || !value)
            continue;

        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(static_cast<uintptr_t>(value), &rva);
        if (std::strcmp(module_name, "<unknown>") == 0 || !is_in_main_module(static_cast<uintptr_t>(value)))
            continue;

        if (is_consumer_upstream_starter_rva(rva))
            starter_hits += 1;
        if (is_consumer_upstream_probe_rva(rva))
            probe_hits += 1;
    }

    if (probe_hits > starter_hits && probe_hits > 0)
        return ConsumerUpstreamBucket::ProbeOwned;
    if (starter_hits > probe_hits && starter_hits > 0)
        return ConsumerUpstreamBucket::StarterOwned;
    return ConsumerUpstreamBucket::Unknown;
}

int score_consumer_upstream_candidate(unsigned long rva, int slot, ConsumerUpstreamBucket bucket)
{
    int score = 0;

    if (bucket == ConsumerUpstreamBucket::StarterOwned)
    {
        if (rva == kConsumerUpstreamPreferredReturnSiteBRva || rva == kConsumerUpstreamPreferredReturnSiteARva)
            score += 200;
        else if (rva == kConsumerUpstreamStarterReturnSiteCRva)
            score += 180;
        else if (rva == kConsumerUpstreamStarterReturnSiteDRva || rva == kConsumerUpstreamStarterReturnSiteERva)
            score += 140;
        else if (is_consumer_upstream_starter_rva(rva))
            score += 100;
    }
    else if (bucket == ConsumerUpstreamBucket::ProbeOwned)
    {
        if (rva == kConsumerUpstreamProbePreferredReturnSiteARva ||
            rva == kConsumerUpstreamProbePreferredReturnSiteBRva ||
            rva == kConsumerUpstreamProbePreferredReturnSiteCRva)
        {
            score += 220;
        }
        else if (rva == kConsumerUpstreamProbeReturnSiteDRva ||
                 rva == kConsumerUpstreamProbeReturnSiteERva ||
                 rva == kConsumerUpstreamProbeReturnSiteFRva ||
                 rva == kConsumerUpstreamProbeReturnSiteGRva)
        {
            score += 180;
        }
        else if (is_consumer_upstream_probe_rva(rva))
        {
            score += 120;
        }
    }
    else
    {
        if (rva == kConsumerUpstreamPreferredReturnSiteBRva || rva == kConsumerUpstreamPreferredReturnSiteARva)
            score += 160;
        else if (rva == kConsumerUpstreamProbePreferredReturnSiteARva ||
                 rva == kConsumerUpstreamProbePreferredReturnSiteBRva ||
                 rva == kConsumerUpstreamProbePreferredReturnSiteCRva)
            score += 150;
        else if (is_consumer_upstream_starter_rva(rva) || is_consumer_upstream_probe_rva(rva))
            score += 100;
    }

    score += std::max(0, 32 - slot);
    return score;
}

bool is_consumer_upstream_preferred_for_bucket(unsigned long rva, ConsumerUpstreamBucket bucket)
{
    if (bucket == ConsumerUpstreamBucket::StarterOwned)
        return rva == kConsumerUpstreamPreferredReturnSiteARva || rva == kConsumerUpstreamPreferredReturnSiteBRva;
    if (bucket == ConsumerUpstreamBucket::ProbeOwned)
    {
        return rva == kConsumerUpstreamProbePreferredReturnSiteARva ||
               rva == kConsumerUpstreamProbePreferredReturnSiteBRva ||
               rva == kConsumerUpstreamProbePreferredReturnSiteCRva;
    }
    return rva == kConsumerUpstreamPreferredReturnSiteARva ||
           rva == kConsumerUpstreamPreferredReturnSiteBRva ||
           rva == kConsumerUpstreamProbePreferredReturnSiteARva ||
           rva == kConsumerUpstreamProbePreferredReturnSiteBRva ||
           rva == kConsumerUpstreamProbePreferredReturnSiteCRva;
}

bool read_stack_dword(const CONTEXT& ctx, int slot, DWORD* out_value)
{
    if (!ctx.Esp || slot < 0 || !out_value)
        return false;

    const uintptr_t slot_addr = ctx.Esp + static_cast<uintptr_t>(slot * sizeof(DWORD));
    return safe_copy_memory(slot_addr, out_value, sizeof(*out_value));
}

void append_pointer_anchor_if_valid(
    std::vector<ConsumerAnchorSnapshot>& anchors,
    std::unordered_set<std::string>& seen_contexts,
    const char* context,
    DWORD value,
    int before_slots = 4,
    int after_slots = 8)
{
    if (!context || !*context || !value)
        return;

    std::string detail;
    const std::string kind = classify_consumer_value(value, &detail);
    if (kind != "ptr_heap" && kind != "ptr_region")
        return;

    if (!seen_contexts.insert(context).second)
        return;

    anchors.push_back({context, static_cast<uintptr_t>(value), before_slots, after_slots});
}

void append_pointer_anchor_from_object_slot_if_valid(
    std::vector<ConsumerAnchorSnapshot>& anchors,
    std::unordered_set<std::string>& seen_contexts,
    const char* context,
    uintptr_t base_addr,
    int slot_index,
    int before_slots = 4,
    int after_slots = 8)
{
    if (!base_addr || slot_index < 0)
        return;

    DWORD value = 0;
    const uintptr_t slot_addr = base_addr + static_cast<uintptr_t>(slot_index * sizeof(DWORD));
    if (!safe_copy_memory(slot_addr, &value, sizeof(value)))
        return;

    append_pointer_anchor_if_valid(anchors, seen_contexts, context, value, before_slots, after_slots);
}

void arm_consumer_upstream_return_traces_from_stack_locked(const CONTEXT& ctx, unsigned long long trace_id, const std::string& path)
{
    if (!ctx.Esp)
        return;

    const int max_slots = g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath ? 40 : 20;
    const ConsumerUpstreamBucket bucket = classify_consumer_upstream_bucket_from_stack(ctx, max_slots);
    const int max_to_arm = bucket == ConsumerUpstreamBucket::ProbeOwned ? 6 : 4;
    std::vector<ConsumerUpstreamCandidate> candidates;
    std::unordered_set<uintptr_t> armed_addrs;
    for (int slot = 0; slot < max_slots; ++slot)
    {
        DWORD value = 0;
        if (!read_stack_dword(ctx, slot, &value) || !value)
            continue;

        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(static_cast<uintptr_t>(value), &rva);
        if (std::strcmp(module_name, "<unknown>") == 0)
            continue;
        if (!is_executable_address(static_cast<uintptr_t>(value)))
            continue;
        const bool in_main = is_in_main_module(static_cast<uintptr_t>(value));
        if (!in_main && g_probe_mode != ProbeMode::ClassFamilyMaterializationWritepath)
            continue;
        if (in_main && !(g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath
            ? is_consumer_upstream_candidate_rva_relaxed(rva)
            : is_consumer_upstream_candidate_rva(rva)))
            continue;

        ConsumerUpstreamCandidate candidate;
        candidate.slot = slot;
        candidate.addr = static_cast<uintptr_t>(value);
        candidate.rva = rva;
        candidate.module_name = module_name;
        candidate.score = score_consumer_upstream_candidate(rva, slot, bucket);
        candidate.preferred = is_consumer_upstream_preferred_for_bucket(rva, bucket) ? 1 : 0;
        candidates.push_back(candidate);
    }

    std::sort(candidates.begin(), candidates.end(), [](const ConsumerUpstreamCandidate& a, const ConsumerUpstreamCandidate& b)
    {
        if (a.score != b.score)
            return a.score > b.score;
        if (a.preferred != b.preferred)
            return a.preferred > b.preferred;
        if (a.slot != b.slot)
            return a.slot < b.slot;
        return a.rva < b.rva;
    });

    log_line(
        "consumer_upstream_bucket bucket=%s candidates=%u trace=%llu path=%s",
        consumer_upstream_bucket_name(bucket),
        static_cast<unsigned>(candidates.size()),
        trace_id,
        path.c_str());

    for (const auto& candidate : candidates)
    {
        if (armed_addrs.size() >= static_cast<size_t>(max_to_arm))
            break;
        if (!armed_addrs.insert(candidate.addr).second)
            continue;

        char label[96] {};
        std::snprintf(label, sizeof(label), "consumer_upstream_ret_%08lX", candidate.rva);
        arm_exec_trace_locked(label, candidate.addr, trace_id, path, 2);
        log_line(
            "consumer_upstream_arm slot=%d addr=0x%08lX module=%s rva=0x%08lX bucket=%s preferred=%d score=%d trace=%llu path=%s",
            candidate.slot,
            static_cast<unsigned long>(candidate.addr),
            candidate.module_name,
            candidate.rva,
            consumer_upstream_bucket_name(bucket),
            candidate.preferred,
            candidate.score,
            trace_id,
            path.c_str());
    }
}

void log_consumer_upstream_hit_context(const std::string& label, unsigned hit, const CONTEXT& ctx)
{
    log_line(
        "consumer_upstream_hit_summary label=%s hit=%u eip=0x%08lX eax=0x%08lX esi=0x%08lX edi=0x%08lX esp=0x%08lX",
        label.c_str(),
        hit,
        ctx.Eip,
        ctx.Eax,
        ctx.Esi,
        ctx.Edi,
        ctx.Esp);

    maybe_apply_entry_wrapper_override(0, ctx.Eip, ctx.Edi, label, hit);

    log_stack_return_candidates(label.c_str(), ctx, 12);

    std::vector<ConsumerAnchorSnapshot> anchors;
    std::unordered_set<std::string> seen_contexts;
    append_pointer_anchor_if_valid(anchors, seen_contexts, "upstream_edi", ctx.Edi);
    append_pointer_anchor_if_valid(anchors, seen_contexts, "upstream_esi", ctx.Esi);
    append_pointer_anchor_if_valid(anchors, seen_contexts, "upstream_eax", ctx.Eax);

    DWORD stack_value = 0;
    if (read_stack_dword(ctx, 0, &stack_value))
        append_pointer_anchor_if_valid(anchors, seen_contexts, "upstream_stack_slot_0", stack_value);
    if (read_stack_dword(ctx, 1, &stack_value))
        append_pointer_anchor_if_valid(anchors, seen_contexts, "upstream_stack_slot_1", stack_value);
    if (read_stack_dword(ctx, 8, &stack_value))
        append_pointer_anchor_if_valid(anchors, seen_contexts, "upstream_stack_slot_8", stack_value);

    const uintptr_t render_lookup = g_last_consumer_render_lookup_addr.load();
    if (ctx.Eax && render_lookup)
    {
        const uintptr_t span_low = std::min<uintptr_t>(ctx.Eax, render_lookup);
        const uintptr_t span_high = std::max<uintptr_t>(ctx.Eax, render_lookup);
        const uintptr_t span_base = span_low >= 0x10 ? span_low - 0x10 : span_low;
        const uintptr_t span_end = span_high + 0x20;
        const int span_dwords = static_cast<int>(((span_end - span_base) / sizeof(uint32_t)) + 1);
        if (span_dwords > 0 && span_dwords <= 96)
        {
            g_lookup_family_span_base = span_base;
            g_lookup_family_span_dwords = span_dwords;
            log_consumer_span_snapshot("lookup_family_span", hit == 1 ? "first_hit" : "later_hit", span_base, span_dwords);
        }
    }

    for (const auto& anchor : anchors)
        log_consumer_anchor_snapshot(anchor.context.c_str(), hit == 1 ? "first_hit" : "later_hit", anchor.base_addr, anchor.before_slots, anchor.after_slots);

    const bool minimal_bridge_provenance_trace =
        g_probe_mode == ProbeMode::ProducerCompactOverrideFocus &&
        g_producer_compact_override.enabled &&
        g_producer_compact_override.trace_bridge_to_first_producer;

    if (hit == 1 && !anchors.empty() && !minimal_bridge_provenance_trace)
    {
        char key[160] {};
        std::snprintf(
            key,
            sizeof(key),
            "upstream|%s|0x%08lX|0x%08lX|0x%08lX",
            label.c_str(),
            static_cast<unsigned long>(ctx.Edi),
            static_cast<unsigned long>(ctx.Esi),
            static_cast<unsigned long>(ctx.Eax));
        start_consumer_deferred_snapshots_once_locked(key, label.c_str(), ctx.Eip, anchors);
    }
}

void log_consumer_asset_lookup_entry_hit_context(unsigned hit, const CONTEXT& ctx, unsigned long long trace_id, const std::string& path)
{
    DWORD return_slot0 = 0;
    read_stack_dword(ctx, 0, &return_slot0);

    log_line(
        "consumer_asset_lookup_entry_hit_summary hit=%u tick=%lu edi=0x%08lX ecx=0x%08lX eax=0x%08lX edx=0x%08lX esi=0x%08lX ret0=0x%08lX",
        hit,
        static_cast<unsigned long>(GetTickCount()),
        static_cast<unsigned long>(ctx.Edi),
        static_cast<unsigned long>(ctx.Ecx),
        static_cast<unsigned long>(ctx.Eax),
        static_cast<unsigned long>(ctx.Edx),
        static_cast<unsigned long>(ctx.Esi),
        static_cast<unsigned long>(return_slot0));

    log_stack_return_candidates("consumer_asset_lookup_entry", ctx, 20);
    arm_consumer_upstream_return_traces_from_stack_locked(ctx, trace_id, path);

    uint32_t wrapper_minus3 = 0;
    uint32_t wrapper_minus1 = 0;
    uint32_t wrapper_plus3 = 0;
    if (capture_entry_wrapper_values(ctx.Edi, &wrapper_minus3, &wrapper_minus1, &wrapper_plus3))
    {
        log_entry_wrapper_snapshot("entry_hit", trace_id, ctx.Eip, ctx.Edi, wrapper_minus3, wrapper_minus1, wrapper_plus3, -1);
        if (wrapper_minus3 != 0 || wrapper_minus1 != 0 || wrapper_plus3 != 0)
        {
            log_line(
                "entry_wrapper_prepopulated trace=%llu base=0x%08lX minus3=0x%08lX minus1=0x%08lX plus3=0x%08lX",
                trace_id,
                static_cast<unsigned long>(ctx.Edi),
                static_cast<unsigned long>(wrapper_minus3),
                static_cast<unsigned long>(wrapper_minus1),
                static_cast<unsigned long>(wrapper_plus3));
            const CallerSelection sel = capture_relevant_caller();
            log_backtrace_selection(0, sel, "entry_wrapper_prepopulated", "asset_lookup_entry");
        }
    }
    maybe_apply_entry_wrapper_override(trace_id, ctx.Eip, ctx.Edi, "consumer_asset_lookup_entry", hit);

    std::vector<ConsumerAnchorSnapshot> anchors;
    std::unordered_set<std::string> seen_contexts;
    append_pointer_anchor_if_valid(anchors, seen_contexts, "asset_lookup_entry_edi", ctx.Edi);
    append_pointer_anchor_if_valid(anchors, seen_contexts, "asset_lookup_entry_ecx", ctx.Ecx);
    append_pointer_anchor_if_valid(anchors, seen_contexts, "asset_lookup_entry_eax", ctx.Eax);
    append_pointer_anchor_if_valid(anchors, seen_contexts, "asset_lookup_entry_edx", ctx.Edx);
    append_pointer_anchor_if_valid(anchors, seen_contexts, "asset_lookup_entry_esp", ctx.Esp);

    uint32_t owner_slot0 = 0;
    if (ctx.Edi && safe_copy_memory(ctx.Edi, &owner_slot0, sizeof(owner_slot0)))
        append_pointer_anchor_if_valid(anchors, seen_contexts, "asset_lookup_entry_owner_slot0", owner_slot0);

    for (const auto& anchor : anchors)
        log_consumer_anchor_snapshot(anchor.context.c_str(), hit == 1 ? "first_hit" : "later_hit", anchor.base_addr, anchor.before_slots, anchor.after_slots);

    const bool minimal_bridge_provenance_trace =
        g_probe_mode == ProbeMode::ProducerCompactOverrideFocus &&
        g_producer_compact_override.enabled &&
        g_producer_compact_override.trace_bridge_to_first_producer;

    if (hit == 1 && !anchors.empty() && !minimal_bridge_provenance_trace)
    {
        char key[160] {};
        std::snprintf(
            key,
            sizeof(key),
            "asset_lookup_entry|0x%08lX|0x%08lX|0x%08lX",
            static_cast<unsigned long>(ctx.Edi),
            static_cast<unsigned long>(ctx.Ecx),
            static_cast<unsigned long>(ctx.Eax));
        start_consumer_deferred_snapshots_once_locked(key, "consumer_asset_lookup_entry", ctx.Eip, anchors);
    }
}

void log_consumer_asset_lookup_hit_context(unsigned hit, unsigned long long trace_id, const std::string& path, CONTEXT& ctx)
{
    uint32_t class_head = 0;
    uint16_t class_word = 0;
    uint32_t class_slot2 = 0;
    uint32_t class_slot3 = 0;
    uint32_t class_slot4 = 0;
    uint32_t class_slot5 = 0;
    uint32_t class_slot6 = 0;
    if (ctx.Ecx)
    {
        safe_copy_memory(ctx.Ecx, &class_head, sizeof(class_head));
        safe_copy_memory(ctx.Ecx + 6, &class_word, sizeof(class_word));
        safe_copy_memory(ctx.Ecx + (2 * sizeof(uint32_t)), &class_slot2, sizeof(class_slot2));
        safe_copy_memory(ctx.Ecx + (3 * sizeof(uint32_t)), &class_slot3, sizeof(class_slot3));
        safe_copy_memory(ctx.Ecx + (4 * sizeof(uint32_t)), &class_slot4, sizeof(class_slot4));
        safe_copy_memory(ctx.Ecx + (5 * sizeof(uint32_t)), &class_slot5, sizeof(class_slot5));
        safe_copy_memory(ctx.Ecx + (6 * sizeof(uint32_t)), &class_slot6, sizeof(class_slot6));
    }

    maybe_apply_producer_compact_override(hit, trace_id, path, ctx, ctx.Ecx, class_head, &class_slot2, &class_slot3, &class_slot4, &class_slot5, &class_slot6);

    log_line(
        "consumer_asset_lookup_hit_summary hit=%u tick=%lu edi=0x%08lX eax=0x%08lX ecx=0x%08lX esi=0x%08lX",
        hit,
        static_cast<unsigned long>(GetTickCount()),
        static_cast<unsigned long>(ctx.Edi),
        static_cast<unsigned long>(ctx.Eax),
        static_cast<unsigned long>(ctx.Ecx),
        static_cast<unsigned long>(ctx.Esi));

    const bool capture_materialization_producer =
        (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus ? hit <= 4 : hit <= 2);
    if (capture_materialization_producer)
    {
        const CallerSelection sel = capture_relevant_caller();
        log_backtrace_selection(0, sel, "consumer_asset_class_lookup", "consumer_probe");
        g_latest_materialization_producer.valid = true;
        g_latest_materialization_producer.hit = hit;
        g_latest_materialization_producer.tick = GetTickCount();
        g_latest_materialization_producer.owner = ctx.Edi;
        g_latest_materialization_producer.source = ctx.Eax;
        g_latest_materialization_producer.class_ptr = ctx.Ecx;
        g_latest_materialization_producer.class_head = class_head;
        g_latest_materialization_producer.class_word = class_word;
        g_latest_materialization_producer.esi_nibble = static_cast<uint8_t>(ctx.Esi & 0xF);
        g_latest_materialization_producer.class_slot2 = class_slot2;
        g_latest_materialization_producer.class_slot3 = class_slot3;
        g_latest_materialization_producer.class_slot4 = class_slot4;
        g_latest_materialization_producer.class_slot5 = class_slot5;
        g_latest_materialization_producer.class_slot6 = class_slot6;
        g_latest_materialization_producer.selected_return = sel.selected_return;
        g_latest_materialization_producer.selected_signature.clear();
        for (size_t i = 0; i < sel.frames.size() && i < 4; ++i)
        {
            unsigned long rva = 0;
            const char* module = module_name_for_addr(sel.frames[i], &rva);
            if (!g_latest_materialization_producer.selected_signature.empty())
                g_latest_materialization_producer.selected_signature += " > ";
            if (module && std::strcmp(module, "<unknown>"))
            {
                char part[96] {};
                std::snprintf(part, sizeof(part), "%s:0x%06lX", module, rva & 0x00FFFFFFu);
                g_latest_materialization_producer.selected_signature += part;
            }
            else
            {
                char part[64] {};
                std::snprintf(part, sizeof(part), "<other>:0x%06lX", static_cast<unsigned long>(sel.frames[i] & 0x00FFFFFFu));
                g_latest_materialization_producer.selected_signature += part;
            }
        }
        log_materialization_producer_snapshot("asset_lookup_hit");
    }
    if (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus)
    {
        maybe_arm_follow_on_render_trace_after_asset_lookup();
        const char* phase = "producer_compact_override";
        bool armed = false;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_edi", ctx.Edi) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_eax", ctx.Eax) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_ecx", ctx.Ecx) || armed;
        if (!armed && g_latest_materialization_producer.class_head)
            maybe_arm_selector_root_from_candidate(phase, "asset_lookup_class_head", g_latest_materialization_producer.class_head);
    }
    if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath && g_policy_field_watches.empty())
    {
        const char* phase = "asset_lookup_hit";
        bool armed = false;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_edi", ctx.Edi) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_esi", ctx.Esi) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_eax", ctx.Eax) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "asset_lookup_ecx", ctx.Ecx) || armed;
        if (!armed && g_latest_materialization_producer.class_head)
            maybe_arm_selector_root_from_candidate(phase, "asset_lookup_class_head", g_latest_materialization_producer.class_head);
    }
    if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath)
    {
        auto it = g_temporal_selector_roots.find(ctx.Ecx);
        if (it != g_temporal_selector_roots.end())
        {
            const auto& obs = it->second;
            const DWORD age_ms = GetTickCount() - obs.first_tick;
            log_line("selector_root_temporal_match reason=asset_lookup_hit addr=0x%08lX age_ms=%lu sightings=%u first_plus3=0x%08lX first_plus4=0x%08lX first_plus5=0x%08lX first_plus6=0x%08lX",
                static_cast<unsigned long>(ctx.Ecx),
                static_cast<unsigned long>(age_ms),
                obs.sightings,
                static_cast<unsigned long>(obs.plus3),
                static_cast<unsigned long>(obs.plus4),
                static_cast<unsigned long>(obs.plus5),
                static_cast<unsigned long>(obs.plus6));
        }
    }
    log_stack_return_candidates("consumer_asset_class_lookup", ctx, 16);

    if (hit == 2 || hit == 4)
    {
        char phase[32] {};
        std::snprintf(phase, sizeof(phase), "hit_%u", hit);
        if (ctx.Edi)
            log_consumer_anchor_snapshot("asset_lookup_edi", phase, ctx.Edi, 4, 8);
        if (ctx.Eax)
            log_consumer_anchor_snapshot("asset_lookup_eax", phase, ctx.Eax, 4, 8);
        if (ctx.Ecx)
            log_consumer_anchor_snapshot("asset_lookup_ecx", phase, ctx.Ecx, 4, 8);
    }
}

void log_consumer_image_class_map_hit_context(unsigned hit, const CONTEXT& ctx)
{
    uint32_t output_value = 0;
    if (ctx.Esi)
        safe_copy_memory(ctx.Esi, &output_value, sizeof(output_value));

    log_line(
        "consumer_image_map_hit_summary hit=%u tick=%lu eax=0x%08lX esi=0x%08lX out_value=0x%08lX",
        hit,
        static_cast<unsigned long>(GetTickCount()),
        static_cast<unsigned long>(ctx.Eax),
        static_cast<unsigned long>(ctx.Esi),
        static_cast<unsigned long>(output_value));

    const CallerSelection sel = capture_relevant_caller();
    log_backtrace_selection(0, sel, "consumer_image_class_map", "consumer_probe");

    if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath && g_policy_field_watches.empty())
    {
        const char* phase = "image_class_map_hit";
        bool armed = false;
        armed = maybe_arm_selector_root_from_candidate(phase, "image_map_out_value", output_value) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "image_map_esi", ctx.Esi) || armed;
        armed = maybe_arm_selector_root_from_candidate(phase, "image_map_eax", ctx.Eax) || armed;
        if (!armed && ctx.Ecx)
            maybe_arm_selector_root_from_candidate(phase, "image_map_ecx", ctx.Ecx);
    }
}

void log_materialization_producer_snapshot(const char* reason)
{
    if (!g_latest_materialization_producer.valid)
        return;

    log_line(
        "materialization_producer_state reason=%s hit=%u tick=%lu owner=0x%08lX source=0x%08lX class=0x%08lX class_head=0x%08lX class_word=0x%04X esi_nibble=0x%X class_plus_2=0x%08lX class_plus_3=0x%08lX class_plus_4=0x%08lX class_plus_5=0x%08lX class_plus_6=0x%08lX selected=0x%08lX signature=%s",
        reason ? reason : "unknown",
        g_latest_materialization_producer.hit,
        static_cast<unsigned long>(g_latest_materialization_producer.tick),
        static_cast<unsigned long>(g_latest_materialization_producer.owner),
        static_cast<unsigned long>(g_latest_materialization_producer.source),
        static_cast<unsigned long>(g_latest_materialization_producer.class_ptr),
        static_cast<unsigned long>(g_latest_materialization_producer.class_head),
        static_cast<unsigned>(g_latest_materialization_producer.class_word),
        static_cast<unsigned>(g_latest_materialization_producer.esi_nibble),
        static_cast<unsigned long>(g_latest_materialization_producer.class_slot2),
        static_cast<unsigned long>(g_latest_materialization_producer.class_slot3),
        static_cast<unsigned long>(g_latest_materialization_producer.class_slot4),
        static_cast<unsigned long>(g_latest_materialization_producer.class_slot5),
        static_cast<unsigned long>(g_latest_materialization_producer.class_slot6),
        static_cast<unsigned long>(g_latest_materialization_producer.selected_return),
        g_latest_materialization_producer.selected_signature.c_str());
}

void log_selector_root_compact_snapshot(const char* reason, const char* phase, uintptr_t selector_root)
{
    if (!selector_root)
        return;
    uint32_t plus3 = 0;
    uint32_t plus4 = 0;
    uint32_t plus5 = 0;
    uint32_t plus6 = 0;
    safe_copy_memory(selector_root + (3 * sizeof(uint32_t)), &plus3, sizeof(plus3));
    safe_copy_memory(selector_root + (4 * sizeof(uint32_t)), &plus4, sizeof(plus4));
    safe_copy_memory(selector_root + (5 * sizeof(uint32_t)), &plus5, sizeof(plus5));
    safe_copy_memory(selector_root + (6 * sizeof(uint32_t)), &plus6, sizeof(plus6));
    log_line(
        "materialization_selector_state reason=%s phase=%s selector_root=0x%08lX plus3=0x%08lX plus4=0x%08lX plus5=0x%08lX plus6=0x%08lX",
        reason ? reason : "unknown",
        phase ? phase : "unknown",
        static_cast<unsigned long>(selector_root),
        static_cast<unsigned long>(plus3),
        static_cast<unsigned long>(plus4),
        static_cast<unsigned long>(plus5),
        static_cast<unsigned long>(plus6));
}

void log_xanim_focus_context(const CONTEXT& ctx, const std::vector<size_t>& indices)
{
    std::string target_list;
    for (size_t i = 0; i < indices.size(); ++i)
    {
        if (indices[i] >= g_touch_targets.size())
            continue;
        if (!target_list.empty())
            target_list += ",";
        target_list += g_touch_targets[indices[i]].text;
    }
    log_line("xanim_focus targets=%s", target_list.c_str());
    log_pointer_info("xanim_eax", ctx.Eax);
    log_pointer_info("xanim_ebx", ctx.Ebx);
    log_pointer_info("xanim_ecx", ctx.Ecx);
    log_pointer_info("xanim_edx", ctx.Edx);
    log_pointer_info("xanim_esi", ctx.Esi);
    log_pointer_info("xanim_edi", ctx.Edi);
    log_pointer_info("xanim_ebp", ctx.Ebp);
    log_pointer_info("xanim_esp", ctx.Esp);
    log_string_if_present("xanim_eax", ctx.Eax);
    log_string_if_present("xanim_ebx", ctx.Ebx);
    log_string_if_present("xanim_ecx", ctx.Ecx);
    log_string_if_present("xanim_edx", ctx.Edx);
    log_string_if_present("xanim_esi", ctx.Esi);
    log_string_if_present("xanim_edi", ctx.Edi);
    log_string_if_present("xanim_ebp", ctx.Ebp);
    log_stack_string_candidates(ctx, 10);
}

bool touch_targets_contain_text(const std::vector<size_t>& indices, const char* text)
{
    if (!text || !*text)
        return false;
    const std::string wanted = to_lower_copy(text);
    for (size_t index : indices)
    {
        if (index >= g_touch_targets.size())
            continue;
        if (to_lower_copy(g_touch_targets[index].text) == wanted)
            return true;
    }
    return false;
}

uintptr_t find_touch_target_addr_locked(const char* text)
{
    if (!text || !*text)
        return 0;

    const std::string wanted = to_lower_copy(text);
    for (const auto& target : g_touch_targets)
    {
        if (to_lower_copy(target.text) == wanted)
            return target.addr;
    }
    return 0;
}

void scan_live_xanim_asset_candidates(const char* target_name, uintptr_t target_name_addr)
{
    if (!target_name || !*target_name)
        return;

    const DWORD started = GetTickCount();
    const std::string alias_name = xanim_alias_for_name(target_name);
    const size_t target_capacity = std::strlen(target_name) + 1;
    std::vector<uintptr_t> name_addrs;
    if (target_name_addr)
    {
        record_observed_asset_address("xanim_name", target_name, target_name_addr, "touch_seed");
        if (!alias_name.empty())
        {
            const bool rewritten = rewrite_ascii_string_in_place(target_name_addr, alias_name, target_capacity);
            log_line("xanim_asset_name_rewrite name=%s alias=%s addr=0x%08lX rewritten=%d source=seed",
                target_name,
                alias_name.c_str(),
                static_cast<unsigned long>(target_name_addr),
                rewritten ? 1 : 0);
        }
        name_addrs.push_back(target_name_addr);
    }

    if (g_probe_mode == ProbeMode::XanimFocus && target_name_addr && alias_name.empty())
    {
        const int near_name_candidates = scan_live_xanim_asset_headers_near_name_addrs(target_name, name_addrs);
        const int near_name_patches = apply_runtime_patches_near_name_addrs(target_name, name_addrs);
        log_line("xanim_asset_scan_complete name=%s nameAddr=0x%08lX stringCopies=%d candidates=%d elapsed_ms=%lu mode=touch_near_only patches=%d",
            target_name,
            static_cast<unsigned long>(target_name_addr),
            1,
            near_name_candidates,
            static_cast<unsigned long>(GetTickCount() - started),
            near_name_patches);
        return;
    }

    std::string string_needle(target_name);
    string_needle.push_back('\0');
    const uintptr_t start_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMinimumApplicationAddress);
    const uintptr_t end_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMaximumApplicationAddress);
    uintptr_t cursor = start_addr;
    int string_occurrences = target_name_addr ? 1 : 0;

    while (cursor < end_addr)
    {
        MEMORY_BASIC_INFORMATION mbi {};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
            break;
        const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t next = region_base + mbi.RegionSize;
        if (region_is_readable(mbi) && mbi.RegionSize >= string_needle.size())
        {
            constexpr size_t kScanChunk = 0x10000;
            std::vector<char> chunk;
            chunk.reserve(kScanChunk + string_needle.size());
            size_t region_offset = 0;
            while (region_offset < mbi.RegionSize)
            {
                const size_t to_copy = std::min<size_t>(kScanChunk + string_needle.size(), mbi.RegionSize - region_offset);
                chunk.assign(to_copy, 0);
                if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                {
                    log_line("xanim_asset_scan_chunk_skip base=0x%08lX off=0x%08lX size=0x%08lX", static_cast<unsigned long>(region_base), static_cast<unsigned long>(region_offset), static_cast<unsigned long>(to_copy));
                    region_offset += kScanChunk;
                    continue;
                }
                for (size_t i = 0; i + string_needle.size() <= to_copy; ++i)
                {
                    if (std::memcmp(chunk.data() + i, string_needle.data(), string_needle.size()) != 0)
                        continue;
                    const uintptr_t found_addr = region_base + region_offset + i;
                    bool known = false;
                    for (const uintptr_t existing : name_addrs)
                    {
                        if (existing == found_addr)
                        {
                            known = true;
                            break;
                        }
                    }
                    if (!known)
                    {
                        if (!alias_name.empty())
                        {
                            const bool rewritten = rewrite_ascii_string_in_place(found_addr, alias_name, target_capacity);
                            log_line("xanim_asset_name_rewrite name=%s alias=%s addr=0x%08lX rewritten=%d source=scan",
                                target_name,
                                alias_name.c_str(),
                                static_cast<unsigned long>(found_addr),
                                rewritten ? 1 : 0);
                        }
                        name_addrs.push_back(found_addr);
                        record_observed_asset_address("xanim_name", target_name, found_addr, "scan_copy");
                        ++string_occurrences;
                        unsigned long string_rva = 0;
                        const char* string_module = module_name_for_addr(found_addr, &string_rva);
                        log_line("xanim_asset_name_copy name=%s addr=0x%08lX module=%s rva=0x%08lX",
                            target_name,
                            static_cast<unsigned long>(found_addr),
                            string_module,
                            string_rva);
                    }
                }
                if (to_copy <= string_needle.size())
                    break;
                region_offset += (kScanChunk > string_needle.size()) ? (kScanChunk - string_needle.size()) : to_copy;
            }
        }
        if (next <= cursor)
            break;
        cursor = next;
    }

    if (!alias_name.empty())
    {
        log_line("xanim_asset_scan_complete name=%s nameAddr=0x%08lX stringCopies=%d candidates=%d elapsed_ms=%lu mode=alias_rewrite_only",
            target_name,
            static_cast<unsigned long>(target_name_addr),
            string_occurrences,
            0,
            static_cast<unsigned long>(GetTickCount() - started));
        return;
    }

    int near_name_candidates = scan_live_xanim_asset_headers_near_name_addrs(target_name, name_addrs);
    const int near_name_patches = apply_runtime_patches_near_name_addrs(target_name, name_addrs);
    if (near_name_patches > 0)
    {
        log_line("xanim_asset_scan_short_circuit name=%s reason=near_name_patch patches=%d",
            target_name,
            near_name_patches);
        log_line("xanim_asset_scan_complete name=%s nameAddr=0x%08lX stringCopies=%d candidates=%d elapsed_ms=%lu",
            target_name,
            static_cast<unsigned long>(target_name_addr),
            string_occurrences,
            near_name_candidates,
            static_cast<unsigned long>(GetTickCount() - started));
        return;
    }
    int candidates = 0;
    cursor = start_addr;
    while (cursor < end_addr)
    {
        MEMORY_BASIC_INFORMATION mbi {};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
            break;
        const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t next = region_base + mbi.RegionSize;
        if (region_is_readable(mbi) && mbi.RegionSize >= sizeof(DWORD) + 104)
        {
            constexpr size_t kScanChunk = 0x10000;
            std::vector<char> chunk;
            chunk.reserve(kScanChunk + sizeof(DWORD));
            size_t region_offset = 0;
            while (region_offset < mbi.RegionSize)
            {
                const size_t to_copy = std::min<size_t>(kScanChunk + sizeof(DWORD), mbi.RegionSize - region_offset);
                chunk.assign(to_copy, 0);
                if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                {
                    region_offset += kScanChunk;
                    continue;
                }
                for (size_t i = 0; i + sizeof(DWORD) <= to_copy; ++i)
                {
                    DWORD value = 0;
                    std::memcpy(&value, chunk.data() + i, sizeof(value));
                    bool matches_name = false;
                    for (const uintptr_t name_addr : name_addrs)
                    {
                        if (value == static_cast<DWORD>(name_addr))
                        {
                            matches_name = true;
                            break;
                        }
                    }
                    if (!matches_name)
                        continue;

                    const uintptr_t header_addr = region_base + region_offset + i;
                    unsigned char header[104] {};
                    if (!safe_copy_memory(header_addr, header, sizeof(header)))
                        continue;
                    if (process_xanim_header_candidate(target_name, header_addr, header, "asset_scan"))
                        ++candidates;
                }
                if (to_copy <= sizeof(DWORD))
                    break;
                region_offset += (kScanChunk > sizeof(DWORD)) ? (kScanChunk - sizeof(DWORD)) : to_copy;
            }
        }
        if (next <= cursor)
            break;
        cursor = next;
    }

    log_line("xanim_asset_scan_complete name=%s nameAddr=0x%08lX stringCopies=%d candidates=%d elapsed_ms=%lu",
        target_name,
        static_cast<unsigned long>(target_name_addr),
        string_occurrences,
        candidates + near_name_candidates,
        static_cast<unsigned long>(GetTickCount() - started));
}

void scan_live_named_asset_refs(const char* prefix, const char* target_name, uintptr_t target_name_addr)
{
    if (!prefix || !*prefix || !target_name || !*target_name)
        return;

    const DWORD started = GetTickCount();
    std::vector<uintptr_t> name_addrs;
    if (target_name_addr)
    {
        name_addrs.push_back(target_name_addr);
        record_observed_asset_address(prefix, target_name, target_name_addr, "touch_seed");
    }

    std::string string_needle(target_name);
    string_needle.push_back('\0');
    const uintptr_t start_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMinimumApplicationAddress);
    const uintptr_t end_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMaximumApplicationAddress);
    uintptr_t cursor = start_addr;
    int string_occurrences = target_name_addr ? 1 : 0;
    int raw_refs = 0;
    int ref_logs = 0;
    std::unordered_set<uintptr_t> seen_ref_addrs;

    auto scan_refs_near_name_addrs = [&](const std::vector<uintptr_t>& addrs)
    {
        constexpr uintptr_t kNearWindow = 0x400000;
        for (const uintptr_t name_addr : addrs)
        {
            if (!name_addr)
                continue;

            const uintptr_t scan_start = (name_addr > kNearWindow) ? (name_addr - kNearWindow) : 0;
            const uintptr_t scan_end = name_addr + kNearWindow;
            uintptr_t near_cursor = scan_start;
            while (near_cursor < scan_end)
            {
                MEMORY_BASIC_INFORMATION mbi {};
                if (!VirtualQuery(reinterpret_cast<void*>(near_cursor), &mbi, sizeof(mbi)))
                    break;

                const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
                const uintptr_t next = region_base + mbi.RegionSize;
                if (region_is_readable(mbi) && mbi.RegionSize >= sizeof(DWORD))
                {
                    constexpr size_t kScanChunk = 0x10000;
                    std::vector<unsigned char> chunk;
                    chunk.reserve(kScanChunk + sizeof(DWORD));
                    size_t region_offset = 0;
                    while (region_offset < mbi.RegionSize)
                    {
                        const size_t to_copy = std::min<size_t>(kScanChunk + sizeof(DWORD), mbi.RegionSize - region_offset);
                        chunk.assign(to_copy, 0);
                        if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                        {
                            region_offset += kScanChunk;
                            continue;
                        }

                        for (size_t i = 0; i + sizeof(DWORD) <= to_copy; ++i)
                        {
                            DWORD value = 0;
                            std::memcpy(&value, chunk.data() + i, sizeof(value));
                            if (value != static_cast<DWORD>(name_addr))
                                continue;

                            const uintptr_t ref_addr = region_base + region_offset + i;
                            if (!seen_ref_addrs.insert(ref_addr).second)
                                continue;

                            ++raw_refs;
                            if (ref_logs < kNamedAssetRefLogMax)
                            {
                                log_named_asset_reference_detail(prefix, target_name, name_addr, ref_addr);
                                ++ref_logs;
                            }
                            record_observed_asset_address(prefix, target_name, ref_addr, "raw_ref", name_addr);
                        }

                        if (to_copy <= sizeof(DWORD))
                            break;
                        region_offset += (kScanChunk > sizeof(DWORD)) ? (kScanChunk - sizeof(DWORD)) : to_copy;
                    }
                }

                if (next <= near_cursor)
                    break;
                near_cursor = next;
            }
        }
    };

    if (target_name_addr)
    {
        unsigned long touch_rva = 0;
        const char* touch_module = module_name_for_addr(target_name_addr, &touch_rva);
        log_line("%s_asset_touch_name name=%s addr=0x%08lX module=%s rva=0x%08lX",
            prefix,
            target_name,
            static_cast<unsigned long>(target_name_addr),
            touch_module,
            touch_rva);
        log_bytes_around("asset_touch_name_bytes", target_name_addr, 16, 48);
        scan_refs_near_name_addrs(name_addrs);
        const bool full_scan_allowed = prefix && std::strcmp(prefix, "xmodel") == 0;
        if (g_probe_mode == ProbeMode::XanimFocus && !full_scan_allowed)
        {
            log_line("%s_asset_scan_complete name=%s nameAddr=0x%08lX stringCopies=%d rawRefs=%d elapsed_ms=%lu mode=touch_near_only",
                prefix,
                target_name,
                static_cast<unsigned long>(target_name_addr),
                1,
                raw_refs,
                static_cast<unsigned long>(GetTickCount() - started));
            return;
        }
    }

    while (cursor < end_addr)
    {
        MEMORY_BASIC_INFORMATION mbi {};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
            break;
        const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t next = region_base + mbi.RegionSize;
        if (region_is_readable(mbi) && mbi.RegionSize >= string_needle.size())
        {
            constexpr size_t kScanChunk = 0x10000;
            std::vector<char> chunk;
            chunk.reserve(kScanChunk + string_needle.size());
            size_t region_offset = 0;
            while (region_offset < mbi.RegionSize)
            {
                const size_t to_copy = std::min<size_t>(kScanChunk + string_needle.size(), mbi.RegionSize - region_offset);
                chunk.assign(to_copy, 0);
                if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                {
                    region_offset += kScanChunk;
                    continue;
                }
                for (size_t i = 0; i + string_needle.size() <= to_copy; ++i)
                {
                    if (std::memcmp(chunk.data() + i, string_needle.data(), string_needle.size()) != 0)
                        continue;
                    const uintptr_t found_addr = region_base + region_offset + i;
                    bool known = false;
                    for (const uintptr_t existing : name_addrs)
                    {
                        if (existing == found_addr)
                        {
                            known = true;
                            break;
                        }
                    }
                    if (!known)
                    {
                        name_addrs.push_back(found_addr);
                        record_observed_asset_address(prefix, target_name, found_addr, "scan_copy");
                        ++string_occurrences;
                        unsigned long string_rva = 0;
                        const char* string_module = module_name_for_addr(found_addr, &string_rva);
                        log_line("%s_asset_name_copy name=%s addr=0x%08lX module=%s rva=0x%08lX",
                            prefix,
                            target_name,
                            static_cast<unsigned long>(found_addr),
                            string_module,
                            string_rva);
                    }
                }
                if (to_copy <= string_needle.size())
                    break;
                region_offset += (kScanChunk > string_needle.size()) ? (kScanChunk - string_needle.size()) : to_copy;
            }
        }
        if (next <= cursor)
            break;
        cursor = next;
    }

    scan_refs_near_name_addrs(name_addrs);

    log_line("%s_asset_scan_complete name=%s nameAddr=0x%08lX stringCopies=%d rawRefs=%d elapsed_ms=%lu",
        prefix,
        target_name,
        static_cast<unsigned long>(target_name_addr),
        string_occurrences,
        raw_refs,
        static_cast<unsigned long>(GetTickCount() - started));
}

void scan_live_xanim_asset_headers_for_watchlist()
{
    const uintptr_t start_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMinimumApplicationAddress);
    const uintptr_t end_addr = reinterpret_cast<uintptr_t>(g_system_info.lpMaximumApplicationAddress);
    uintptr_t cursor = start_addr;
    int candidates = 0;
    std::unordered_set<uintptr_t> seen_headers;

    while (cursor < end_addr)
    {
        MEMORY_BASIC_INFORMATION mbi {};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
            break;

        const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t next = region_base + mbi.RegionSize;
        if (region_is_readable(mbi) && mbi.RegionSize >= 104)
        {
            constexpr size_t kScanChunk = 0x10000;
            std::vector<unsigned char> chunk;
            chunk.reserve(kScanChunk + 128);
            size_t region_offset = 0;
            while (region_offset < mbi.RegionSize)
            {
                const size_t to_copy = std::min<size_t>(kScanChunk + 128, mbi.RegionSize - region_offset);
                chunk.assign(to_copy, 0);
                if (!safe_copy_memory(region_base + region_offset, chunk.data(), to_copy))
                {
                    region_offset += kScanChunk;
                    continue;
                }

                for (size_t i = 0; i + 104 <= to_copy; i += 4)
                {
                    const uintptr_t header_addr = region_base + region_offset + i;
                    if (!seen_headers.insert(header_addr).second)
                        continue;

                    const unsigned char* header = chunk.data() + i;
                    const DWORD name_ptr = *reinterpret_cast<const DWORD*>(header + 0x00);
                    if (!name_ptr || !pointer_readable(name_ptr))
                        continue;

                    const std::string name_text = safe_read_ascii_string(name_ptr, 64);
                    if (name_text.empty())
                        continue;

                    const std::string name_lower = to_lower_copy(name_text);
                    if (g_watch_xanims.find(name_lower) == g_watch_xanims.end())
                        continue;

                    if (process_xanim_header_candidate(name_text.c_str(), header_addr, header, "header_scan"))
                        ++candidates;
                }

                if (to_copy <= 104)
                    break;
                region_offset += (kScanChunk > 104) ? (kScanChunk - 104) : to_copy;
            }
        }

        if (next <= cursor)
            break;
        cursor = next;
    }

    log_line("xanim_header_scan_complete candidates=%d", candidates);
}

DWORD WINAPI xanim_asset_census_thread(void*)
{
    log_line("xanim_asset_census_thread_started");
    const DWORD initial_delay_ms = xanim_asset_census_delay_ms();
    const DWORD repeat_delay_ms = xanim_asset_census_repeat_delay_ms();
    const int total_passes = xanim_asset_census_passes();
    Sleep(initial_delay_ms);
    for (int pass = 1; pass <= total_passes; ++pass)
    {
        const DWORD pass_started = GetTickCount();
        log_line("xanim_asset_census_begin pass=%d/%d delay_ms=%lu", pass, total_passes, static_cast<unsigned long>(pass == 1 ? initial_delay_ms : repeat_delay_ms));
        std::vector<std::string> target_names;
        std::vector<std::string> target_models;
        for (const auto& watch : g_watch_xanims)
        {
            if (!watch.empty())
                target_names.push_back(watch);
        }
        for (const auto& watch : g_watch_xmodels)
        {
            if (!watch.empty())
                target_models.push_back(watch);
        }
        for (const auto& expectation : g_xanim_expectations)
        {
            if (expectation.asset_name.empty())
                continue;
            bool seen = false;
            for (const auto& existing : target_names)
            {
                if (existing == expectation.asset_name)
                {
                    seen = true;
                    break;
                }
            }
            if (!seen)
                target_names.push_back(expectation.asset_name);
        }
        bool any_target_addr = false;
        const bool touch_ready = g_touch_trace_complete.load();
        log_line("xanim_asset_census_touch_state pass=%d touchReady=%d", pass, touch_ready ? 1 : 0);
        for (const auto& target_model : target_models)
        {
            uintptr_t target_addr = 0;
            if (touch_ready)
            {
                std::lock_guard<std::mutex> lock(g_state_mutex);
                target_addr = find_touch_target_addr_locked(target_model.c_str());
            }
            log_line("xmodel_asset_census_target name=%s addr=0x%08lX pass=%d",
                target_model.c_str(),
                static_cast<unsigned long>(target_addr),
                pass);
            if (!target_addr && pass == 1)
            {
                log_line("xmodel_asset_census_target_full_scan name=%s pass=%d reason=no_touch_addr",
                    target_model.c_str(),
                    pass);
            }
            if (target_addr)
                any_target_addr = true;
            scan_live_named_asset_refs("xmodel", target_model.c_str(), target_addr);
        }
        for (const auto& target_name : target_names)
        {
            uintptr_t target_addr = 0;
            if (touch_ready)
            {
                std::lock_guard<std::mutex> lock(g_state_mutex);
                target_addr = find_touch_target_addr_locked(target_name.c_str());
            }
            log_line("xanim_asset_census_target name=%s addr=0x%08lX pass=%d",
                target_name.c_str(),
                static_cast<unsigned long>(target_addr),
                pass);
            if (!target_addr && pass == 1)
            {
                log_line("xanim_asset_census_target_deferred name=%s pass=%d reason=no_touch_addr",
                    target_name.c_str(),
                    pass);
                continue;
            }
            if (target_addr)
                any_target_addr = true;
            scan_live_xanim_asset_candidates(target_name.c_str(), target_addr);
        }
        log_line("xanim_asset_census_targets_complete count=%u pass=%d mode=%s",
                static_cast<unsigned>(target_names.size() + target_models.size()),
                pass,
                (g_probe_mode == ProbeMode::XanimFocus) ? "xanim_focus_full" : "legacy");
        if (any_target_addr || pass > 1)
            scan_live_xanim_asset_headers_for_watchlist();
        else
            log_line("xanim_header_scan_deferred pass=%d reason=no_touch_addr", pass);
        if ((any_target_addr || pass > 1) && (pass == 1 || (pass % 2) == 0))
        {
            scan_expected_xanim_sections();
            apply_runtime_patches_via_expectations();
        }
        arm_touch_trace_pages();
        log_line("xanim_asset_census_pass_complete pass=%d elapsed_ms=%lu",
            pass,
            static_cast<unsigned long>(GetTickCount() - pass_started));
        if (pass < total_passes)
            Sleep(repeat_delay_ms);
    }
    return 0;
}

void log_xanim_resolver_state(const CONTEXT& ctx)
{
    DWORD query2 = 0;
    DWORD query3 = 0;
    DWORD cand0 = 0;
    DWORD cand1 = 0;
    DWORD cand2 = 0;
    DWORD cand3 = 0;
    safe_copy_memory(ctx.Edx + 8, &query2, sizeof(query2));
    safe_copy_memory(ctx.Edx + 0xC, &query3, sizeof(query3));
    safe_copy_memory(ctx.Eax + 8, &cand0, sizeof(cand0));
    safe_copy_memory(ctx.Eax + 0xC, &cand1, sizeof(cand1));
    safe_copy_memory(ctx.Eax + 0x10, &cand2, sizeof(cand2));
    safe_copy_memory(ctx.Eax + 0x14, &cand3, sizeof(cand3));

    const bool match0 = ctx.Ebx == cand0;
    const bool match1 = ctx.Edi == cand1;
    const bool match2 = query2 == cand2;
    const bool match3 = query3 == cand3;
    const bool full_match = match0 && match1 && match2 && match3;

    log_line("xanim_resolver_state query0=0x%08lX query1=0x%08lX query2=0x%08lX query3=0x%08lX cand0=0x%08lX cand1=0x%08lX cand2=0x%08lX cand3=0x%08lX match0=%d match1=%d match2=%d match3=%d full_match=%d",
        static_cast<unsigned long>(ctx.Ebx),
        static_cast<unsigned long>(ctx.Edi),
        static_cast<unsigned long>(query2),
        static_cast<unsigned long>(query3),
        static_cast<unsigned long>(cand0),
        static_cast<unsigned long>(cand1),
        static_cast<unsigned long>(cand2),
        static_cast<unsigned long>(cand3),
        match0 ? 1 : 0,
        match1 ? 1 : 0,
        match2 ? 1 : 0,
        match3 ? 1 : 0,
        full_match ? 1 : 0);

    log_pointer_info("xanim_resolver_edx", ctx.Edx);
    log_pointer_info("xanim_resolver_eax", ctx.Eax);
    log_pointer_info("xanim_resolver_eax_plus_4", ctx.Eax + 4);
    log_pointer_info("xanim_resolver_eax_plus_8", ctx.Eax + 8);
    log_string_if_present("xanim_resolver_eax_str", ctx.Eax);
    log_string_if_present("xanim_resolver_eax_plus_4_str", ctx.Eax + 4);
    log_stack_string_candidates(ctx, 12);
}

void log_xanim_resolver_branch_state(const char* label, const CONTEXT& ctx)
{
    const std::string ebx_text = safe_read_ascii_string(ctx.Ebx);
    const std::string eax_text = safe_read_ascii_string(ctx.Eax);
    const std::string edx_text = safe_read_ascii_string(ctx.Edx);
    log_line("xanim_resolver_branch label=%s ebx=0x%08lX eax=0x%08lX edx=0x%08lX ebx_str=%s eax_str=%s edx_str=%s",
        label ? label : "<null>",
        static_cast<unsigned long>(ctx.Ebx),
        static_cast<unsigned long>(ctx.Eax),
        static_cast<unsigned long>(ctx.Edx),
        ebx_text.empty() ? "<none>" : ebx_text.c_str(),
        eax_text.empty() ? "<none>" : eax_text.c_str(),
        edx_text.empty() ? "<none>" : edx_text.c_str());
}

void log_backtrace_frames(const char* prefix, unsigned skip = 0, unsigned max_frames = 8)
{
    void* frames_raw[32] {};
    const USHORT captured = CaptureStackBackTrace(skip, std::min<unsigned>(max_frames, static_cast<unsigned>(std::size(frames_raw))), frames_raw, nullptr);
    log_line("%s backtrace_count=%u", prefix, static_cast<unsigned>(captured));
    for (USHORT i = 0; i < captured; ++i)
    {
        const uintptr_t frame = reinterpret_cast<uintptr_t>(frames_raw[i]);
        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(frame, &rva);
        if (std::strcmp(module_name, "<unknown>") == 0)
            log_line("%s frame[%u]=0x%08lX module=<unknown>", prefix, static_cast<unsigned>(i), static_cast<unsigned long>(frame));
        else
            log_line("%s frame[%u]=0x%08lX module=%s rva=0x%08lX", prefix, static_cast<unsigned>(i), static_cast<unsigned long>(frame), module_name, rva);
    }
}

bool region_is_readable(const MEMORY_BASIC_INFORMATION& mbi)
{
    if (mbi.State != MEM_COMMIT)
        return false;
    if ((mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
        return false;

    const DWORD protect = mbi.Protect & 0xFFu;
    switch (protect)
    {
    case PAGE_READONLY:
    case PAGE_READWRITE:
    case PAGE_WRITECOPY:
    case PAGE_EXECUTE_READ:
    case PAGE_EXECUTE_READWRITE:
    case PAGE_EXECUTE_WRITECOPY:
        return true;
    default:
        return false;
    }
}

bool region_is_executable(const MEMORY_BASIC_INFORMATION& mbi)
{
    if (mbi.State != MEM_COMMIT)
        return false;
    if ((mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
        return false;

    const DWORD protect = mbi.Protect & 0xFFu;
    switch (protect)
    {
    case PAGE_EXECUTE:
    case PAGE_EXECUTE_READ:
    case PAGE_EXECUTE_READWRITE:
    case PAGE_EXECUTE_WRITECOPY:
        return true;
    default:
        return false;
    }
}

bool is_executable_address(uintptr_t addr)
{
    if (!addr)
        return false;

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(addr), &mbi, sizeof(mbi)))
        return false;
    return region_is_executable(mbi);
}

void enumerate_modules(bool verbose = true)
{
    g_modules.clear();

    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
    if (snap == INVALID_HANDLE_VALUE)
        return;

    MODULEENTRY32 me {};
    me.dwSize = sizeof(me);
    if (Module32First(snap, &me))
    {
        do
        {
            ModuleInfoLite info;
            info.base = me.hModule;
            info.size = me.modBaseSize;
            info.name = to_lower_copy(std::string(me.szModule));
            info.path = std::string(me.szExePath);
            g_modules.push_back(info);
        } while (Module32Next(snap, &me));
    }
    CloseHandle(snap);

    if (!verbose)
        return;

    log_line("module_count=%u", static_cast<unsigned>(g_modules.size()));
    for (const auto& module : g_modules)
    {
        log_line("module name=%s base=0x%08lX size=0x%08lX path=%s",
            module.name.c_str(),
            static_cast<unsigned long>(reinterpret_cast<uintptr_t>(module.base)),
            static_cast<unsigned long>(module.size),
            module.path.c_str());
    }
}

void load_probe_mode()
{
    const std::string mode_path = module_relative_path(L"..\\..\\..\\active_probe_mode.txt");
    FILE* file = std::fopen(mode_path.c_str(), "rb");
    if (!file)
    {
        g_probe_mode = ProbeMode::Safe;
        log_line("probe_mode path=%s value=%s source=default", mode_path.c_str(), probe_mode_name());
        return;
    }

    char buffer[128] {};
    const size_t count = std::fread(buffer, 1, sizeof(buffer) - 1, file);
    std::fclose(file);
    std::string value(buffer, count);
    value = to_lower_copy(value);
    value.erase(std::remove_if(value.begin(), value.end(), [](unsigned char c) {
        return c == '\r' || c == '\n' || c == ' ' || c == '\t';
    }), value.end());
    const size_t eq = value.find('=');
    if (eq != std::string::npos)
        value = value.substr(eq + 1);

    if (value == "bootstrap_guard_only")
        g_probe_mode = ProbeMode::BootstrapGuardOnly;
    else if (value == "render_opacity_focus")
        g_probe_mode = ProbeMode::RenderOpacityFocus;
    else if (value == "viewmodel_render_focus")
        g_probe_mode = ProbeMode::ViewmodelRenderFocus;
    else if (value == "xanim_focus")
        g_probe_mode = ProbeMode::XanimFocus;
    else if (value == "xanim_consumer_focus")
        g_probe_mode = ProbeMode::XanimConsumerFocus;
    else if (value == "xanim_asset_lookup_focus")
        g_probe_mode = ProbeMode::XanimAssetLookupFocus;
    else if (value == "producer_compact_override_focus")
        g_probe_mode = ProbeMode::ProducerCompactOverrideFocus;
    else if (value == "class_family_materialization_writepath")
        g_probe_mode = ProbeMode::ClassFamilyMaterializationWritepath;
    else
        g_probe_mode = ProbeMode::Safe;

    log_line("probe_mode path=%s value=%s source=file", mode_path.c_str(), probe_mode_name());
}

void load_entry_wrapper_override()
{
    g_entry_wrapper_override = EntryWrapperOverrideConfig {};
    g_entry_wrapper_override_applied = false;

    const std::string config_path = module_relative_path(L"..\\..\\..\\active_entry_wrapper_override.txt");
    FILE* file = std::fopen(config_path.c_str(), "rb");
    if (!file)
    {
        log_line("entry_wrapper_override path=%s enabled=0 source=default", config_path.c_str());
        return;
    }

    char buffer[4096] {};
    const size_t count = std::fread(buffer, 1, sizeof(buffer) - 1, file);
    std::fclose(file);
    std::string text(buffer, count);

    auto trim_copy = [](std::string value) {
        while (!value.empty() && (value.front() == ' ' || value.front() == '\t' || value.front() == '\r' || value.front() == '\n'))
            value.erase(value.begin());
        while (!value.empty() && (value.back() == ' ' || value.back() == '\t' || value.back() == '\r' || value.back() == '\n'))
            value.pop_back();
        return value;
    };

    auto parse_u32 = [&](const std::string& raw, uint32_t* out_value) -> bool {
        if (!out_value)
            return false;
        std::string value = trim_copy(raw);
        if (value.empty())
            return false;
        int base = 10;
        if (value.size() > 2 && value[0] == '0' && (value[1] == 'x' || value[1] == 'X'))
        {
            value = value.substr(2);
            base = 16;
        }
        char* end = nullptr;
        const unsigned long parsed = std::strtoul(value.c_str(), &end, base);
        if (!end || *end != '\0')
            return false;
        *out_value = static_cast<uint32_t>(parsed);
        return true;
    };

    size_t start = 0;
    while (start < text.size())
    {
        size_t end = text.find_first_of("\r\n", start);
        if (end == std::string::npos)
            end = text.size();
        std::string line = trim_copy(text.substr(start, end - start));
        start = end + 1;
        if (line.empty() || line[0] == '#')
            continue;

        const size_t eq = line.find('=');
        if (eq == std::string::npos)
            continue;

        const std::string key = to_lower_copy(trim_copy(line.substr(0, eq)));
        const std::string value = trim_copy(line.substr(eq + 1));
        if (key == "enabled")
        {
            g_entry_wrapper_override.enabled = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_minus1")
        {
            g_entry_wrapper_override.patch_minus1 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_plus3")
        {
            g_entry_wrapper_override.patch_plus3 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "minus1")
        {
            parse_u32(value, &g_entry_wrapper_override.minus1_value);
        }
        else if (key == "minus1_rva")
        {
            g_entry_wrapper_override.use_minus1_rva = parse_u32(value, &g_entry_wrapper_override.minus1_rva);
        }
        else if (key == "plus3")
        {
            parse_u32(value, &g_entry_wrapper_override.plus3_value);
        }
        else if (key == "plus3_rva")
        {
            g_entry_wrapper_override.use_plus3_rva = parse_u32(value, &g_entry_wrapper_override.plus3_rva);
        }
        else if (key == "label")
        {
            g_entry_wrapper_override.label = value;
        }
        else if (key == "apply_label")
        {
            g_entry_wrapper_override.apply_label = value;
        }
        else if (key == "target_hit")
        {
            uint32_t target_hit = 0;
            if (parse_u32(value, &target_hit) && target_hit > 0)
                g_entry_wrapper_override.target_hit = target_hit;
        }
    }

    if (!(g_entry_wrapper_override.patch_minus1 || g_entry_wrapper_override.patch_plus3))
        g_entry_wrapper_override.enabled = false;

    log_line(
        "entry_wrapper_override path=%s enabled=%d patch_minus1=%d minus1=0x%08lX use_minus1_rva=%d minus1_rva=0x%08lX patch_plus3=%d plus3=0x%08lX use_plus3_rva=%d plus3_rva=0x%08lX target_hit=%u apply_label=%s label=%s source=file",
        config_path,
        g_entry_wrapper_override.enabled ? 1 : 0,
        g_entry_wrapper_override.patch_minus1 ? 1 : 0,
        static_cast<unsigned long>(g_entry_wrapper_override.minus1_value),
        g_entry_wrapper_override.use_minus1_rva ? 1 : 0,
        static_cast<unsigned long>(g_entry_wrapper_override.minus1_rva),
        g_entry_wrapper_override.patch_plus3 ? 1 : 0,
        static_cast<unsigned long>(g_entry_wrapper_override.plus3_value),
        g_entry_wrapper_override.use_plus3_rva ? 1 : 0,
        static_cast<unsigned long>(g_entry_wrapper_override.plus3_rva),
        g_entry_wrapper_override.target_hit,
        g_entry_wrapper_override.apply_label.empty() ? "<any>" : g_entry_wrapper_override.apply_label.c_str(),
        g_entry_wrapper_override.label.empty() ? "<none>" : g_entry_wrapper_override.label.c_str());
}

void load_producer_compact_override()
{
    g_producer_compact_override = ProducerCompactOverrideConfig {};
    g_producer_compact_override_applied = false;
    g_producer_follow_on_render_armed = false;
    g_producer_class_trace_started = false;
    g_seed_normalization = SeedNormalizationState {};

    const std::string stability_config_path = module_relative_path(L"..\\..\\..\\active_producer_class_override_stability.txt");
    const std::string default_config_path = module_relative_path(L"..\\..\\..\\active_producer_class_override.txt");
    FILE* file = std::fopen(stability_config_path.c_str(), "rb");
    const char* config_path = stability_config_path.c_str();
    if (!file)
    {
        file = std::fopen(default_config_path.c_str(), "rb");
        config_path = default_config_path.c_str();
    }
    if (!file)
    {
        log_line("producer_compact_override path=%s enabled=0 source=default", default_config_path.c_str());
        return;
    }

    char buffer[4096] {};
    const size_t count = std::fread(buffer, 1, sizeof(buffer) - 1, file);
    std::fclose(file);
    std::string text(buffer, count);

    auto trim_copy = [](std::string value) {
        while (!value.empty() && (value.front() == ' ' || value.front() == '\t' || value.front() == '\r' || value.front() == '\n'))
            value.erase(value.begin());
        while (!value.empty() && (value.back() == ' ' || value.back() == '\t' || value.back() == '\r' || value.back() == '\n'))
            value.pop_back();
        return value;
    };

    auto parse_u32 = [&](const std::string& raw, uint32_t* out_value) -> bool {
        if (!out_value)
            return false;
        std::string value = trim_copy(raw);
        if (value.empty())
            return false;
        int base = 10;
        if (value.size() > 2 && value[0] == '0' && (value[1] == 'x' || value[1] == 'X'))
        {
            value = value.substr(2);
            base = 16;
        }
        char* end = nullptr;
        const unsigned long parsed = std::strtoul(value.c_str(), &end, base);
        if (!end || *end != '\0')
            return false;
        *out_value = static_cast<uint32_t>(parsed);
        return true;
    };

    size_t start = 0;
    while (start < text.size())
    {
        size_t end = text.find_first_of("\r\n", start);
        if (end == std::string::npos)
            end = text.size();
        std::string line = trim_copy(text.substr(start, end - start));
        start = end + 1;
        if (line.empty() || line[0] == '#')
            continue;

        const size_t eq = line.find('=');
        if (eq == std::string::npos)
            continue;

        const std::string key = to_lower_copy(trim_copy(line.substr(0, eq)));
        const std::string value = trim_copy(line.substr(eq + 1));
        if (key == "enabled")
        {
            g_producer_compact_override.enabled = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus5")
        {
            g_producer_compact_override.patch_class_plus5 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus6")
        {
            g_producer_compact_override.patch_class_plus6 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "trace_target_family_steps")
        {
            g_producer_compact_override.trace_target_family_steps = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "trace_bridge_to_first_producer")
        {
            g_producer_compact_override.trace_bridge_to_first_producer = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "stop_after_bridge_candidate_birth")
        {
            g_producer_compact_override.stop_after_bridge_candidate_birth = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "arm_render_from_startup")
        {
            g_producer_compact_override.arm_render_from_startup = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_pointer_swap_34")
        {
            g_producer_compact_override.patch_pointer_swap_34 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_pointer_family_from_initial")
        {
            g_producer_compact_override.patch_pointer_family_from_initial = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_head_from_initial")
        {
            g_producer_compact_override.patch_class_head_from_initial = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_head")
        {
            g_producer_compact_override.patch_class_head = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus2_from_initial")
        {
            g_producer_compact_override.patch_class_plus2_from_initial = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus2")
        {
            g_producer_compact_override.patch_class_plus2 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus3_from_initial")
        {
            g_producer_compact_override.patch_class_plus3_from_initial = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus3")
        {
            g_producer_compact_override.patch_class_plus3 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus4_from_initial")
        {
            g_producer_compact_override.patch_class_plus4_from_initial = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus4")
        {
            g_producer_compact_override.patch_class_plus4 = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "patch_class_plus5_from_initial")
        {
            g_producer_compact_override.patch_class_plus5_from_initial = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "class_head")
        {
            parse_u32(value, &g_producer_compact_override.class_head_value);
        }
        else if (key == "class_plus2")
        {
            parse_u32(value, &g_producer_compact_override.class_plus2_value);
        }
        else if (key == "class_plus3")
        {
            parse_u32(value, &g_producer_compact_override.class_plus3_value);
        }
        else if (key == "class_plus4")
        {
            parse_u32(value, &g_producer_compact_override.class_plus4_value);
        }
        else if (key == "class_plus5")
        {
            parse_u32(value, &g_producer_compact_override.class_plus5_value);
        }
        else if (key == "class_plus6")
        {
            parse_u32(value, &g_producer_compact_override.class_plus6_value);
        }
        else if (key == "follow_on_render")
        {
            g_producer_compact_override.follow_on_render = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "target_hit")
        {
            uint32_t parsed = 0;
            if (parse_u32(value, &parsed) && parsed > 0)
                g_producer_compact_override.target_hit = static_cast<unsigned>(parsed);
        }
        else if (key == "target_mode")
        {
            const std::string mode = to_lower_copy(value);
            if (mode == "first_distinct_after_initial" || mode == "distinct_after_initial")
                g_producer_compact_override.target_first_distinct_after_initial = true;
            else
                g_producer_compact_override.target_first_distinct_after_initial = false;
        }
        else if (key == "bridge_trace_steps")
        {
            uint32_t parsed = 0;
            if (parse_u32(value, &parsed) && parsed > 0)
                g_producer_compact_override.bridge_trace_steps = static_cast<unsigned>(parsed);
        }
        else if (key == "require_bridge_bucket")
        {
            g_producer_compact_override.require_bridge_bucket = (value == "1" || to_lower_copy(value) == "true" || to_lower_copy(value) == "yes");
        }
        else if (key == "bridge_required_minus1")
        {
            parse_u32(value, &g_producer_compact_override.bridge_required_minus1);
        }
        else if (key == "bridge_required_plus3")
        {
            parse_u32(value, &g_producer_compact_override.bridge_required_plus3);
        }
        else if (key == "label")
        {
            g_producer_compact_override.label = value;
        }
    }

    if (!(g_producer_compact_override.patch_pointer_swap_34 ||
          g_producer_compact_override.patch_pointer_family_from_initial ||
          g_producer_compact_override.patch_class_head_from_initial ||
          g_producer_compact_override.patch_class_head ||
          g_producer_compact_override.patch_class_plus2_from_initial ||
          g_producer_compact_override.patch_class_plus2 ||
          g_producer_compact_override.patch_class_plus3_from_initial ||
          g_producer_compact_override.patch_class_plus3 ||
          g_producer_compact_override.patch_class_plus4_from_initial ||
          g_producer_compact_override.patch_class_plus4 ||
          g_producer_compact_override.patch_class_plus5_from_initial ||
          g_producer_compact_override.patch_class_plus5 ||
          g_producer_compact_override.patch_class_plus6 ||
          g_producer_compact_override.trace_target_family_steps ||
          g_producer_compact_override.trace_bridge_to_first_producer))
        g_producer_compact_override.enabled = false;

    log_line(
        "producer_compact_override path=%s enabled=%d target_mode=%s target_hit=%u patch_pointer_swap_34=%d patch_pointer_family_from_initial=%d patch_class_head_from_initial=%d patch_class_head=%d class_head=0x%08lX patch_class_plus2_from_initial=%d patch_class_plus2=%d class_plus2=0x%08lX patch_class_plus3_from_initial=%d patch_class_plus3=%d class_plus3=0x%08lX patch_class_plus4_from_initial=%d patch_class_plus4=%d class_plus4=0x%08lX patch_class_plus5_from_initial=%d patch_class_plus5=%d class_plus5=0x%08lX patch_class_plus6=%d class_plus6=0x%08lX trace_target_family_steps=%d trace_bridge_to_first_producer=%d stop_after_bridge_candidate_birth=%d bridge_trace_steps=%u require_bridge_bucket=%d bridge_required_minus1=0x%08lX bridge_required_plus3=0x%08lX arm_render_from_startup=%d follow_on_render=%d label=%s source=file",
        config_path,
        g_producer_compact_override.enabled ? 1 : 0,
        producer_compact_target_mode_name(),
        g_producer_compact_override.target_hit,
        g_producer_compact_override.patch_pointer_swap_34 ? 1 : 0,
        g_producer_compact_override.patch_pointer_family_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_head_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_head ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.class_head_value),
        g_producer_compact_override.patch_class_plus2_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_plus2 ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.class_plus2_value),
        g_producer_compact_override.patch_class_plus3_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_plus3 ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.class_plus3_value),
        g_producer_compact_override.patch_class_plus4_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_plus4 ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.class_plus4_value),
        g_producer_compact_override.patch_class_plus5_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_plus5 ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.class_plus5_value),
        g_producer_compact_override.patch_class_plus6 ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.class_plus6_value),
        g_producer_compact_override.trace_target_family_steps ? 1 : 0,
        g_producer_compact_override.trace_bridge_to_first_producer ? 1 : 0,
        g_producer_compact_override.stop_after_bridge_candidate_birth ? 1 : 0,
        g_producer_compact_override.bridge_trace_steps,
        g_producer_compact_override.require_bridge_bucket ? 1 : 0,
        static_cast<unsigned long>(g_producer_compact_override.bridge_required_minus1),
        static_cast<unsigned long>(g_producer_compact_override.bridge_required_plus3),
        g_producer_compact_override.arm_render_from_startup ? 1 : 0,
        g_producer_compact_override.follow_on_render ? 1 : 0,
        g_producer_compact_override.label.empty() ? "<none>" : g_producer_compact_override.label.c_str());
}

void seed_guard_message_watch()
{
    const char* const kCustomMapGuard = "A mod is required for custom maps.";
    g_watch_materials.insert(kCustomMapGuard);
    log_line("guard_message_watch_seeded text=%s", kCustomMapGuard);
}

void seed_direct_custom_map_guard_touch()
{
    if (!g_main_base)
        return;

    const uintptr_t guard_addr = g_main_base + kCustomMapGuardStringRva;
    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(guard_addr), &mbi, sizeof(mbi)))
    {
        log_line("direct_guard_touch_seed_failed addr=0x%08lX gle=%lu",
            static_cast<unsigned long>(guard_addr),
            GetLastError());
        return;
    }

    if (!region_is_readable(mbi))
    {
        log_line("direct_guard_touch_seed_unreadable addr=0x%08lX protect=0x%08lX",
            static_cast<unsigned long>(guard_addr),
            static_cast<unsigned long>(mbi.Protect));
        return;
    }

    const std::string live_text = safe_read_ascii_string(guard_addr);
    add_touch_target_locked("material", "A mod is required for custom maps.", guard_addr, mbi.Protect);
    log_line("direct_guard_touch_seeded addr=0x%08lX page=0x%08lX text=%s",
        static_cast<unsigned long>(guard_addr),
        static_cast<unsigned long>(guard_addr & ~(static_cast<uintptr_t>(g_system_info.dwPageSize) - 1u)),
        live_text.c_str());
}

int scan_custom_map_guard_copies_locked()
{
    const std::string needle = "A mod is required for custom maps.";
    const uintptr_t original_addr = g_main_base ? (g_main_base + kCustomMapGuardStringRva) : 0;
    int added = 0;
    uintptr_t addr = 0;
    MEMORY_BASIC_INFORMATION mbi {};
    while (VirtualQuery(reinterpret_cast<void*>(addr), &mbi, sizeof(mbi)) == sizeof(mbi))
    {
        if (region_is_readable(mbi)
            && (mbi.Type == MEM_PRIVATE || mbi.Type == MEM_MAPPED)
            && mbi.RegionSize >= needle.size())
        {
            std::vector<unsigned char> buffer(mbi.RegionSize);
            if (safe_copy_memory(reinterpret_cast<uintptr_t>(mbi.BaseAddress), buffer.data(), buffer.size()))
            {
                const auto begin = buffer.begin();
                const auto end = buffer.end();
                const auto nbegin = reinterpret_cast<const unsigned char*>(needle.data());
                const auto nend = nbegin + needle.size();
                auto it = begin;
                while ((it = std::search(it, end, nbegin, nend)) != end)
                {
                    const uintptr_t found_addr = reinterpret_cast<uintptr_t>(mbi.BaseAddress) + static_cast<size_t>(it - begin);
                    if (found_addr != original_addr && !is_probe_module_addr(found_addr))
                    {
                        const size_t before = g_touch_targets.size();
                        add_touch_target_locked("custom_map_guard_copy", needle, found_addr, mbi.Protect);
                        if (g_touch_targets.size() != before)
                            ++added;
                    }
                    ++it;
                }
            }
        }
        const uintptr_t next = reinterpret_cast<uintptr_t>(mbi.BaseAddress) + mbi.RegionSize;
        if (next <= addr)
            break;
        addr = next;
    }
    return added;
}

void load_watchlist()
{
    const std::string watch_path = module_relative_path(L"..\\..\\..\\active_probe_watchlist.txt");
    FILE* file = std::fopen(watch_path.c_str(), "rb");
    if (!file)
    {
        log_line("watchlist_missing path=%s", watch_path.c_str());
        return;
    }

    char line[1024] {};
    unsigned count = 0;
    while (std::fgets(line, sizeof(line), file))
    {
        std::string text = line;
        while (!text.empty() && (text.back() == '\r' || text.back() == '\n'))
            text.pop_back();
        if (text.empty())
            continue;

        ++count;
        log_line("watch_entry %s", text.c_str());

        const size_t eq = text.find('=');
        if (eq == std::string::npos)
            continue;

        std::string key = to_lower_copy(text.substr(0, eq));
        std::string value = to_lower_copy(text.substr(eq + 1));
        if (key == "image")
            g_watch_images.insert(value);
        else if (key == "file")
            g_watch_files.insert(value);
        else if (key == "material")
            g_watch_materials.insert(value);
        else if (key == "techset")
            g_watch_techsets.insert(value);
        else if (key == "xanim")
            g_watch_xanims.insert(value);
        else if (key == "xmodel")
            g_watch_xmodels.insert(value);
        else if (key == "xanim_alias")
        {
            const size_t arrow = value.find("->");
            if (arrow != std::string::npos)
            {
                const std::string from = to_lower_copy(value.substr(0, arrow));
                const std::string to = to_lower_copy(value.substr(arrow + 2));
                if (!from.empty() && !to.empty())
                {
                    g_xanim_aliases[from] = to;
                    log_line("xanim_alias from=%s to=%s", from.c_str(), to.c_str());
                }
            }
        }
    }
    std::fclose(file);
    log_line("watchlist_loaded path=%s entries=%u", watch_path.c_str(), count);

    g_watch_images.insert("fxt_debris_clump_dirt");
    g_watch_images.insert("fxt_light_glow_square");
    g_watch_images.insert("fxt_light_phosphorous");

    if (g_probe_mode == ProbeMode::XanimFocus)
    {
        seed_default_xanim_watchlist();
        seed_default_xanim_file_watchlist();
        log_line("xanim_focus_seeded_file_watches count=%u", static_cast<unsigned>(g_watch_files.size()));
    }
}

void load_xanim_expectations()
{
    g_xanim_expected_assets.clear();
    g_xanim_expectations.clear();

    const std::string expectation_path = module_relative_path(L"xanim_runtime_expectations.txt");
    FILE* file = std::fopen(expectation_path.c_str(), "rb");
    if (!file)
    {
        log_line("xanim_expectations_missing path=%s", expectation_path.c_str());
        return;
    }

    char line[1024] {};
    unsigned count = 0;
    while (std::fgets(line, sizeof(line), file))
    {
        std::string text = line;
        while (!text.empty() && (text.back() == '\r' || text.back() == '\n'))
            text.pop_back();
        if (text.empty())
            continue;
        std::vector<std::string> parts;
        size_t start = 0;
        while (start <= text.size())
        {
            const size_t sep = text.find('|', start);
            if (sep == std::string::npos)
            {
                parts.push_back(text.substr(start));
                break;
            }
            parts.push_back(text.substr(start, sep - start));
            start = sep + 1;
        }
        if (parts.empty())
            continue;

        if (parts[0] == "asset")
        {
            if (parts.size() >= 21)
            {
                XanimExpectedAssetVariant asset;
                asset.asset_name = to_lower_copy(parts[1]);
                asset.variant_name = parts[2];
                asset.numframes = static_cast<uint16_t>(std::strtoul(parts[3].c_str(), nullptr, 0));
                asset.data_byte_count = static_cast<uint16_t>(std::strtoul(parts[4].c_str(), nullptr, 0));
                asset.data_short_count = static_cast<uint16_t>(std::strtoul(parts[5].c_str(), nullptr, 0));
                asset.data_int_count = static_cast<uint16_t>(std::strtoul(parts[6].c_str(), nullptr, 0));
                asset.notify_count = static_cast<uint8_t>(std::strtoul(parts[7].c_str(), nullptr, 0));
                asset.total_bones = static_cast<uint8_t>(std::strtoul(parts[8].c_str(), nullptr, 0));
                asset.frequency = static_cast<float>(std::atof(parts[9].c_str()));
                asset.asset_type = static_cast<uint8_t>(std::strtoul(parts[10].c_str(), nullptr, 0));
                asset.is_default = static_cast<uint8_t>(std::strtoul(parts[11].c_str(), nullptr, 0));
                asset.b_loop = static_cast<uint8_t>(std::strtoul(parts[12].c_str(), nullptr, 0));
                asset.b_delta = static_cast<uint8_t>(std::strtoul(parts[13].c_str(), nullptr, 0));
                asset.b_delta3d = static_cast<uint8_t>(std::strtoul(parts[14].c_str(), nullptr, 0));
                asset.names_ptr_present = static_cast<uint8_t>(std::strtoul(parts[15].c_str(), nullptr, 0));
                asset.data_byte_ptr_present = static_cast<uint8_t>(std::strtoul(parts[16].c_str(), nullptr, 0));
                asset.data_short_ptr_present = static_cast<uint8_t>(std::strtoul(parts[17].c_str(), nullptr, 0));
                asset.data_int_ptr_present = static_cast<uint8_t>(std::strtoul(parts[18].c_str(), nullptr, 0));
                asset.notify_ptr_present = static_cast<uint8_t>(std::strtoul(parts[19].c_str(), nullptr, 0));
                asset.delta_part_ptr_present = static_cast<uint8_t>(std::strtoul(parts[20].c_str(), nullptr, 0));
                if (!asset.asset_name.empty() && !asset.variant_name.empty())
                {
                    g_xanim_expected_assets.push_back(std::move(asset));
                    ++count;
                }
            }
            else if (parts.size() >= 8)
            {
                XanimExpectedAssetVariant asset;
                asset.asset_name = to_lower_copy(parts[1]);
                asset.variant_name = "legacy";
                asset.numframes = static_cast<uint16_t>(std::strtoul(parts[2].c_str(), nullptr, 0));
                asset.data_byte_count = static_cast<uint16_t>(std::strtoul(parts[3].c_str(), nullptr, 0));
                asset.data_short_count = static_cast<uint16_t>(std::strtoul(parts[4].c_str(), nullptr, 0));
                asset.data_int_count = static_cast<uint16_t>(std::strtoul(parts[5].c_str(), nullptr, 0));
                asset.notify_count = static_cast<uint8_t>(std::strtoul(parts[6].c_str(), nullptr, 0));
                asset.total_bones = static_cast<uint8_t>(std::strtoul(parts[7].c_str(), nullptr, 0));
                if (!asset.asset_name.empty())
                {
                    g_xanim_expected_assets.push_back(std::move(asset));
                    ++count;
                }
            }
            continue;
        }

        if (parts[0] != "section" || parts.size() < 7)
            continue;

        XanimExpectationSection section;
        section.asset_name = to_lower_copy(parts[1]);
        section.section_name = parts[2];
        section.size = static_cast<size_t>(std::strtoul(parts[3].c_str(), nullptr, 0));
        section.hash = static_cast<uint32_t>(std::strtoul(parts[4].c_str(), nullptr, 0));
        section.prefix_offset = static_cast<size_t>(std::strtoul(parts[5].c_str(), nullptr, 0));
        section.prefix = parse_hex_bytes(parts[6]);
        if (parts.size() >= 8)
            section.relative_offset = static_cast<size_t>(std::strtoul(parts[7].c_str(), nullptr, 0));
        if (section.asset_name.empty() || section.section_name.empty() || section.size == 0 || section.hash == 0 || section.prefix.empty())
            continue;
        g_xanim_expectations.push_back(std::move(section));
        ++count;
    }
    std::fclose(file);
    log_line("xanim_expectations_loaded path=%s entries=%u assets=%u sections=%u",
        expectation_path.c_str(),
        count,
        static_cast<unsigned>(g_xanim_expected_assets.size()),
        static_cast<unsigned>(g_xanim_expectations.size()));
}

bool patch_imports_in_module(HMODULE module, const char* target_name, void* replacement, void** original_out)
{
    if (!module)
        return false;

    __try
    {
        auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return false;
        auto* nt = reinterpret_cast<IMAGE_NT_HEADERS*>(reinterpret_cast<unsigned char*>(module) + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE)
            return false;

        const DWORD image_size = nt->OptionalHeader.SizeOfImage;
        const IMAGE_DATA_DIRECTORY& dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
        if (!dir.VirtualAddress || !dir.Size)
            return false;
        if (dir.VirtualAddress >= image_size || dir.VirtualAddress + dir.Size > image_size)
            return false;

        bool touched = false;
        auto* imports = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(reinterpret_cast<unsigned char*>(module) + dir.VirtualAddress);
        const size_t max_desc = dir.Size / sizeof(IMAGE_IMPORT_DESCRIPTOR);
        for (size_t desc_index = 0; desc_index < max_desc && imports[desc_index].Name; ++desc_index)
        {
            auto& import_desc = imports[desc_index];
            if (import_desc.FirstThunk >= image_size)
                continue;
            if (import_desc.OriginalFirstThunk && import_desc.OriginalFirstThunk >= image_size)
                continue;

            auto* orig = reinterpret_cast<IMAGE_THUNK_DATA*>(reinterpret_cast<unsigned char*>(module) + (import_desc.OriginalFirstThunk ? import_desc.OriginalFirstThunk : import_desc.FirstThunk));
            auto* thunk = reinterpret_cast<IMAGE_THUNK_DATA*>(reinterpret_cast<unsigned char*>(module) + import_desc.FirstThunk);

            for (size_t thunk_index = 0; thunk_index < 16384 && orig[thunk_index].u1.AddressOfData; ++thunk_index)
            {
                auto& orig_thunk = orig[thunk_index];
                auto& iat_thunk = thunk[thunk_index];
                if (IMAGE_SNAP_BY_ORDINAL(orig_thunk.u1.Ordinal))
                    continue;
                if (orig_thunk.u1.AddressOfData >= image_size)
                    continue;

                auto* by_name = reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(reinterpret_cast<unsigned char*>(module) + orig_thunk.u1.AddressOfData);
                if (std::strcmp(reinterpret_cast<const char*>(by_name->Name), target_name) != 0)
                    continue;

                DWORD old = 0;
                if (!VirtualProtect(&iat_thunk.u1.Function, sizeof(void*), PAGE_READWRITE, &old))
                    continue;
                if (original_out && !*original_out)
                    *original_out = reinterpret_cast<void*>(iat_thunk.u1.Function);
                iat_thunk.u1.Function = reinterpret_cast<ULONG_PTR>(replacement);
                VirtualProtect(&iat_thunk.u1.Function, sizeof(void*), old, &old);
                FlushInstructionCache(GetCurrentProcess(), &iat_thunk.u1.Function, sizeof(void*));
                touched = true;
            }
        }
        return touched;
    }
    __except (EXCEPTION_EXECUTE_HANDLER)
    {
        return false;
    }
}

void install_file_hooks()
{
    int create_w_count = 0;
    int create_a_count = 0;
    int read_count = 0;
    int close_count = 0;

    for (const auto& module : g_modules)
    {
        if (module.base == g_self)
            continue;
        if (module.name == "ntdll.dll" || module.name == "kernel32.dll" || module.name == "kernelbase.dll")
            continue;
        create_w_count += patch_imports_in_module(module.base, "CreateFileW", reinterpret_cast<void*>(&hook_create_file_w), reinterpret_cast<void**>(&g_real_create_file_w)) ? 1 : 0;
        create_a_count += patch_imports_in_module(module.base, "CreateFileA", reinterpret_cast<void*>(&hook_create_file_a), reinterpret_cast<void**>(&g_real_create_file_a)) ? 1 : 0;
        read_count += patch_imports_in_module(module.base, "ReadFile", reinterpret_cast<void*>(&hook_read_file), reinterpret_cast<void**>(&g_real_read_file)) ? 1 : 0;
        close_count += patch_imports_in_module(module.base, "CloseHandle", reinterpret_cast<void*>(&hook_close_handle), reinterpret_cast<void**>(&g_real_close_handle)) ? 1 : 0;
    }

    log_line("file_hook_install complete createfilew_modules=%d createfilea_modules=%d readfile_modules=%d closehandle_modules=%d realW=0x%08lX realA=0x%08lX realRead=0x%08lX realClose=0x%08lX",
        create_w_count,
        create_a_count,
        read_count,
        close_count,
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_create_file_w)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_create_file_a)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_read_file)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_real_close_handle)));
}

std::vector<std::pair<std::string, std::string>> build_touch_needles()
{
    std::vector<std::pair<std::string, std::string>> needles;
    needles.reserve(g_watch_images.size() * 2 + g_watch_materials.size() + g_watch_techsets.size() + g_watch_xanims.size() + g_watch_xmodels.size());

    for (const auto& image : g_watch_images)
    {
        needles.emplace_back("image", image);
        if (!image.empty() && image.front() != ',')
            needles.emplace_back("image", "," + image);
    }
    for (const auto& material : g_watch_materials)
        needles.emplace_back("material", material);
    for (const auto& techset : g_watch_techsets)
        needles.emplace_back("techset", techset);
    for (const auto& xanim : g_watch_xanims)
        needles.emplace_back("xanim", xanim);
    for (const auto& xmodel : g_watch_xmodels)
        needles.emplace_back("xmodel", xmodel);

    if (g_probe_mode == ProbeMode::RenderOpacityFocus)
    {
        std::vector<std::pair<std::string, std::string>> filtered;
        filtered.reserve(needles.size());
        for (const auto& needle : needles)
        {
            if (is_opacity_focus_target(needle.first, needle.second))
                filtered.push_back(needle);
        }
        return filtered;
    }
    if (g_probe_mode == ProbeMode::XanimFocus)
    {
        std::vector<std::pair<std::string, std::string>> filtered;
        filtered.reserve(needles.size());
        for (const auto& needle : needles)
        {
            if (is_xanim_focus_target(needle.first, needle.second))
                filtered.push_back(needle);
        }
        return filtered;
    }

    return needles;
}

const char* selector_policy_slot_label(int slot)
{
    switch (slot)
    {
    case 3:
        return "selector_root_plus3";
    case 4:
        return "selector_root_plus4";
    case 5:
        return "selector_root_plus5";
    default:
        return "selector_root_slot";
    }
}

const char* guard_access_kind(unsigned long access_type)
{
    switch (access_type)
    {
    case 0:
        return "read";
    case 1:
        return "write";
    case 8:
        return "execute";
    default:
        return "unknown";
    }
}

const int kEntryWrapperTrackedSlots[3] = {-3, -1, 3};

int entry_wrapper_slot_index(int slot)
{
    for (int i = 0; i < 3; ++i)
    {
        if (kEntryWrapperTrackedSlots[i] == slot)
            return i;
    }
    return -1;
}

const char* entry_wrapper_slot_label(int slot)
{
    switch (slot)
    {
    case -3:
        return "wrapper_minus3";
    case -1:
        return "wrapper_minus1";
    case 3:
        return "wrapper_plus3";
    default:
        return "wrapper_slot";
    }
}

bool capture_entry_wrapper_values(uintptr_t wrapper_base, uint32_t* minus3, uint32_t* minus1, uint32_t* plus3)
{
    if (!wrapper_base || !minus3 || !minus1 || !plus3)
        return false;

    return safe_copy_memory(wrapper_base + static_cast<intptr_t>(-3 * static_cast<int>(sizeof(uint32_t))), minus3, sizeof(*minus3)) &&
        safe_copy_memory(wrapper_base + static_cast<intptr_t>(-1 * static_cast<int>(sizeof(uint32_t))), minus1, sizeof(*minus1)) &&
        safe_copy_memory(wrapper_base + static_cast<intptr_t>(3 * static_cast<int>(sizeof(uint32_t))), plus3, sizeof(*plus3));
}

void log_entry_wrapper_snapshot(
    const char* reason,
    unsigned long long trace_id,
    uintptr_t eip,
    uintptr_t wrapper_base,
    uint32_t minus3,
    uint32_t minus1,
    uint32_t plus3,
    int step = -1)
{
    log_line(
        "entry_wrapper_snapshot reason=%s trace=%llu step=%d eip=0x%08lX base=0x%08lX minus3=0x%08lX minus1=0x%08lX plus3=0x%08lX",
        reason ? reason : "unknown",
        trace_id,
        step,
        static_cast<unsigned long>(eip),
        static_cast<unsigned long>(wrapper_base),
        static_cast<unsigned long>(minus3),
        static_cast<unsigned long>(minus1),
        static_cast<unsigned long>(plus3));
}

const char* producer_class_field_label(size_t index)
{
    switch (index)
    {
    case 0:
        return "class_head";
    case 1:
        return "class_plus_2";
    case 2:
        return "class_plus_3";
    case 3:
        return "class_plus_4";
    case 4:
        return "class_plus_5";
    case 5:
        return "class_plus_6";
    default:
        return "class_field";
    }
}

bool capture_u32_slots(uintptr_t base, size_t count, uint32_t* values)
{
    if (!base || !values || count == 0)
        return false;
    for (size_t i = 0; i < count; ++i)
    {
        if (!safe_copy_memory(base + (i * sizeof(uint32_t)), &values[i], sizeof(uint32_t)))
            return false;
    }
    return true;
}

bool capture_producer_class_values(uintptr_t class_ptr, uint32_t* class_head, uint32_t* class_slot2, uint32_t* class_slot3, uint32_t* class_slot4, uint32_t* class_slot5, uint32_t* class_slot6)
{
    if (!class_ptr || !class_head || !class_slot2 || !class_slot3 || !class_slot4 || !class_slot5 || !class_slot6)
        return false;

    return safe_copy_memory(class_ptr, class_head, sizeof(*class_head)) &&
        safe_copy_memory(class_ptr + (2 * sizeof(uint32_t)), class_slot2, sizeof(*class_slot2)) &&
        safe_copy_memory(class_ptr + (3 * sizeof(uint32_t)), class_slot3, sizeof(*class_slot3)) &&
        safe_copy_memory(class_ptr + (4 * sizeof(uint32_t)), class_slot4, sizeof(*class_slot4)) &&
        safe_copy_memory(class_ptr + (5 * sizeof(uint32_t)), class_slot5, sizeof(*class_slot5)) &&
        safe_copy_memory(class_ptr + (6 * sizeof(uint32_t)), class_slot6, sizeof(*class_slot6));
}

void log_producer_class_snapshot(
    const char* reason,
    unsigned long long trace_id,
    uintptr_t eip,
    uintptr_t class_ptr,
    uint32_t class_head,
    uint32_t class_slot2,
    uint32_t class_slot3,
    uint32_t class_slot4,
    uint32_t class_slot5,
    uint32_t class_slot6,
    int step)
{
    log_line(
        "producer_class_snapshot reason=%s trace=%llu step=%d eip=0x%08lX class=0x%08lX class_head=0x%08lX class_plus2=0x%08lX class_plus3=0x%08lX class_plus4=0x%08lX class_plus5=0x%08lX class_plus6=0x%08lX",
        reason ? reason : "unknown",
        trace_id,
        step,
        static_cast<unsigned long>(eip),
        static_cast<unsigned long>(class_ptr),
        static_cast<unsigned long>(class_head),
        static_cast<unsigned long>(class_slot2),
        static_cast<unsigned long>(class_slot3),
        static_cast<unsigned long>(class_slot4),
        static_cast<unsigned long>(class_slot5),
        static_cast<unsigned long>(class_slot6));
}

void log_seed_normalization_core(
    const char* reason,
    unsigned long long trace_id,
    uintptr_t eip,
    uintptr_t base,
    const uint32_t* slots)
{
    if (!slots)
        return;
    log_line(
        "seed_to_first_producer_core reason=%s trace=%llu eip=0x%08lX base=0x%08lX slot0=0x%08lX slot1=0x%08lX slot2=0x%08lX slot3=0x%08lX slot4=0x%08lX slot5=0x%08lX slot6=0x%08lX",
        reason ? reason : "unknown",
        trace_id,
        static_cast<unsigned long>(eip),
        static_cast<unsigned long>(base),
        static_cast<unsigned long>(slots[0]),
        static_cast<unsigned long>(slots[1]),
        static_cast<unsigned long>(slots[2]),
        static_cast<unsigned long>(slots[3]),
        static_cast<unsigned long>(slots[4]),
        static_cast<unsigned long>(slots[5]),
        static_cast<unsigned long>(slots[6]));
}

void prime_producer_class_trace_state_locked(StepTraceState& state, unsigned long long trace_id, const CONTEXT& ctx, uintptr_t class_ptr)
{
    state.producer_class_ptr = class_ptr;
    state.producer_arm_tick = GetTickCount();
    state.producer_initialized = false;
    state.producer_any_change = false;
    std::fill(std::begin(state.producer_initial_values), std::end(state.producer_initial_values), 0);
    std::fill(std::begin(state.producer_last_values), std::end(state.producer_last_values), 0);
    std::fill(std::begin(state.producer_field_changed), std::end(state.producer_field_changed), false);

    if (!class_ptr)
        return;

    uint32_t class_head = 0;
    uint32_t class_slot2 = 0;
    uint32_t class_slot3 = 0;
    uint32_t class_slot4 = 0;
    uint32_t class_slot5 = 0;
    uint32_t class_slot6 = 0;
    if (!capture_producer_class_values(class_ptr, &class_head, &class_slot2, &class_slot3, &class_slot4, &class_slot5, &class_slot6))
        return;

    state.producer_initialized = true;
    state.producer_initial_values[0] = class_head;
    state.producer_initial_values[1] = class_slot2;
    state.producer_initial_values[2] = class_slot3;
    state.producer_initial_values[3] = class_slot4;
    state.producer_initial_values[4] = class_slot5;
    state.producer_initial_values[5] = class_slot6;
    std::copy(std::begin(state.producer_initial_values), std::end(state.producer_initial_values), std::begin(state.producer_last_values));

    log_producer_class_snapshot("trace_arm", trace_id, ctx.Eip, class_ptr, class_head, class_slot2, class_slot3, class_slot4, class_slot5, class_slot6);
    log_line(
        "producer_class_trace_armed trace=%llu base=0x%08lX class_head=0x%08lX class_plus2=0x%08lX class_plus3=0x%08lX class_plus4=0x%08lX class_plus5=0x%08lX class_plus6=0x%08lX",
        trace_id,
        static_cast<unsigned long>(class_ptr),
        static_cast<unsigned long>(class_head),
        static_cast<unsigned long>(class_slot2),
        static_cast<unsigned long>(class_slot3),
        static_cast<unsigned long>(class_slot4),
        static_cast<unsigned long>(class_slot5),
        static_cast<unsigned long>(class_slot6));
}

void trace_producer_class_step_locked(StepTraceState& state, const CONTEXT& ctx, int step_number)
{
    if (!state.producer_initialized || !state.producer_class_ptr)
        return;

    uint32_t values[6] {};
    if (!capture_producer_class_values(state.producer_class_ptr, &values[0], &values[1], &values[2], &values[3], &values[4], &values[5]))
        return;

    log_producer_class_snapshot("step", state.trace_id, ctx.Eip, state.producer_class_ptr, values[0], values[1], values[2], values[3], values[4], values[5], step_number);

    bool logged_change = false;
    for (size_t i = 0; i < 6; ++i)
    {
        if (values[i] == state.producer_last_values[i])
            continue;

        const uintptr_t slot_addr = state.producer_class_ptr + ((i == 0 ? 0 : (static_cast<uintptr_t>(i + 1) * sizeof(uint32_t))));
        log_line(
            "producer_class_field_change trace=%llu step=%d eip=0x%08lX class=0x%08lX field=%s addr=0x%08lX old=0x%08lX new=0x%08lX delta_from_arm_ms=%lu first_change=%d",
            state.trace_id,
            step_number,
            static_cast<unsigned long>(ctx.Eip),
            static_cast<unsigned long>(state.producer_class_ptr),
            producer_class_field_label(i),
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(state.producer_last_values[i]),
            static_cast<unsigned long>(values[i]),
            static_cast<unsigned long>(GetTickCount() - state.producer_arm_tick),
            state.producer_field_changed[i] ? 0 : 1);
        state.producer_last_values[i] = values[i];
        if (!state.producer_field_changed[i])
        {
            state.producer_field_changed[i] = true;
            state.producer_any_change = true;
        }
        logged_change = true;
    }

    if (logged_change)
    {
        const CallerSelection sel = capture_relevant_caller();
        log_backtrace_selection(0, sel, "producer_class_change", "producer_class_trace");
    }
}

bool maybe_prime_bridge_producer_candidate_locked(StepTraceState& state, const CONTEXT& ctx, int step_number)
{
    if (state.producer_initialized)
        return false;

    struct CandidateReg
    {
        const char* name;
        uintptr_t value;
    };

    const CandidateReg candidates[] = {
        {"ecx", ctx.Ecx},
        {"eax", ctx.Eax},
        {"esi", ctx.Esi},
        {"edi", ctx.Edi},
    };

    for (const auto& candidate : candidates)
    {
        if (!candidate.value)
            continue;

        uint32_t class_head = 0;
        uint32_t class_slot2 = 0;
        uint32_t class_slot3 = 0;
        uint32_t class_slot4 = 0;
        uint32_t class_slot5 = 0;
        uint32_t class_slot6 = 0;
        if (!capture_producer_class_values(candidate.value, &class_head, &class_slot2, &class_slot3, &class_slot4, &class_slot5, &class_slot6))
            continue;
        if (class_slot5 == 0 && class_slot6 == 0)
            continue;

        prime_producer_class_trace_state_locked(state, state.trace_id, ctx, candidate.value);
        log_line(
            "bridge_first_producer_candidate_birth trace=%llu step=%d eip=0x%08lX reg=%s class=0x%08lX class_head=0x%08lX class_plus2=0x%08lX class_plus3=0x%08lX class_plus4=0x%08lX class_plus5=0x%08lX class_plus6=0x%08lX",
            state.trace_id,
            step_number,
            static_cast<unsigned long>(ctx.Eip),
            candidate.name,
            static_cast<unsigned long>(candidate.value),
            static_cast<unsigned long>(class_head),
            static_cast<unsigned long>(class_slot2),
            static_cast<unsigned long>(class_slot3),
            static_cast<unsigned long>(class_slot4),
            static_cast<unsigned long>(class_slot5),
            static_cast<unsigned long>(class_slot6));
        const CallerSelection sel = capture_relevant_caller();
        log_backtrace_selection(0, sel, "bridge_first_producer_candidate", "bridge_to_first_producer_flow");

        g_seed_normalization = SeedNormalizationState {};
        g_seed_normalization.active = true;
        g_seed_normalization.trace_id = state.trace_id;
        g_seed_normalization.birth_tick = GetTickCount();
        g_seed_normalization.seed_ptr = candidate.value;
        g_seed_normalization.birth_eip = ctx.Eip;
        g_seed_normalization.birth_reg = candidate.name;
        capture_u32_slots(candidate.value, 7, g_seed_normalization.seed_slots);
        log_seed_normalization_core("seed_birth", state.trace_id, ctx.Eip, candidate.value, g_seed_normalization.seed_slots);
        log_consumer_anchor_snapshot("seed_to_first_producer_seed_birth", "seed_birth", candidate.value, 0, 8);

        if (g_producer_compact_override.stop_after_bridge_candidate_birth)
            state.force_complete = true;
        return true;
    }

    return false;
}

void prime_entry_wrapper_trace_state_locked(StepTraceState& state, const CONTEXT& ctx)
{
    state.wrapper_base = ctx.Edi;
    state.wrapper_arm_tick = GetTickCount();
    state.wrapper_initialized = false;
    state.wrapper_prepopulated = false;
    state.wrapper_any_change = false;
    std::fill(std::begin(state.wrapper_initial_values), std::end(state.wrapper_initial_values), 0);
    std::fill(std::begin(state.wrapper_last_values), std::end(state.wrapper_last_values), 0);
    std::fill(std::begin(state.wrapper_slot_changed), std::end(state.wrapper_slot_changed), false);

    if (!state.wrapper_base)
        return;

    uint32_t minus3 = 0;
    uint32_t minus1 = 0;
    uint32_t plus3 = 0;
    if (!capture_entry_wrapper_values(state.wrapper_base, &minus3, &minus1, &plus3))
        return;

    state.wrapper_initialized = true;
    state.wrapper_initial_values[0] = minus3;
    state.wrapper_initial_values[1] = minus1;
    state.wrapper_initial_values[2] = plus3;
    state.wrapper_last_values[0] = minus3;
    state.wrapper_last_values[1] = minus1;
    state.wrapper_last_values[2] = plus3;
    state.wrapper_prepopulated = (minus3 != 0 || minus1 != 0 || plus3 != 0);

    log_entry_wrapper_snapshot("entry_arm", state.trace_id, ctx.Eip, state.wrapper_base, minus3, minus1, plus3);
    log_line(
        "entry_wrapper_trace_armed trace=%llu base=0x%08lX minus3=0x%08lX minus1=0x%08lX plus3=0x%08lX prepopulated=%d",
        state.trace_id,
        static_cast<unsigned long>(state.wrapper_base),
        static_cast<unsigned long>(minus3),
        static_cast<unsigned long>(minus1),
        static_cast<unsigned long>(plus3),
        state.wrapper_prepopulated ? 1 : 0);

    if (state.wrapper_prepopulated)
    {
        log_line(
            "entry_wrapper_prepopulated trace=%llu base=0x%08lX minus3=0x%08lX minus1=0x%08lX plus3=0x%08lX",
            state.trace_id,
            static_cast<unsigned long>(state.wrapper_base),
            static_cast<unsigned long>(minus3),
            static_cast<unsigned long>(minus1),
            static_cast<unsigned long>(plus3));
        const CallerSelection sel = capture_relevant_caller();
        log_backtrace_selection(0, sel, "entry_wrapper_prepopulated", "asset_lookup_entry");
    }
}

void maybe_apply_entry_wrapper_override(unsigned long long trace_id, uintptr_t eip, uintptr_t wrapper_base, const std::string& point_label, unsigned hit)
{
    if (!g_entry_wrapper_override.enabled || !wrapper_base)
        return;
    if (!g_entry_wrapper_override.apply_label.empty() && point_label != g_entry_wrapper_override.apply_label)
        return;
    if (hit != g_entry_wrapper_override.target_hit)
        return;
    if (g_entry_wrapper_override_applied.exchange(true))
        return;

    const uintptr_t minus1_addr = wrapper_base + static_cast<intptr_t>(-1 * static_cast<int>(sizeof(uint32_t)));
    const uintptr_t plus3_addr = wrapper_base + static_cast<intptr_t>(3 * static_cast<int>(sizeof(uint32_t)));
    uint32_t old_minus1 = 0;
    uint32_t old_plus3 = 0;
    safe_copy_memory(minus1_addr, &old_minus1, sizeof(old_minus1));
    safe_copy_memory(plus3_addr, &old_plus3, sizeof(old_plus3));

    const uint32_t target_minus1 = g_entry_wrapper_override.use_minus1_rva
        ? static_cast<uint32_t>(rva_to_va(g_entry_wrapper_override.minus1_rva))
        : g_entry_wrapper_override.minus1_value;
    const uint32_t target_plus3 = g_entry_wrapper_override.use_plus3_rva
        ? static_cast<uint32_t>(rva_to_va(g_entry_wrapper_override.plus3_rva))
        : g_entry_wrapper_override.plus3_value;

    bool wrote_any = false;
    if (g_entry_wrapper_override.patch_minus1)
    {
        DWORD old = 0;
        VirtualProtect(reinterpret_cast<void*>(minus1_addr), sizeof(uint32_t), PAGE_READWRITE, &old);
        std::memcpy(reinterpret_cast<void*>(minus1_addr), &target_minus1, sizeof(uint32_t));
        DWORD restore = 0;
        VirtualProtect(reinterpret_cast<void*>(minus1_addr), sizeof(uint32_t), old, &restore);
        wrote_any = true;
    }
    if (g_entry_wrapper_override.patch_plus3)
    {
        DWORD old = 0;
        VirtualProtect(reinterpret_cast<void*>(plus3_addr), sizeof(uint32_t), PAGE_READWRITE, &old);
        std::memcpy(reinterpret_cast<void*>(plus3_addr), &target_plus3, sizeof(uint32_t));
        DWORD restore = 0;
        VirtualProtect(reinterpret_cast<void*>(plus3_addr), sizeof(uint32_t), old, &restore);
        wrote_any = true;
    }

    uint32_t new_minus1 = 0;
    uint32_t new_plus3 = 0;
    safe_copy_memory(minus1_addr, &new_minus1, sizeof(new_minus1));
    safe_copy_memory(plus3_addr, &new_plus3, sizeof(new_plus3));

    log_line(
        "entry_wrapper_override_apply trace=%llu eip=0x%08lX point=%s hit=%u base=0x%08lX label=%s patch_minus1=%d old_minus1=0x%08lX new_minus1=0x%08lX patch_plus3=%d old_plus3=0x%08lX new_plus3=0x%08lX wrote_any=%d",
        trace_id,
        static_cast<unsigned long>(eip),
        point_label.c_str(),
        hit,
        static_cast<unsigned long>(wrapper_base),
        g_entry_wrapper_override.label.empty() ? "<none>" : g_entry_wrapper_override.label.c_str(),
        g_entry_wrapper_override.patch_minus1 ? 1 : 0,
        static_cast<unsigned long>(old_minus1),
        static_cast<unsigned long>(new_minus1),
        g_entry_wrapper_override.patch_plus3 ? 1 : 0,
        static_cast<unsigned long>(old_plus3),
        static_cast<unsigned long>(new_plus3),
        wrote_any ? 1 : 0);

    uint32_t minus3 = 0;
    uint32_t minus1 = 0;
    uint32_t plus3 = 0;
    if (capture_entry_wrapper_values(wrapper_base, &minus3, &minus1, &plus3))
        log_entry_wrapper_snapshot("override_post_patch", trace_id, eip, wrapper_base, minus3, minus1, plus3, -1);
}

void maybe_apply_producer_compact_override(unsigned hit, unsigned long long trace_id, const std::string& path, CONTEXT& ctx, uintptr_t class_ptr, uint32_t class_head, uint32_t* class_slot2, uint32_t* class_slot3, uint32_t* class_slot4, uint32_t* class_slot5, uint32_t* class_slot6)
{
    if (!g_producer_compact_override.enabled || !class_ptr)
        return;

    uint32_t observed_slot2 = 0;
    uint32_t observed_slot3 = 0;
    uint32_t observed_slot4 = 0;
    uint32_t observed_slot5 = 0;
    uint32_t observed_slot6 = 0;
    safe_copy_memory(class_ptr + (2 * sizeof(uint32_t)), &observed_slot2, sizeof(observed_slot2));
    safe_copy_memory(class_ptr + (3 * sizeof(uint32_t)), &observed_slot3, sizeof(observed_slot3));
    safe_copy_memory(class_ptr + (4 * sizeof(uint32_t)), &observed_slot4, sizeof(observed_slot4));
    safe_copy_memory(class_ptr + (5 * sizeof(uint32_t)), &observed_slot5, sizeof(observed_slot5));
    safe_copy_memory(class_ptr + (6 * sizeof(uint32_t)), &observed_slot6, sizeof(observed_slot6));

    const bool has_patch =
        g_producer_compact_override.patch_pointer_swap_34 ||
        g_producer_compact_override.patch_pointer_family_from_initial ||
        g_producer_compact_override.patch_class_head_from_initial ||
        g_producer_compact_override.patch_class_head ||
        g_producer_compact_override.patch_class_plus2_from_initial ||
        g_producer_compact_override.patch_class_plus2 ||
        g_producer_compact_override.patch_class_plus3_from_initial ||
        g_producer_compact_override.patch_class_plus3 ||
        g_producer_compact_override.patch_class_plus4_from_initial ||
        g_producer_compact_override.patch_class_plus4 ||
        g_producer_compact_override.patch_class_plus5_from_initial ||
        g_producer_compact_override.patch_class_plus5 ||
        g_producer_compact_override.patch_class_plus6;

    unsigned distinct_index = 0;
    if (g_producer_compact_override.target_first_distinct_after_initial)
    {
        if (!g_producer_compact_override.initial_family_seen)
        {
            g_producer_compact_override.initial_family_seen = true;
            g_producer_compact_override.initial_class_ptr = class_ptr;
            g_producer_compact_override.initial_class_head = class_head;
            g_producer_compact_override.initial_class_slot2 = observed_slot2;
            g_producer_compact_override.initial_class_slot3 = observed_slot3;
            g_producer_compact_override.initial_class_slot4 = observed_slot4;
            g_producer_compact_override.initial_class_slot5 = observed_slot5;
            log_line(
                "producer_compact_override_baseline mode=%s hit=%u class=0x%08lX class_head=0x%08lX class_plus2=0x%08lX class_plus3=0x%08lX class_plus4=0x%08lX class_plus5=0x%08lX label=%s",
                producer_compact_target_mode_name(),
                hit,
                static_cast<unsigned long>(class_ptr),
                static_cast<unsigned long>(class_head),
                static_cast<unsigned long>(observed_slot2),
                static_cast<unsigned long>(observed_slot3),
                static_cast<unsigned long>(observed_slot4),
                static_cast<unsigned long>(observed_slot5),
                g_producer_compact_override.label.empty() ? "<none>" : g_producer_compact_override.label.c_str());
            return;
        }

        if (class_ptr == g_producer_compact_override.initial_class_ptr &&
            class_head == g_producer_compact_override.initial_class_head)
        {
            return;
        }

        distinct_index = 1;
    }
    else
    {
        if (hit != g_producer_compact_override.target_hit)
            return;
    }

    if (g_producer_compact_override.trace_target_family_steps &&
        !g_producer_class_trace_started.exchange(true) &&
        g_step_traces.find(GetCurrentThreadId()) == g_step_traces.end())
    {
        log_line(
            "producer_class_trace_target hit=%u target_mode=%s distinct_index=%u eip=0x%08lX class=0x%08lX class_head=0x%08lX class_plus2=0x%08lX class_plus3=0x%08lX class_plus4=0x%08lX class_plus5=0x%08lX class_plus6=0x%08lX label=%s",
            hit,
            producer_compact_target_mode_name(),
            distinct_index,
            static_cast<unsigned long>(ctx.Eip),
            static_cast<unsigned long>(class_ptr),
            static_cast<unsigned long>(class_head),
            static_cast<unsigned long>(observed_slot2),
            static_cast<unsigned long>(observed_slot3),
            static_cast<unsigned long>(observed_slot4),
            static_cast<unsigned long>(observed_slot5),
            static_cast<unsigned long>(observed_slot6),
            g_producer_compact_override.label.empty() ? "<none>" : g_producer_compact_override.label.c_str());
        begin_step_trace_locked(GetCurrentThreadId(), "producer_target_family_flow", trace_id, path, ctx.Eip, kProducerClassStepTraceInstructions);
        auto step_state_it = g_step_traces.find(GetCurrentThreadId());
        if (step_state_it != g_step_traces.end())
            prime_producer_class_trace_state_locked(step_state_it->second, trace_id, ctx, class_ptr);
        ctx.EFlags |= 0x100u;
        log_line(
            "branch_trace_request kind=producer_target_family_flow start=0x%08lX steps=%d trace=%llu path=%s",
            static_cast<unsigned long>(ctx.Eip),
            kProducerClassStepTraceInstructions,
            trace_id,
            path.c_str());
    }

    if (!has_patch)
        return;

    if (g_producer_compact_override_applied.exchange(true))
        return;

    const uintptr_t class_plus5_addr = class_ptr + (5 * sizeof(uint32_t));
    const uintptr_t class_plus6_addr = class_ptr + (6 * sizeof(uint32_t));
    const uintptr_t class_head_addr = class_ptr;
    const uintptr_t class_plus2_addr = class_ptr + (2 * sizeof(uint32_t));
    const uintptr_t class_plus3_addr = class_ptr + (3 * sizeof(uint32_t));
    const uintptr_t class_plus4_addr = class_ptr + (4 * sizeof(uint32_t));
    uint32_t old_head = class_head;
    uint32_t old_plus2 = observed_slot2;
    uint32_t old_plus3 = observed_slot3;
    uint32_t old_plus4 = observed_slot4;
    uint32_t old_plus5 = 0;
    uint32_t old_plus6 = 0;
    safe_copy_memory(class_plus5_addr, &old_plus5, sizeof(old_plus5));
    safe_copy_memory(class_plus6_addr, &old_plus6, sizeof(old_plus6));

    auto write_u32 = [](uintptr_t addr, uint32_t value) {
        DWORD old = 0;
        if (!VirtualProtect(reinterpret_cast<void*>(addr), sizeof(uint32_t), PAGE_READWRITE, &old))
            return false;
        std::memcpy(reinterpret_cast<void*>(addr), &value, sizeof(uint32_t));
        DWORD restore = 0;
        VirtualProtect(reinterpret_cast<void*>(addr), sizeof(uint32_t), old, &restore);
        return true;
    };

    bool wrote_any = false;
    const bool patch_head_from_initial = g_producer_compact_override.patch_pointer_family_from_initial || g_producer_compact_override.patch_class_head_from_initial;
    const bool patch_plus2_from_initial = g_producer_compact_override.patch_pointer_family_from_initial || g_producer_compact_override.patch_class_plus2_from_initial;
    const bool patch_plus3_from_initial = g_producer_compact_override.patch_pointer_family_from_initial || g_producer_compact_override.patch_class_plus3_from_initial;
    const bool patch_plus4_from_initial = g_producer_compact_override.patch_pointer_family_from_initial || g_producer_compact_override.patch_class_plus4_from_initial;
    const bool patch_plus5_from_initial = g_producer_compact_override.patch_class_plus5_from_initial;

    if (patch_head_from_initial)
        wrote_any = write_u32(class_head_addr, g_producer_compact_override.initial_class_head) || wrote_any;
    if (patch_plus2_from_initial)
        wrote_any = write_u32(class_plus2_addr, g_producer_compact_override.initial_class_slot2) || wrote_any;
    if (patch_plus3_from_initial)
        wrote_any = write_u32(class_plus3_addr, g_producer_compact_override.initial_class_slot3) || wrote_any;
    if (patch_plus4_from_initial)
        wrote_any = write_u32(class_plus4_addr, g_producer_compact_override.initial_class_slot4) || wrote_any;
    if (patch_plus5_from_initial)
        wrote_any = write_u32(class_plus5_addr, g_producer_compact_override.initial_class_slot5) || wrote_any;

    if (g_producer_compact_override.patch_class_head)
        wrote_any = write_u32(class_head_addr, g_producer_compact_override.class_head_value) || wrote_any;
    if (g_producer_compact_override.patch_class_plus2)
        wrote_any = write_u32(class_plus2_addr, g_producer_compact_override.class_plus2_value) || wrote_any;
    if (g_producer_compact_override.patch_class_plus3)
        wrote_any = write_u32(class_plus3_addr, g_producer_compact_override.class_plus3_value) || wrote_any;
    if (g_producer_compact_override.patch_class_plus4)
        wrote_any = write_u32(class_plus4_addr, g_producer_compact_override.class_plus4_value) || wrote_any;

    if (g_producer_compact_override.patch_pointer_family_from_initial)
    {
        // already applied above through the granular role flags
    }
    if (g_producer_compact_override.patch_pointer_swap_34)
    {
        wrote_any = write_u32(class_plus3_addr, old_plus4) || wrote_any;
        wrote_any = write_u32(class_plus4_addr, old_plus3) || wrote_any;
    }
    if (g_producer_compact_override.patch_class_plus5)
    {
        wrote_any = write_u32(class_plus5_addr, g_producer_compact_override.class_plus5_value) || wrote_any;
    }
    if (g_producer_compact_override.patch_class_plus6)
    {
        wrote_any = write_u32(class_plus6_addr, g_producer_compact_override.class_plus6_value) || wrote_any;
    }

    uint32_t new_head = 0;
    uint32_t new_plus2 = 0;
    uint32_t new_plus3 = 0;
    uint32_t new_plus4 = 0;
    safe_copy_memory(class_head_addr, &new_head, sizeof(new_head));
    safe_copy_memory(class_plus2_addr, &new_plus2, sizeof(new_plus2));
    safe_copy_memory(class_plus3_addr, &new_plus3, sizeof(new_plus3));
    safe_copy_memory(class_plus4_addr, &new_plus4, sizeof(new_plus4));
    uint32_t new_plus5 = 0;
    uint32_t new_plus6 = 0;
    safe_copy_memory(class_plus5_addr, &new_plus5, sizeof(new_plus5));
    safe_copy_memory(class_plus6_addr, &new_plus6, sizeof(new_plus6));
    if (class_slot2)
        *class_slot2 = new_plus2;
    if (class_slot3)
        *class_slot3 = new_plus3;
    if (class_slot4)
        *class_slot4 = new_plus4;
    if (class_slot5)
        *class_slot5 = new_plus5;
    if (class_slot6)
        *class_slot6 = new_plus6;
    class_head = new_head;

    log_line(
        "producer_compact_override_apply hit=%u target_mode=%s target_hit=%u distinct_index=%u initial_class=0x%08lX initial_class_head=0x%08lX initial_class_plus2=0x%08lX initial_class_plus3=0x%08lX initial_class_plus4=0x%08lX initial_class_plus5=0x%08lX class=0x%08lX class_head=0x%08lX label=%s patch_pointer_swap_34=%d patch_pointer_family_from_initial=%d old_class_head=0x%08lX new_class_head=0x%08lX old_class_plus2=0x%08lX new_class_plus2=0x%08lX old_class_plus3=0x%08lX new_class_plus3=0x%08lX old_class_plus4=0x%08lX new_class_plus4=0x%08lX patch_class_plus5_from_initial=%d patch_class_plus5=%d old_class_plus5=0x%08lX new_class_plus5=0x%08lX patch_class_plus6=%d old_class_plus6=0x%08lX new_class_plus6=0x%08lX wrote_any=%d",
        hit,
        producer_compact_target_mode_name(),
        g_producer_compact_override.target_hit,
        distinct_index,
        static_cast<unsigned long>(g_producer_compact_override.initial_class_ptr),
        static_cast<unsigned long>(g_producer_compact_override.initial_class_head),
        static_cast<unsigned long>(g_producer_compact_override.initial_class_slot2),
        static_cast<unsigned long>(g_producer_compact_override.initial_class_slot3),
        static_cast<unsigned long>(g_producer_compact_override.initial_class_slot4),
        static_cast<unsigned long>(g_producer_compact_override.initial_class_slot5),
        static_cast<unsigned long>(class_ptr),
        static_cast<unsigned long>(new_head),
        g_producer_compact_override.label.empty() ? "<none>" : g_producer_compact_override.label.c_str(),
        g_producer_compact_override.patch_pointer_swap_34 ? 1 : 0,
        g_producer_compact_override.patch_pointer_family_from_initial ? 1 : 0,
        static_cast<unsigned long>(old_head),
        static_cast<unsigned long>(new_head),
        static_cast<unsigned long>(old_plus2),
        static_cast<unsigned long>(new_plus2),
        static_cast<unsigned long>(old_plus3),
        static_cast<unsigned long>(new_plus3),
        static_cast<unsigned long>(old_plus4),
        static_cast<unsigned long>(new_plus4),
        g_producer_compact_override.patch_class_plus5_from_initial ? 1 : 0,
        g_producer_compact_override.patch_class_plus5 ? 1 : 0,
        static_cast<unsigned long>(old_plus5),
        static_cast<unsigned long>(new_plus5),
        g_producer_compact_override.patch_class_plus6 ? 1 : 0,
        static_cast<unsigned long>(old_plus6),
        static_cast<unsigned long>(new_plus6),
        wrote_any ? 1 : 0);
}

void maybe_arm_follow_on_render_trace_after_asset_lookup()
{
    if (g_probe_mode != ProbeMode::ProducerCompactOverrideFocus)
        return;
    if (!g_producer_compact_override.follow_on_render)
        return;
    if (g_producer_follow_on_render_armed.exchange(true))
        return;
    // Called from the breakpoint handler while g_state_mutex is already held.
    // Taking it again here deadlocks before any downstream render traces arm.

    struct FollowOnSpec
    {
        const char* label;
        DWORD rva;
        BYTE bytes[10];
        size_t size;
        int max_hits;
    };

    static const FollowOnSpec specs[] = {
        {"consumer_render_table", kConsumerRenderTableRva, {0x66, 0x83, 0x3E, 0x00, 0x75, 0x7C, 0xEB, 0x04}, 8, 4},
        {"consumer_submit_flags", kConsumerSubmitFlagsRva, {0xF7, 0x86, 0x20, 0xFF, 0xFF, 0xFF, 0x00, 0x20, 0x00, 0x00}, 10, 1},
    };

    for (const auto& spec : specs)
    {
        const uintptr_t addr = rva_to_va(spec.rva);
        if (!bytes_match(addr, spec.bytes, spec.size))
        {
            log_line("producer_follow_on_trace_skip label=%s addr=0x%08lX reason=signature_mismatch",
                spec.label,
                static_cast<unsigned long>(addr));
            continue;
        }
        arm_exec_trace_locked(spec.label, addr, 0, "producer_override_follow_on", spec.max_hits);
        log_line("producer_follow_on_trace_arm label=%s addr=0x%08lX max_hits=%d",
            spec.label,
            static_cast<unsigned long>(addr),
            spec.max_hits);
    }
}

void trace_entry_wrapper_step_locked(StepTraceState& state, const CONTEXT& ctx, int step_number)
{
    if (!state.wrapper_initialized || !state.wrapper_base)
        return;

    uint32_t values[3] {};
    if (!capture_entry_wrapper_values(state.wrapper_base, &values[0], &values[1], &values[2]))
        return;

    log_entry_wrapper_snapshot("step", state.trace_id, ctx.Eip, state.wrapper_base, values[0], values[1], values[2], step_number);

    bool logged_change = false;
    for (int i = 0; i < 3; ++i)
    {
        if (values[i] == state.wrapper_last_values[i])
            continue;

        const int slot = kEntryWrapperTrackedSlots[i];
        const uintptr_t slot_addr = state.wrapper_base + static_cast<intptr_t>(slot * static_cast<int>(sizeof(uint32_t)));
        log_line(
            "entry_wrapper_field_change trace=%llu step=%d eip=0x%08lX base=0x%08lX slot=%+d label=%s addr=0x%08lX old=0x%08lX new=0x%08lX delta_from_entry_ms=%lu first_change=%d",
            state.trace_id,
            step_number,
            static_cast<unsigned long>(ctx.Eip),
            static_cast<unsigned long>(state.wrapper_base),
            slot,
            entry_wrapper_slot_label(slot),
            static_cast<unsigned long>(slot_addr),
            static_cast<unsigned long>(state.wrapper_last_values[i]),
            static_cast<unsigned long>(values[i]),
            static_cast<unsigned long>(GetTickCount() - state.wrapper_arm_tick),
            state.wrapper_slot_changed[i] ? 0 : 1);
        state.wrapper_last_values[i] = values[i];
        if (!state.wrapper_slot_changed[i])
        {
            state.wrapper_slot_changed[i] = true;
            state.wrapper_any_change = true;
        }
        logged_change = true;
    }

    if (logged_change)
    {
        const CallerSelection sel = capture_relevant_caller();
        log_backtrace_selection(0, sel, "entry_wrapper_change", "asset_lookup_entry");
    }
}

void add_policy_field_watch_locked(const char* phase, uintptr_t selector_root, int slot)
{
    if (!selector_root)
        return;

    const uintptr_t addr = selector_root + static_cast<uintptr_t>(slot * sizeof(uint32_t));
    for (const auto& existing : g_policy_field_watches)
    {
        if (existing.addr == addr)
            return;
    }

    MEMORY_BASIC_INFORMATION mbi {};
    if (!VirtualQuery(reinterpret_cast<void*>(addr), &mbi, sizeof(mbi)))
        return;
    if (!region_is_readable(mbi))
        return;
    if ((mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
        return;

    uint32_t value = 0;
    if (!safe_copy_memory(addr, &value, sizeof(value)))
        return;

    PolicyFieldWatch watch;
    watch.label = selector_policy_slot_label(slot);
    watch.phase = phase ? phase : "unknown";
    watch.selector_root = selector_root;
    watch.slot = slot;
    watch.addr = addr;
    watch.page_base = addr & ~(static_cast<uintptr_t>(g_system_info.dwPageSize) - 1u);
    watch.original_protect = mbi.Protect & ~PAGE_GUARD;
    watch.last_value = value;
    watch.arm_tick = GetTickCount();
    g_policy_field_pages[watch.page_base].push_back(g_policy_field_watches.size());
    g_policy_field_watches.push_back(std::move(watch));

    log_line(
        "policy_write_watch_added phase=%s label=%s selector_root=0x%08lX slot=+%d addr=0x%08lX page=0x%08lX value=0x%08lX",
        phase ? phase : "unknown",
        g_policy_field_watches.back().label.c_str(),
        static_cast<unsigned long>(selector_root),
        slot,
        static_cast<unsigned long>(addr),
        static_cast<unsigned long>(g_policy_field_watches.back().page_base),
        static_cast<unsigned long>(value));
}

void arm_policy_field_pages_locked()
{
    unsigned armed_pages = 0;
    for (auto& [page_base, indices] : g_policy_field_pages)
    {
        bool any_active = false;
        DWORD protect = PAGE_READONLY;
        for (size_t index : indices)
        {
            if (index >= g_policy_field_watches.size())
                continue;
            auto& watch = g_policy_field_watches[index];
            if (!watch.active || watch.armed)
                continue;
            any_active = true;
            protect = watch.original_protect;
        }
        if (!any_active)
            continue;

        DWORD old = 0;
        if (!VirtualProtect(reinterpret_cast<void*>(page_base), g_system_info.dwPageSize, protect | PAGE_GUARD, &old))
            continue;

        for (size_t index : indices)
        {
            if (index >= g_policy_field_watches.size())
                continue;
            auto& watch = g_policy_field_watches[index];
            if (watch.active)
                watch.armed = true;
        }
        ++armed_pages;
    }

    if (armed_pages > 0)
    {
        log_line(
            "policy_write_watch_armed fields=%u pages=%u",
            static_cast<unsigned>(g_policy_field_watches.size()),
            armed_pages);
    }
}

void arm_selector_root_policy_watches_locked(const char* phase, uintptr_t selector_root)
{
    add_policy_field_watch_locked(phase, selector_root, 3);
    add_policy_field_watch_locked(phase, selector_root, 4);
    add_policy_field_watch_locked(phase, selector_root, 5);
    arm_policy_field_pages_locked();
}

void add_touch_target_locked(const std::string& label, const std::string& text, uintptr_t addr, DWORD original_protect)
{
    if (g_touch_targets.size() >= kTouchTraceMaxPages && g_touch_pages.find(addr & ~(static_cast<uintptr_t>(g_system_info.dwPageSize) - 1u)) == g_touch_pages.end())
        return;

    const uintptr_t page_base = addr & ~(static_cast<uintptr_t>(g_system_info.dwPageSize) - 1u);
    for (const auto& existing : g_touch_targets)
    {
        if (existing.addr == addr && existing.text == text && existing.label == label)
            return;
    }

    TouchTraceTarget target;
    target.label = label;
    target.text = text;
    target.addr = addr;
    target.page_base = page_base;
    target.original_protect = original_protect & ~PAGE_GUARD;
    g_touch_pages[page_base].push_back(g_touch_targets.size());
    g_touch_targets.push_back(std::move(target));
    record_observed_asset_address(label.c_str(), text.c_str(), addr, "touch_target", page_base);
}

void arm_touch_trace_pages()
{
    std::lock_guard<std::mutex> lock(g_state_mutex);
    for (auto& target : g_touch_targets)
    {
        if (target.armed)
            continue;
        DWORD old = 0;
        if (!VirtualProtect(reinterpret_cast<void*>(target.page_base), g_system_info.dwPageSize, target.original_protect | PAGE_GUARD, &old))
            continue;
        target.armed = true;
    }

    log_line("touch_trace_armed targets=%u pages=%u delay_ms=%lu",
        static_cast<unsigned>(g_touch_targets.size()),
        static_cast<unsigned>(g_touch_pages.size()),
        static_cast<unsigned long>(touch_trace_delay_ms()));
}

void scan_touch_targets()
{
    const auto needles = build_touch_needles();
    if (needles.empty())
    {
        log_line("touch_trace_scan skipped reason=no_needles");
        return;
    }

    std::unordered_set<std::string> found_keys;
    uintptr_t cursor = 0;
    unsigned regions_scanned = 0;

    while (true)
    {
        MEMORY_BASIC_INFORMATION mbi {};
        const SIZE_T q = VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi));
        if (!q)
            break;

        const uintptr_t base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
        const uintptr_t next = base + mbi.RegionSize;
        if (next <= cursor)
            break;
        cursor = next;

        if (!region_is_readable(mbi))
            continue;
        ++regions_scanned;

        std::vector<unsigned char> buffer;
        size_t offset = 0;
        while (offset < mbi.RegionSize)
        {
            const size_t remaining = static_cast<size_t>(mbi.RegionSize - offset);
            const size_t chunk = std::min(kTouchTraceChunkSize, remaining);
            buffer.resize(chunk);
            if (!safe_copy_memory(base + offset, buffer.data(), chunk))
            {
                offset += chunk;
                continue;
            }

            for (const auto& needle : needles)
            {
                const std::string key = needle.first + ":" + needle.second;
                if (found_keys.find(key) != found_keys.end())
                    continue;
                const auto it = std::search(buffer.begin(), buffer.end(), needle.second.begin(), needle.second.end());
                if (it == buffer.end())
                    continue;

                const uintptr_t found_addr = base + offset + static_cast<size_t>(std::distance(buffer.begin(), it));
                if (is_probe_module_addr(found_addr))
                    continue;
                if (needle.first == "xanim")
                {
                    const std::string alias_name = xanim_alias_for_name(needle.second);
                    if (!alias_name.empty())
                    {
                        const bool rewritten = rewrite_ascii_string_in_place(found_addr, alias_name, needle.second.size() + 1);
                        log_line("xanim_touch_seed_rewrite name=%s alias=%s addr=0x%08lX rewritten=%d source=touch_scan",
                            needle.second.c_str(),
                            alias_name.c_str(),
                            static_cast<unsigned long>(found_addr),
                            rewritten ? 1 : 0);
                    }
                }

                add_touch_target_locked(needle.first, needle.second, found_addr, mbi.Protect);
                found_keys.insert(key);
            }

            offset += chunk;
        }
    }

    log_line("touch_trace_scan_complete needles=%u found=%u pages=%u regions=%u",
        static_cast<unsigned>(needles.size()),
        static_cast<unsigned>(found_keys.size()),
        static_cast<unsigned>(g_touch_pages.size()),
        regions_scanned);
    for (const auto& target : g_touch_targets)
    {
        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(target.addr, &rva);
        if (std::strcmp(module_name, "<unknown>") == 0)
            log_line("touch_trace_target label=%s text=%s addr=0x%08lX page=0x%08lX module=<unknown>",
                target.label.c_str(), target.text.c_str(), static_cast<unsigned long>(target.addr), static_cast<unsigned long>(target.page_base));
        else
            log_line("touch_trace_target label=%s text=%s addr=0x%08lX page=0x%08lX module=%s rva=0x%08lX",
                target.label.c_str(), target.text.c_str(), static_cast<unsigned long>(target.addr), static_cast<unsigned long>(target.page_base), module_name, rva);
    }

    if (g_probe_mode == ProbeMode::XanimFocus)
    {
        for (const auto& target : g_touch_targets)
        {
            if (target.label != "xanim" || !target.addr || target.text.empty())
                continue;

            std::vector<uintptr_t> name_addrs;
            name_addrs.push_back(target.addr);
            const int candidates = scan_live_xanim_asset_headers_near_name_addrs(target.text.c_str(), name_addrs);
            log_line("xanim_fast_header_scan name=%s addr=0x%08lX candidates=%d",
                target.text.c_str(),
                static_cast<unsigned long>(target.addr),
                candidates);
        }
    }
}

DWORD WINAPI touch_trace_thread(void*)
{
    g_touch_trace_started = true;
    log_line("touch_trace_thread delay_ms=%lu", static_cast<unsigned long>(touch_trace_delay_ms()));
    Sleep(touch_trace_delay_ms());
    if (g_probe_mode == ProbeMode::RenderOpacityFocus)
    {
        log_line("touch_trace_skipped mode=%s reason=stability", probe_mode_name());
        g_touch_trace_complete = true;
        return 0;
    }
    enumerate_modules(false);
    scan_touch_targets();
    arm_touch_trace_pages();
    if (g_probe_mode == ProbeMode::Safe)
        arm_consumer_exec_traces();
    g_touch_trace_complete = true;
    return 0;
}

DWORD WINAPI late_touch_rescan_thread(void*)
{
    for (int pass = 1; pass <= kLateTouchRescanPasses; ++pass)
    {
        Sleep(kLateTouchRescanDelayMs);
        enumerate_modules(false);
        scan_touch_targets();
        arm_touch_trace_pages();
        log_line("late_touch_rescan pass=%d/%d targets=%u pages=%u",
            pass,
            kLateTouchRescanPasses,
            static_cast<unsigned>(g_touch_targets.size()),
            static_cast<unsigned>(g_touch_pages.size()));
    }
    return 0;
}

DWORD WINAPI guard_copy_scan_thread(void*)
{
    for (int pass = 1; pass <= kGuardCopyScanPasses; ++pass)
    {
        Sleep(kGuardCopyScanDelayMs);
        int added = 0;
        {
            std::lock_guard<std::mutex> lock(g_state_mutex);
            added = scan_custom_map_guard_copies_locked();
        }
        arm_touch_trace_pages();
        log_line("guard_copy_scan pass=%d/%d added=%d targets=%u pages=%u",
            pass,
            kGuardCopyScanPasses,
            added,
            static_cast<unsigned>(g_touch_targets.size()),
            static_cast<unsigned>(g_touch_pages.size()));
    }
    return 0;
}

DWORD WINAPI consumer_arm_thread(void*)
{
    const DWORD initial_delay_ms = consumer_arm_initial_delay_ms();
    const DWORD retry_delay_ms =
        g_probe_mode == ProbeMode::XanimAssetLookupFocus ? 500 :
        (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus ? 500 :
        (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath ? 50 :
        (is_minimal_consumer_focus_mode() ? 2000 : kConsumerArmRetryDelayMs)));
    const int max_attempts =
        g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath ? 40 :
        (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus ? 6 : kConsumerArmMaxAttempts);
    log_line("consumer_arm_thread delay_ms=%lu retry_ms=%lu max_attempts=%d",
        static_cast<unsigned long>(initial_delay_ms),
        static_cast<unsigned long>(retry_delay_ms),
        max_attempts);
    Sleep(initial_delay_ms);
    for (int attempt = 1; attempt <= max_attempts; ++attempt)
    {
        const char* stage = "begin";
        log_line("consumer_arm_attempt_begin attempt=%d", attempt);
        int armed = 0;
        __try
        {
            stage = "enumerate_modules";
            enumerate_modules(false);
            log_line("consumer_arm_attempt_enumerate_done attempt=%d", attempt);
            stage = "arm_consumer_exec_traces";
            armed = arm_consumer_exec_traces();
            stage = "complete";
            log_line("consumer_arm_attempt attempt=%d armed=%d", attempt, armed);
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            log_line("consumer_arm_attempt_exception attempt=%d stage=%s code=0x%08lX",
                attempt,
                stage,
                static_cast<unsigned long>(GetExceptionCode()));
            armed = 0;
        }
        if (armed > 0)
            break;
        if (attempt < max_attempts)
            Sleep(retry_delay_ms);
    }
    return 0;
}

DWORD WINAPI selector_root_temporal_thread(void*)
{
    const DWORD start_tick = GetTickCount();
    const DWORD scan_window_ms = 45000;
    const DWORD scan_sleep_ms = 100;
    const size_t chunk_size = 0x10000;
    log_line("selector_root_temporal_thread_started window_ms=%lu sleep_ms=%lu",
        static_cast<unsigned long>(scan_window_ms),
        static_cast<unsigned long>(scan_sleep_ms));

    while ((GetTickCount() - start_tick) < scan_window_ms)
    {
        if (g_consumer_first_hit_logged.load())
            break;

        uintptr_t cursor = 0;
        while (true)
        {
            MEMORY_BASIC_INFORMATION mbi {};
            if (!VirtualQuery(reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)))
                break;

            const uintptr_t region_base = reinterpret_cast<uintptr_t>(mbi.BaseAddress);
            const uintptr_t region_end = region_base + mbi.RegionSize;
            const bool good_region =
                region_is_readable(mbi) &&
                mbi.Type == MEM_PRIVATE &&
                mbi.RegionSize >= 28 &&
                mbi.RegionSize <= 0x02000000;
            if (good_region)
            {
                static constexpr int candidate_offsets[] = {-8, -4, 0, 4, 8};
                uintptr_t scan_cursor = region_base;
                while (scan_cursor + 28 <= region_end)
                {
                    const size_t to_copy = static_cast<size_t>(std::min<uintptr_t>(region_end - scan_cursor, chunk_size));
                    if (to_copy < (9 * sizeof(uint32_t)) || !pointer_readable(scan_cursor, std::min<size_t>(to_copy, 64)))
                    {
                        scan_cursor += chunk_size;
                        continue;
                    }
                    std::vector<uint8_t> buffer(to_copy, 0);
                    if (!safe_copy_memory(scan_cursor, buffer.data(), to_copy))
                    {
                        scan_cursor += chunk_size;
                        continue;
                    }

                    for (size_t offset = 24; offset + 4 <= to_copy; offset += sizeof(uint32_t))
                    {
                        const uint32_t marker = *reinterpret_cast<const uint32_t*>(buffer.data() + offset);
                        if (!is_known_materialization_plus6_value(marker))
                            continue;

                        const uintptr_t base_candidate = scan_cursor + offset - (6 * sizeof(uint32_t));
                        for (int delta : candidate_offsets)
                        {
                            const uintptr_t candidate = base_candidate + delta;
                            if (candidate < region_base || candidate + (9 * sizeof(uint32_t)) > region_end)
                                continue;

                            char reason[32] {};
                            std::snprintf(reason, sizeof(reason), "temporal_scan_%+d", delta);
                            std::lock_guard<std::mutex> lock(g_state_mutex);
                            if (g_temporal_selector_roots.size() < 128 || g_temporal_selector_roots.find(candidate) != g_temporal_selector_roots.end())
                                record_temporal_selector_root_candidate_locked(candidate, reason);
                        }
                    }

                    scan_cursor += to_copy;
                }
            }

            if (region_end <= cursor)
                break;
            cursor = region_end;
        }

        Sleep(scan_sleep_ms);
    }

    log_line("selector_root_temporal_thread_complete first_hit=%d tracked=%u elapsed_ms=%lu",
        g_consumer_first_hit_logged.load() ? 1 : 0,
        static_cast<unsigned>(g_temporal_selector_roots.size()),
        static_cast<unsigned long>(GetTickCount() - start_tick));
    g_selector_root_temporal_started = false;
    return 0;
}

DWORD WINAPI consumer_deferred_snapshot_thread(void* param)
{
    std::unique_ptr<ConsumerDeferredSnapshotRequest> request(static_cast<ConsumerDeferredSnapshotRequest*>(param));
    if (!request)
        return 0;

    const DWORD default_target_offsets_ms[] = {250, 1000, 2500, 4000};
    const char* default_phases[] = {"post_hit_250ms", "post_hit_1000ms", "post_hit_2500ms", "post_hit_4000ms"};
    const DWORD asset_lookup_target_offsets_ms[] = {100, 400, 1200, 2500};
    const char* asset_lookup_phases[] = {"post_hit_100ms", "post_hit_400ms", "post_hit_1200ms", "post_hit_2500ms"};
    const DWORD* target_offsets_ms = default_target_offsets_ms;
    const char** phases = default_phases;
    if (g_probe_mode == ProbeMode::XanimAssetLookupFocus)
    {
        target_offsets_ms = asset_lookup_target_offsets_ms;
        phases = asset_lookup_phases;
    }
    const DWORD start_tick = GetTickCount();
    for (size_t pass = 0; pass < 4; ++pass)
    {
        const DWORD elapsed = GetTickCount() - start_tick;
        if (elapsed < target_offsets_ms[pass])
            Sleep(target_offsets_ms[pass] - elapsed);
        log_line(
            "consumer_deferred_snapshot trigger=%s addr=0x%08lX phase=%s",
            request->trigger_label.c_str(),
            static_cast<unsigned long>(request->trigger_addr),
            phases[pass]);
        for (const auto& anchor : request->anchors)
            log_consumer_anchor_snapshot(anchor.context.c_str(), phases[pass], anchor.base_addr, anchor.before_slots, anchor.after_slots);
        if (g_probe_mode == ProbeMode::XanimConsumerFocus)
        {
            const uintptr_t span_base = g_lookup_family_span_base.load();
            const int span_dwords = g_lookup_family_span_dwords.load();
            if (span_base && span_dwords > 0)
                log_consumer_span_snapshot("lookup_family_span", phases[pass], span_base, span_dwords);
        }
    }
    return 0;
}

bool start_consumer_deferred_snapshots_once_locked(const char* trigger_key, const char* trigger_label, uintptr_t trigger_addr, const std::vector<ConsumerAnchorSnapshot>& anchors)
{
    if (!trigger_key || !*trigger_key || !trigger_label || !*trigger_label || !trigger_addr || anchors.empty())
        return false;

    bool inserted = false;
    inserted = g_consumer_deferred_snapshot_keys.insert(trigger_key).second;
    if (!inserted)
        return false;

    auto* request = new ConsumerDeferredSnapshotRequest();
    request->trigger_label = trigger_label;
    request->trigger_addr = trigger_addr;
    request->anchors = anchors;

    HANDLE snapshot_thread = CreateThread(nullptr, 0, consumer_deferred_snapshot_thread, request, 0, nullptr);
    if (snapshot_thread)
    {
        log_line(
            "consumer_deferred_snapshot_thread_started trigger=%s addr=0x%08lX anchors=%u key=%s",
            trigger_label,
            static_cast<unsigned long>(trigger_addr),
            static_cast<unsigned>(anchors.size()),
            trigger_key);
        CloseHandle(snapshot_thread);
        return true;
    }

    delete request;
    g_consumer_deferred_snapshot_keys.erase(trigger_key);
    log_line(
        "consumer_deferred_snapshot_thread_failed trigger=%s addr=0x%08lX key=%s gle=%lu",
        trigger_label,
        static_cast<unsigned long>(trigger_addr),
        trigger_key,
        GetLastError());
    return false;
}

bool start_consumer_deferred_snapshots_once(const char* trigger_key, const char* trigger_label, uintptr_t trigger_addr, const std::vector<ConsumerAnchorSnapshot>& anchors)
{
    std::lock_guard<std::mutex> lock(g_state_mutex);
    return start_consumer_deferred_snapshots_once_locked(trigger_key, trigger_label, trigger_addr, anchors);
}

uintptr_t rva_to_va(DWORD rva)
{
    return g_main_base + rva;
}

const char* consumer_label_for_addr(uintptr_t addr)
{
    if (addr == rva_to_va(kConsumerImageClassMapRva))
        return "consumer_image_class_map";
    if (addr == rva_to_va(kConsumerAssetClassLookupRva))
        return "consumer_asset_class_lookup";
    if (addr == rva_to_va(kConsumerRenderTableRva))
        return "consumer_render_table";
    if (addr == rva_to_va(kConsumerSubmitFlagsRva))
        return "consumer_submit_flags";
    return nullptr;
}

void arm_opacity_focus_consumers_locked(unsigned long long trace_id, const std::string& path)
{
    const int render_hits = g_probe_mode == ProbeMode::ViewmodelRenderFocus ? 1 : 12;
    const int submit_hits = g_probe_mode == ProbeMode::ViewmodelRenderFocus ? 1 : 4;
    arm_exec_trace_locked("consumer_render_table", rva_to_va(kConsumerRenderTableRva), trace_id, path, render_hits);
    arm_exec_trace_locked("consumer_submit_flags", rva_to_va(kConsumerSubmitFlagsRva), trace_id, path, submit_hits);
    g_opacity_focus_consumers_armed = true;
    log_line("opacity_focus_arm trace=%llu path=%s render_table=0x%08lX submit_flags=0x%08lX",
        trace_id,
        path.c_str(),
        static_cast<unsigned long>(rva_to_va(kConsumerRenderTableRva)),
        static_cast<unsigned long>(rva_to_va(kConsumerSubmitFlagsRva)));
}

void arm_opacity_focus_consumers(unsigned long long trace_id, const std::string& path)
{
    std::lock_guard<std::mutex> lock(g_state_mutex);
    arm_opacity_focus_consumers_locked(trace_id, path);
}

DWORD WINAPI opacity_focus_fallback_thread(void*)
{
    const DWORD delay_ms = std::max<DWORD>(consumer_arm_initial_delay_ms() + 4000, 6000);
    log_line("opacity_focus_fallback_thread delay_ms=%lu", static_cast<unsigned long>(delay_ms));
    Sleep(delay_ms);
    if (g_opacity_focus_consumers_armed.load())
    {
        log_line("opacity_focus_fallback_skipped reason=already_armed");
        return 0;
    }
    enumerate_modules(false);
    const unsigned long long trace_id = g_next_trace_id++;
    arm_opacity_focus_consumers(trace_id, "opacity_focus_fallback");
    log_line("opacity_focus_fallback_armed trace=%llu", trace_id);
    return 0;
}

bool arm_xanim_focus_resolver_locked(unsigned long long trace_id, const std::string& path)
{
    const uintptr_t addr = rva_to_va(kXanimResolverCompareRva);
    if (!is_runtime_candidate_code_addr(addr))
        return false;

    arm_exec_trace_locked("xanim_resolver_compare", addr, trace_id, path, 48);
    auto it = g_exec_traces.find(addr);
    return it != g_exec_traces.end() && it->second.armed;
}

DWORD WINAPI xanim_focus_arm_thread(void*)
{
    log_line("xanim_focus_arm_thread retry_ms=%lu max_attempts=%d",
        static_cast<unsigned long>(kXanimResolverArmRetryDelayMs),
        kXanimResolverArmMaxAttempts);
    for (int attempt = 1; attempt <= kXanimResolverArmMaxAttempts; ++attempt)
    {
        enumerate_modules(false);
        std::lock_guard<std::mutex> lock(g_state_mutex);
        const unsigned long long trace_id = g_next_trace_id++;
        const bool armed = arm_xanim_focus_resolver_locked(trace_id, "xanim_focus_bootstrap");
        const uintptr_t addr = rva_to_va(kXanimResolverCompareRva);
        unsigned long rva = 0;
        const char* module_name = module_name_for_addr(addr, &rva);
        log_line("xanim_focus_bootstrap attempt=%d armed=%d addr=0x%08lX module=%s rva=0x%08lX trace=%llu",
            attempt,
            armed ? 1 : 0,
            static_cast<unsigned long>(addr),
            module_name,
            rva,
            trace_id);
        if (armed)
            return 0;
        if (attempt < kXanimResolverArmMaxAttempts)
            Sleep(kXanimResolverArmRetryDelayMs);
    }
    return 0;
}

std::string join_touch_targets(const std::vector<size_t>& indices)
{
    std::string out;
    unsigned count = 0;
    for (size_t index : indices)
    {
        if (index >= g_touch_targets.size())
            continue;
        const auto& target = g_touch_targets[index];
        if (count++)
            out.push_back(',');
        out += target.label;
        out.push_back(':');
        out += target.text;
        if (count >= 6)
            break;
    }
    return out;
}

void begin_step_trace_locked(DWORD thread_id, const char* label, unsigned long long trace_id, const std::string& path, uintptr_t start_eip, int steps)
{
    if (!label || steps <= 0)
        return;
    auto& state = g_step_traces[thread_id];
    state.label = label;
    state.trace_id = trace_id;
    state.path = path;
    state.last_eip = start_eip;
    state.steps_remaining = steps;
    state.total_steps = steps;
    log_line("step_trace_begin label=%s thread=%lu trace=%llu start=0x%08lX steps=%d path=%s",
        label,
        static_cast<unsigned long>(thread_id),
        trace_id,
        static_cast<unsigned long>(start_eip),
        steps,
        path.c_str());
}

bool bytes_match(uintptr_t addr, const BYTE* expected, size_t size)
{
    BYTE buffer[32] {};
    if (size > sizeof(buffer))
        return false;
    if (!safe_copy_memory(addr, buffer, size))
        return false;
    return std::memcmp(buffer, expected, size) == 0;
}

bool patch_byte(uintptr_t addr, BYTE value, BYTE* original = nullptr)
{
    DWORD old = 0;
    if (!VirtualProtect(reinterpret_cast<void*>(addr), 1, PAGE_EXECUTE_READWRITE, &old))
        return false;
    if (original)
        *original = *reinterpret_cast<BYTE*>(addr);
    *reinterpret_cast<BYTE*>(addr) = value;
    VirtualProtect(reinterpret_cast<void*>(addr), 1, old, &old);
    FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(addr), 1);
    return true;
}

void arm_exec_trace_locked(const char* label, uintptr_t addr, unsigned long long trace_id, const std::string& path, int max_hits = 1)
{
    auto& point = g_exec_traces[addr];
    point.label = label;
    point.addr = addr;
    point.trace_id = trace_id;
    point.path = path;
    point.max_hits = max_hits;
    if (!point.armed)
    {
        if (!patch_byte(addr, 0xCC, &point.original))
            return;
        point.armed = true;
        log_line("exec_trace_armed label=%s addr=0x%08lX original=%02X max_hits=%d trace=%llu path=%s",
            point.label.c_str(), static_cast<unsigned long>(point.addr), point.original, point.max_hits, point.trace_id, point.path.c_str());
        log_bytes_around("exec_trace_site bytes", addr);
    }
    else
    {
        log_line("exec_trace_rearmed label=%s addr=0x%08lX trace=%llu path=%s max_hits=%d",
            point.label.c_str(), static_cast<unsigned long>(point.addr), point.trace_id, point.path.c_str(), point.max_hits);
    }
}

void arm_exec_trace(const char* label, uintptr_t addr, unsigned long long trace_id, const std::string& path, int max_hits = 1)
{
    std::lock_guard<std::mutex> lock(g_state_mutex);
    arm_exec_trace_locked(label, addr, trace_id, path, max_hits);
}

DWORD WINAPI opacity_focus_rearm_thread(void*)
{
    Sleep(250);
    std::lock_guard<std::mutex> lock(g_state_mutex);
    const uintptr_t addr = rva_to_va(kConsumerRenderTableRva);
    auto it = g_exec_traces.find(addr);
    if (it != g_exec_traces.end() && !it->second.armed && it->second.hits < it->second.max_hits)
    {
        patch_byte(it->second.addr, 0xCC, nullptr);
        it->second.armed = true;
        log_line("opacity_focus_rearm label=%s addr=0x%08lX hit=%d max_hits=%d",
            it->second.label.c_str(),
            static_cast<unsigned long>(it->second.addr),
            it->second.hits,
            it->second.max_hits);
    }
    g_opacity_focus_rearm_pending = false;
    return 0;
}

DWORD WINAPI xanim_focus_rearm_thread(void* param)
{
    const uintptr_t addr = reinterpret_cast<uintptr_t>(param);
    Sleep(150);
    std::lock_guard<std::mutex> lock(g_state_mutex);
    auto it = g_exec_traces.find(addr);
    if (it != g_exec_traces.end() && !it->second.armed && it->second.hits < it->second.max_hits)
    {
        patch_byte(it->second.addr, 0xCC, nullptr);
        it->second.armed = true;
        log_line("xanim_focus_rearm label=%s addr=0x%08lX hit=%d max_hits=%d",
            it->second.label.c_str(),
            static_cast<unsigned long>(it->second.addr),
            it->second.hits,
            it->second.max_hits);
    }
    g_xanim_focus_rearm_pending = false;
    return 0;
}

int arm_consumer_exec_traces()
{
    std::lock_guard<std::mutex> lock(g_state_mutex);
    struct ConsumerSpec
    {
        const char* label;
        DWORD rva;
        BYTE bytes[10];
        size_t size;
    };

    static const ConsumerSpec specs[] = {
        {"consumer_image_class_map", kConsumerImageClassMapRva, {0x8B, 0x04, 0x85, 0x28, 0x4A, 0xD2, 0x00, 0x89, 0x06}, 9},
        {"consumer_asset_class_lookup", kConsumerAssetClassLookupRva, {0x0F, 0xB7, 0x41, 0x06, 0x33, 0xDB, 0x89, 0x44, 0x24, 0x14}, 10},
        {"consumer_render_table", kConsumerRenderTableRva, {0x66, 0x83, 0x3E, 0x00, 0x75, 0x7C, 0xEB, 0x04}, 8},
        {"consumer_submit_flags", kConsumerSubmitFlagsRva, {0xF7, 0x86, 0x20, 0xFF, 0xFF, 0xFF, 0x00, 0x20, 0x00, 0x00}, 10},
    };

    int armed_count = 0;
    bool asset_lookup_armed = false;
    for (const auto& spec : specs)
    {
        if (is_render_only_focus_mode())
        {
            const std::string label = spec.label;
            if (label != "consumer_render_table" && label != "consumer_submit_flags")
                continue;
        }
        if (is_asset_lookup_only_mode())
        {
            const std::string label = spec.label;
            if (label != "consumer_asset_class_lookup")
                continue;
        }
        if (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus)
        {
            const std::string label = spec.label;
            if (label != "consumer_asset_class_lookup" &&
                label != "consumer_render_table" &&
                label != "consumer_submit_flags")
                continue;
            if (!g_producer_compact_override.arm_render_from_startup &&
                (label == "consumer_render_table" || label == "consumer_submit_flags"))
                continue;
        }
        if (is_materialization_writepath_mode())
        {
            const std::string label = spec.label;
            if (label != "consumer_asset_class_lookup" && label != "consumer_image_class_map")
                continue;
        }
        const uintptr_t addr = rva_to_va(spec.rva);
        if (!bytes_match(addr, spec.bytes, spec.size))
        {
            log_line("consumer_trace_skip label=%s addr=0x%08lX reason=signature_mismatch",
                spec.label,
                static_cast<unsigned long>(addr));
            log_bytes_around("consumer_trace_skip bytes", addr, 8, 16);
            continue;
        }
        int max_hits = 1;
        if (g_probe_mode == ProbeMode::XanimConsumerFocus && std::strcmp(spec.label, "consumer_render_table") == 0)
            max_hits = 4;
        if (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus && std::strcmp(spec.label, "consumer_render_table") == 0)
            max_hits = 8;
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath && std::strcmp(spec.label, "consumer_render_table") == 0)
            max_hits = 4;
        if (is_minimal_consumer_focus_mode() && std::strcmp(spec.label, "consumer_asset_class_lookup") == 0)
            max_hits = 4;
        arm_exec_trace_locked(spec.label, addr, 0, "consumer_probe", max_hits);
        if (std::strcmp(spec.label, "consumer_asset_class_lookup") == 0)
            asset_lookup_armed = g_exec_traces[addr].armed;
        armed_count += 1;
    }
    if ((g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath ||
         g_probe_mode == ProbeMode::ProducerCompactOverrideFocus) && !asset_lookup_armed)
        return 0;
    if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath ||
        g_probe_mode == ProbeMode::ProducerCompactOverrideFocus)
    {
        const uintptr_t asset_lookup_addr = rva_to_va(kConsumerAssetClassLookupRva);
        const uintptr_t entry = find_function_prologue_near(asset_lookup_addr, 0x200);
        if (entry)
        {
            const int entry_hits = g_probe_mode == ProbeMode::ProducerCompactOverrideFocus ? 4 : 2;
            arm_exec_trace_locked("consumer_asset_lookup_entry", entry, 0, "consumer_probe", entry_hits);
            log_line("asset_lookup_entry_arm addr=0x%08lX target=0x%08lX",
                static_cast<unsigned long>(entry),
                static_cast<unsigned long>(asset_lookup_addr));
        }
        else
        {
            log_line("asset_lookup_entry_not_found target=0x%08lX", static_cast<unsigned long>(asset_lookup_addr));
        }
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath)
            arm_asset_lookup_callsite_traces_locked();
    }
    return armed_count;
}

void log_consumer_render_state(const char* label, const CONTEXT& ctx)
{
    if (!label)
        return;

    const bool minimal_consumer_focus = is_minimal_consumer_focus_mode();

    if (std::strcmp(label, "consumer_asset_class_lookup") == 0)
    {
        uint32_t owner_plus_4 = 0;
        uint16_t class_word = 0;
        uint32_t class_head = 0;
        uint32_t class_slot2 = 0;
        uint32_t class_slot3 = 0;
        uint32_t class_slot4 = 0;
        uint32_t class_slot5 = 0;
        uint32_t class_slot6 = 0;
        if (ctx.Edi)
            safe_copy_memory(ctx.Edi + 4, &owner_plus_4, sizeof(owner_plus_4));
        if (ctx.Ecx)
        {
            safe_copy_memory(ctx.Ecx + 6, &class_word, sizeof(class_word));
            capture_producer_class_values(ctx.Ecx, &class_head, &class_slot2, &class_slot3, &class_slot4, &class_slot5, &class_slot6);
        }

        log_line(
            "consumer_asset_lookup_compact label=%s owner=0x%08lX owner_plus_4=0x%08lX source=0x%08lX class=0x%08lX class_head=0x%08lX class_word=0x%04X esi_nibble=0x%X",
            label,
            ctx.Edi,
            static_cast<unsigned long>(owner_plus_4),
            ctx.Eax,
            ctx.Ecx,
            static_cast<unsigned long>(class_head),
            static_cast<unsigned>(class_word),
            static_cast<unsigned>(ctx.Esi & 0xF));

        if (g_seed_normalization.active && !g_seed_normalization.first_family_logged)
        {
            g_seed_normalization.first_family_logged = true;
            uint32_t source_slots[7] {};
            capture_u32_slots(ctx.Eax, 7, source_slots);
            log_line(
                "seed_to_first_producer_first_family trace=%llu delta_from_birth_ms=%lu seed=0x%08lX source=0x%08lX owner=0x%08lX owner_plus_4=0x%08lX class=0x%08lX source_matches_seed=%d owner_plus4_matches_seed=%d class_head=0x%08lX class_plus2=0x%08lX class_plus3=0x%08lX class_plus4=0x%08lX class_plus5=0x%08lX class_plus6=0x%08lX",
                g_seed_normalization.trace_id,
                static_cast<unsigned long>(GetTickCount() - g_seed_normalization.birth_tick),
                static_cast<unsigned long>(g_seed_normalization.seed_ptr),
                static_cast<unsigned long>(ctx.Eax),
                static_cast<unsigned long>(ctx.Edi),
                static_cast<unsigned long>(owner_plus_4),
                static_cast<unsigned long>(ctx.Ecx),
                ctx.Eax == g_seed_normalization.seed_ptr ? 1 : 0,
                owner_plus_4 == g_seed_normalization.seed_ptr ? 1 : 0,
                static_cast<unsigned long>(class_head),
                class_slot2,
                class_slot3,
                class_slot4,
                class_slot5,
                class_slot6);
            log_seed_normalization_core("first_family_source", g_seed_normalization.trace_id, ctx.Eip, ctx.Eax, source_slots);

            log_line(
                "seed_to_first_producer_seed_compare trace=%llu seed=0x%08lX source=0x%08lX slot0_changed=%d slot1_changed=%d slot2_changed=%d slot3_changed=%d slot4_changed=%d slot5_changed=%d slot6_changed=%d",
                g_seed_normalization.trace_id,
                static_cast<unsigned long>(g_seed_normalization.seed_ptr),
                static_cast<unsigned long>(ctx.Eax),
                source_slots[0] != g_seed_normalization.seed_slots[0] ? 1 : 0,
                source_slots[1] != g_seed_normalization.seed_slots[1] ? 1 : 0,
                source_slots[2] != g_seed_normalization.seed_slots[2] ? 1 : 0,
                source_slots[3] != g_seed_normalization.seed_slots[3] ? 1 : 0,
                source_slots[4] != g_seed_normalization.seed_slots[4] ? 1 : 0,
                source_slots[5] != g_seed_normalization.seed_slots[5] ? 1 : 0,
                source_slots[6] != g_seed_normalization.seed_slots[6] ? 1 : 0);
            uint32_t source_minus4 = 0;
            uint32_t source_minus3 = 0;
            uint32_t source_minus2 = 0;
            uint32_t source_minus1 = 0;
            safe_copy_memory(ctx.Eax + static_cast<intptr_t>(-4 * static_cast<int>(sizeof(uint32_t))), &source_minus4, sizeof(source_minus4));
            safe_copy_memory(ctx.Eax + static_cast<intptr_t>(-3 * static_cast<int>(sizeof(uint32_t))), &source_minus3, sizeof(source_minus3));
            safe_copy_memory(ctx.Eax + static_cast<intptr_t>(-2 * static_cast<int>(sizeof(uint32_t))), &source_minus2, sizeof(source_minus2));
            safe_copy_memory(ctx.Eax + static_cast<intptr_t>(-1 * static_cast<int>(sizeof(uint32_t))), &source_minus1, sizeof(source_minus1));
            log_line(
                "source_to_class_emission_neighborhood trace=%llu source=0x%08lX owner=0x%08lX class=0x%08lX minus4=0x%08lX minus3=0x%08lX minus2=0x%08lX minus1=0x%08lX owner_match_minus4=%d class_match_minus4=%d class_match_minus1=%d",
                g_seed_normalization.trace_id,
                static_cast<unsigned long>(ctx.Eax),
                static_cast<unsigned long>(ctx.Edi),
                static_cast<unsigned long>(ctx.Ecx),
                static_cast<unsigned long>(source_minus4),
                static_cast<unsigned long>(source_minus3),
                static_cast<unsigned long>(source_minus2),
                static_cast<unsigned long>(source_minus1),
                source_minus4 == ctx.Edi ? 1 : 0,
                source_minus4 == ctx.Ecx ? 1 : 0,
                source_minus1 == ctx.Ecx ? 1 : 0);
            if (ctx.Eax)
                log_consumer_anchor_snapshot("seed_to_first_producer_source", "first_family", ctx.Eax, 4, 8);
            if (ctx.Ecx)
                log_consumer_anchor_snapshot("seed_to_first_producer_class", "first_family", ctx.Ecx, 0, 8);
        }

        if (minimal_consumer_focus && g_probe_mode != ProbeMode::ProducerCompactOverrideFocus)
        {
            if (ctx.Edi)
                log_consumer_anchor_snapshot("asset_lookup_edi", "first_hit", ctx.Edi);
            if (ctx.Eax)
                log_consumer_anchor_snapshot("asset_lookup_eax", "first_hit", ctx.Eax);
            if (ctx.Ecx)
                log_consumer_anchor_snapshot("asset_lookup_ecx", "first_hit", ctx.Ecx);

            std::vector<ConsumerAnchorSnapshot> anchors;
            if (ctx.Edi)
                anchors.push_back({"asset_lookup_edi", ctx.Edi, 4, 8});
            if (ctx.Eax)
                anchors.push_back({"asset_lookup_eax", ctx.Eax, 4, 8});
            if (ctx.Ecx)
                anchors.push_back({"asset_lookup_ecx", ctx.Ecx, 4, 8});

            if (!anchors.empty())
            {
                char key[160] {};
                std::snprintf(
                    key,
                    sizeof(key),
                    "asset_lookup|0x%08lX|0x%08lX|0x%08lX",
                    static_cast<unsigned long>(ctx.Edi),
                    static_cast<unsigned long>(ctx.Eax),
                    static_cast<unsigned long>(ctx.Ecx));
                start_consumer_deferred_snapshots_once_locked(key, label, rva_to_va(kConsumerAssetClassLookupRva), anchors);
            }
        }
        return;
    }

    if (std::strcmp(label, "consumer_image_class_map") == 0)
    {
        uint32_t output_value = 0;
        if (ctx.Esi)
            safe_copy_memory(ctx.Esi, &output_value, sizeof(output_value));

        log_line(
            "consumer_image_map_compact label=%s index=0x%08lX out_ptr=0x%08lX out_value=0x%08lX eax_slot=%lu",
            label,
            ctx.Eax,
            ctx.Esi,
            static_cast<unsigned long>(output_value),
            static_cast<unsigned long>(ctx.Eax & 0xFFFF));

        if (minimal_consumer_focus)
        {
            if (ctx.Esi)
                log_consumer_anchor_snapshot("image_map_esi", "first_hit", ctx.Esi);

            if (ctx.Esi)
            {
                char key[96] {};
                std::snprintf(key, sizeof(key), "image_map|0x%08lX|0x%08lX", static_cast<unsigned long>(ctx.Eax), static_cast<unsigned long>(ctx.Esi));
                start_consumer_deferred_snapshots_once_locked(key, label, rva_to_va(kConsumerImageClassMapRva), {{"image_map_esi", ctx.Esi, 4, 8}});
            }
        }
        return;
    }

    if (std::strcmp(label, "consumer_render_table") == 0 ||
        std::strcmp(label, "consumer_render_table_zero_path") == 0 ||
        std::strcmp(label, "consumer_render_table_compare") == 0 ||
        std::strcmp(label, "consumer_render_table_match_branch") == 0 ||
        std::strcmp(label, "consumer_render_table_nonzero_branch") == 0)
    {
        log_line("render_state label=%s esi_minus_e0=0x%08lX esi=0x%08lX esi_plus_8=0x%08lX eax=0x%08lX eax_plus_4=0x%08lX",
            label,
            ctx.Esi >= 0xE0 ? ctx.Esi - 0xE0 : 0,
            ctx.Esi,
            ctx.Esi + 8,
            ctx.Eax,
            ctx.Eax + 4);
        const bool compact_render_focus = minimal_consumer_focus || g_probe_mode == ProbeMode::ViewmodelRenderFocus;
        if (compact_render_focus)
        {
            log_line(
                "consumer_focus_render_state_compact label=%s owning=0x%08lX render=0x%08lX render_plus_8=0x%08lX lookup=0x%08lX",
                label,
                ctx.Esi >= 0xE0 ? ctx.Esi - 0xE0 : 0,
                ctx.Esi,
                ctx.Esi + 8,
                ctx.Eax);
        }
        else
        {
            if (ctx.Esi >= 0xE0)
                log_pointer_info("render_state_esi_minus_e0", ctx.Esi - 0xE0);
            log_pointer_info("render_state_esi", ctx.Esi);
            log_pointer_info("render_state_esi_plus_8", ctx.Esi + 8);
            log_pointer_info("render_state_eax", ctx.Eax);
            if (ctx.Esi >= 0xE0)
            {
                log_bytes_around("render_state_esi_minus_e0_bytes", ctx.Esi - 0xE0, 16, 48);
                log_dword_window("render_state_esi_minus_e0", ctx.Esi - 0xE0);
                track_consumer_object_window("render_state_esi_minus_e0", ctx.Esi - 0xE0);
                log_consumer_dword_window_correlations("render_state_esi_minus_e0", ctx.Esi - 0xE0, 4, capture_dword_window_values(ctx.Esi - 0xE0));
                log_watched_asset_pointers_near("render_state_esi_minus_e0", ctx.Esi - 0xE0);
            }
            log_bytes_around("render_state_esi_bytes", ctx.Esi, 16, 48);
            log_dword_window("render_state_esi", ctx.Esi);
            track_consumer_object_window("render_state_esi", ctx.Esi);
            log_consumer_dword_window_correlations("render_state_esi", ctx.Esi, 4, capture_dword_window_values(ctx.Esi));
            log_watched_asset_pointers_near("render_state_esi", ctx.Esi);
            log_bytes_around("render_state_esi_plus_8_bytes", ctx.Esi + 8, 16, 48);
            log_dword_window("render_state_esi_plus_8", ctx.Esi + 8);
            track_consumer_object_window("render_state_esi_plus_8", ctx.Esi + 8);
            log_consumer_dword_window_correlations("render_state_esi_plus_8", ctx.Esi + 8, 4, capture_dword_window_values(ctx.Esi + 8));
            log_watched_asset_pointers_near("render_state_esi_plus_8", ctx.Esi + 8);
            log_bytes_around("render_state_eax_bytes", ctx.Eax, 16, 48);
            log_dword_window("render_state_eax", ctx.Eax);
            track_consumer_object_window("render_state_eax", ctx.Eax);
            log_consumer_dword_window_correlations("render_state_eax", ctx.Eax, 4, capture_dword_window_values(ctx.Eax));
            log_watched_asset_pointers_near("render_state_eax", ctx.Eax);
        }

        if (std::strcmp(label, "consumer_render_table") == 0)
        {
            WORD esi_word = 0;
            DWORD table_value = 0;
            DWORD esi_plus_8 = 0;
            const bool have_esi_word = safe_copy_memory(ctx.Esi, &esi_word, sizeof(esi_word));
            const bool have_table_value = safe_copy_memory(ctx.Eax, &table_value, sizeof(table_value));
            const bool have_esi_plus_8 = safe_copy_memory(ctx.Esi + 8, &esi_plus_8, sizeof(esi_plus_8));
            const bool zero_lane = have_esi_word && esi_word == 0;
            const bool compare_match = zero_lane && have_table_value && have_esi_plus_8 && table_value == esi_plus_8;
            log_line("render_branch_infer label=%s esi_word=0x%04X zero_lane=%d table_value=0x%08lX esi_plus_8_value=0x%08lX compare_match=%d inferred=%s",
                label,
                static_cast<unsigned>(esi_word),
                zero_lane ? 1 : 0,
                static_cast<unsigned long>(table_value),
                static_cast<unsigned long>(esi_plus_8),
                compare_match ? 1 : 0,
                !zero_lane ? "nonzero_branch" : (compare_match ? "zero_compare_match" : "zero_compare_miss"));
        }
    }

    if (std::strcmp(label, "consumer_submit_flags") == 0)
    {
        const uintptr_t flag_addr = ctx.Esi >= 0xE0 ? (ctx.Esi - 0xE0) : 0;
        DWORD flags = 0;
        if (flag_addr)
            safe_copy_memory(flag_addr, &flags, sizeof(flags));
        log_line("render_submit_flags label=%s flag_addr=0x%08lX flags=0x%08lX test_mask=0x00002000 masked=0x%08lX",
            label,
            static_cast<unsigned long>(flag_addr),
            static_cast<unsigned long>(flags),
            static_cast<unsigned long>(flags & 0x00002000u));
        if (g_probe_mode != ProbeMode::ViewmodelRenderFocus && flag_addr)
        {
            log_pointer_info("render_submit_flag_addr", flag_addr);
            track_consumer_object_window("render_submit_flag_addr", flag_addr);
            log_consumer_dword_window_correlations("render_submit_flag_addr", flag_addr, 4, capture_dword_window_values(flag_addr));
        }
        if (g_probe_mode != ProbeMode::ViewmodelRenderFocus)
        {
            log_pointer_info("render_submit_esi", ctx.Esi);
            log_pointer_info("render_submit_eax", ctx.Eax);
        }
    }
}

void log_consumer_render_hit_context(unsigned hit, const CONTEXT& ctx)
{
    const uintptr_t owning_base = ctx.Esi >= 0xE0 ? ctx.Esi - 0xE0 : 0;
    const DWORD tick = GetTickCount();
    g_last_consumer_render_lookup_addr = ctx.Eax;
    g_last_consumer_render_edi_addr = ctx.Edi;
    log_line(
        "consumer_render_hit_summary hit=%u tick=%lu owning=0x%08lX render=0x%08lX render_plus_8=0x%08lX lookup=0x%08lX",
        hit,
        static_cast<unsigned long>(tick),
        static_cast<unsigned long>(owning_base),
        static_cast<unsigned long>(ctx.Esi),
        static_cast<unsigned long>(ctx.Esi + 8),
        static_cast<unsigned long>(ctx.Eax));

    if (g_probe_mode == ProbeMode::ViewmodelRenderFocus)
        return;

    if (hit <= 2)
    {
        const CallerSelection sel = capture_relevant_caller();
        log_backtrace_selection(0, sel, "consumer_render_table", "consumer_probe");
    }
    log_stack_return_candidates("consumer_render_table", ctx, 16);

    if (hit == 2 || hit == 4)
    {
        char phase[32] {};
        std::snprintf(phase, sizeof(phase), "hit_%u", hit);
        if (owning_base)
            log_consumer_anchor_snapshot("render_state_esi_minus_e0", phase, owning_base);
        log_consumer_anchor_snapshot("render_state_esi", phase, ctx.Esi);
        log_consumer_anchor_snapshot("render_state_esi_plus_8", phase, ctx.Esi + 8);
        if (ctx.Eax)
            log_consumer_anchor_snapshot("render_state_eax", phase, ctx.Eax);
        if (ctx.Edi)
            try_log_consumer_render_edi_family(phase, ctx.Edi, false);
    }
}

void arm_branch_traces_after_return(bool success, unsigned long long trace_id, const std::string& path)
{
    if (success)
    {
        arm_exec_trace("special_open_success_branch", rva_to_va(kSpecialOpenSuccessBranchRva), trace_id, path);
        log_line("branch_trace_request kind=success target1=0x%08lX target2=0x%08lX trace=%llu path=%s",
            static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessBranchRva)),
            static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessContinueRva)),
            trace_id,
            path.c_str());
    }
    else
    {
        arm_exec_trace("special_open_miss_continue", rva_to_va(kSpecialOpenMissContinueRva), trace_id, path);
        arm_exec_trace("special_open_flag_branch", rva_to_va(kSpecialOpenFlagBranchRva), trace_id, path);
        log_line("branch_trace_request kind=miss target1=0x%08lX target2=0x%08lX trace=%llu path=%s",
            static_cast<unsigned long>(rva_to_va(kSpecialOpenMissContinueRva)),
            static_cast<unsigned long>(rva_to_va(kSpecialOpenFlagBranchRva)),
            trace_id,
            path.c_str());
    }
}

CallerSelection capture_relevant_caller()
{
    CallerSelection result;
    void* frames_raw[24] {};
    const USHORT captured = CaptureStackBackTrace(0, static_cast<DWORD>(std::size(frames_raw)), frames_raw, nullptr);
    result.frames.reserve(captured);
    for (USHORT i = 0; i < captured; ++i)
        result.frames.push_back(reinterpret_cast<uintptr_t>(frames_raw[i]));

    uintptr_t first_bootstrapper = 0;
    for (uintptr_t frame : result.frames)
    {
        if (!is_in_main_module(frame))
            continue;
        const unsigned long rva = main_module_rva(frame);
        if (!first_bootstrapper)
            first_bootstrapper = frame;
        if (rva >= 0x00680000 && rva <= 0x006A0000)
        {
            result.selected_return = frame;
            break;
        }
    }

    if (!result.selected_return)
        result.selected_return = first_bootstrapper;

    return result;
}

void log_backtrace_selection(unsigned long long trace_id, const CallerSelection& sel, const std::string& image, const std::string& path)
{
    log_line("caller_select trace=%llu image=%s selected=0x%08lX frame_count=%u path=%s",
        trace_id,
        image.c_str(),
        static_cast<unsigned long>(sel.selected_return),
        static_cast<unsigned>(sel.frames.size()),
        path.c_str());

    const size_t limit = std::min<size_t>(sel.frames.size(), 8);
    for (size_t i = 0; i < limit; ++i)
    {
        const uintptr_t frame = sel.frames[i];
        if (is_in_main_module(frame))
        {
            log_line("caller_frame[%u]=0x%08lX module=plutonium-bootstrapper-win32.exe rva=0x%08lX",
                static_cast<unsigned>(i),
                static_cast<unsigned long>(frame),
                main_module_rva(frame));
        }
        else
        {
            log_line("caller_frame[%u]=0x%08lX module=<other>",
                static_cast<unsigned>(i),
                static_cast<unsigned long>(frame));
        }
    }
}

extern "C" uintptr_t __cdecl on_return_trace_hit(SavedRegisters* saved)
{
    ReturnTraceState state {};
    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_return_states.find(GetCurrentThreadId());
        if (it != g_return_states.end())
        {
            state = it->second;
            g_return_states.erase(it);
        }
    }

    const bool success = saved && saved->eax != 0xFFFFFFFFu;
    log_line("return_trace_hit label=special_open_return hit=1 return=0x%08lX eax=0x%08lX ebx=0x%08lX ecx=0x%08lX edx=0x%08lX esi=0x%08lX edi=0x%08lX success=%d trace=%llu path=%s slot=0x%08lX",
        static_cast<unsigned long>(state.original_return),
        saved ? saved->eax : 0,
        saved ? saved->ebx : 0,
        saved ? saved->ecx : 0,
        saved ? saved->edx : 0,
        saved ? saved->esi : 0,
        saved ? saved->edi : 0,
        success ? 1 : 0,
        state.trace_id,
        state.path.c_str(),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(state.slot)));
    log_bytes_around("return_trace_target bytes", state.original_return);
    arm_branch_traces_after_return(success, state.trace_id, state.path);
    return state.original_return;
}

extern "C" __declspec(naked) void return_trace_thunk()
{
    __asm
    {
        pushfd
        pushad
        mov eax, esp
        push eax
        call on_return_trace_hit
        add esp, 4
        mov [esp + 28], eax
        popad
        popfd
        jmp eax
    }
}

void maybe_install_return_trace(unsigned long long trace_id, uintptr_t selected_return, const std::string& path)
{
    void** slot = reinterpret_cast<void**>(_AddressOfReturnAddress());
    const uintptr_t ret = selected_return;
    if (!ret)
        return;
    if (ret != rva_to_va(kDispatchCallSiteRva))
        return;

    ReturnTraceState state;
    state.slot = slot;
    state.original_return = ret;
    state.trace_id = trace_id;
    state.path = path;

    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        g_return_states[GetCurrentThreadId()] = state;
    }

    *slot = g_return_trace_thunk;
    log_line("return_trace_installed label=special_open_return return=0x%08lX slot=0x%08lX thunk=0x%08lX trace=%llu path=%s",
        static_cast<unsigned long>(ret),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(slot)),
        static_cast<unsigned long>(reinterpret_cast<uintptr_t>(g_return_trace_thunk)),
        trace_id,
        path.c_str());
    log_bytes_around("special_open_caller bytes", ret);
}

void begin_asset_trace(HANDLE handle, const std::string& image, const std::string& path, const std::string& resolved)
{
    AssetTrace trace;
    trace.trace_id = g_next_trace_id++;
    trace.thread_id = GetCurrentThreadId();
    trace.handle = reinterpret_cast<uintptr_t>(handle);
    trace.image = image;
    trace.path = path;
    trace.resolved = resolved;
    const CallerSelection caller = capture_relevant_caller();
    trace.return_addr = caller.selected_return;

    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        g_active_handles[trace.handle] = trace;
    }

    log_line("asset_trace_begin trace=%llu thread=%lu handle=0x%08lX image=%s path=%s resolved=%s return=0x%08lX",
        trace.trace_id, trace.thread_id, static_cast<unsigned long>(trace.handle), trace.image.c_str(), trace.path.c_str(), trace.resolved.c_str(), static_cast<unsigned long>(trace.return_addr));
    if (path.find("\\,") != std::string::npos || image == "fxt_light_phosphorous" || image == "fxt_debris_clump" || image == "fxt_light_glow_square")
        log_backtrace_selection(trace.trace_id, caller, image, path);
    maybe_install_return_trace(trace.trace_id, trace.return_addr, path);
}

HANDLE WINAPI hook_create_file_a(LPCSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file)
{
    const std::string path = file_name ? file_name : "";
    std::string image;
    const bool watched_image = try_match_watched_image(path, image);
    const bool watched_file = path_is_watched_file(to_lower_copy(path));

    HANDLE handle = g_real_create_file_a(file_name, desired_access, share_mode, sa, creation_disposition, flags, template_file);
    std::string resolved = path;

    if (watched_image && handle == INVALID_HANDLE_VALUE && path.find("\\,") != std::string::npos)
    {
        resolved = sanitize_comma_iwi_path(path);
        handle = g_real_create_file_a(resolved.c_str(), desired_access, share_mode, sa, creation_disposition, flags, template_file);
        if (handle != INVALID_HANDLE_VALUE)
            log_line("createfilea_sanitized original=%s resolved=%s handle=0x%08lX", path.c_str(), resolved.c_str(), static_cast<unsigned long>(reinterpret_cast<uintptr_t>(handle)));
        else
            log_line("createfilea_sanitized_miss original=%s resolved=%s", path.c_str(), resolved.c_str());
    }

    if (watched_image || watched_file)
        log_line("createfilea path=%s access=0x%08lX share=0x%08lX creation=0x%08lX flags=0x%08lX handle=0x%08lX", path.c_str(), desired_access, share_mode, creation_disposition, flags, static_cast<unsigned long>(reinterpret_cast<uintptr_t>(handle)));

    if (watched_image && handle != INVALID_HANDLE_VALUE)
        begin_asset_trace(handle, image, path, resolved);

    return handle;
}

HANDLE WINAPI hook_create_file_w(LPCWSTR file_name, DWORD desired_access, DWORD share_mode, LPSECURITY_ATTRIBUTES sa, DWORD creation_disposition, DWORD flags, HANDLE template_file)
{
    const std::string path = file_name ? narrow_from_wide(file_name) : "";
    HANDLE handle = g_real_create_file_w(file_name, desired_access, share_mode, sa, creation_disposition, flags, template_file);
    if (path_is_watched_file(to_lower_copy(path)))
        log_line("createfilew path=%s access=0x%08lX share=0x%08lX creation=0x%08lX flags=0x%08lX handle=0x%08lX", path.c_str(), desired_access, share_mode, creation_disposition, flags, static_cast<unsigned long>(reinterpret_cast<uintptr_t>(handle)));
    return handle;
}

BOOL WINAPI hook_read_file(HANDLE handle, LPVOID buffer, DWORD bytes_to_read, LPDWORD bytes_read, LPOVERLAPPED overlapped)
{
    const BOOL ok = g_real_read_file(handle, buffer, bytes_to_read, bytes_read, overlapped);
    const uintptr_t key = reinterpret_cast<uintptr_t>(handle);
    bool should_arm_opacity_focus = false;
    unsigned long long opacity_trace_id = 0;
    std::string opacity_path;
    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_active_handles.find(key);
        if (it == g_active_handles.end())
            return ok;

        AssetTrace& trace = it->second;
        const DWORD got = bytes_read ? *bytes_read : 0;
        trace.total_read += got;
        trace.read_calls += 1;
        log_line("asset_read trace=%llu handle=0x%08lX ok=%d requested=%lu read=%lu total=%zu calls=%d image=%s resolved=%s",
            trace.trace_id, static_cast<unsigned long>(key), ok ? 1 : 0, bytes_to_read, got, trace.total_read, trace.read_calls, trace.image.c_str(), trace.resolved.c_str());
        if (got && !trace.logged_first)
        {
            log_line("asset_read_first trace=%llu image=%s bytes=%lu prefix=%s", trace.trace_id, trace.image.c_str(), got, hex_prefix(buffer, got).c_str());
            trace.logged_first = true;
            if (g_probe_mode == ProbeMode::RenderOpacityFocus && is_opacity_focus_image(trace.image) && !trace.opacity_focus_armed)
            {
                trace.opacity_focus_armed = true;
                should_arm_opacity_focus = true;
                opacity_trace_id = trace.trace_id;
                opacity_path = "opacity_focus_asset:" + trace.image;
            }
        }
        else if (got)
        {
            log_line("asset_read_sample trace=%llu image=%s bytes=%lu prefix=%s", trace.trace_id, trace.image.c_str(), got, hex_prefix(buffer, got).c_str());
        }
    }

    if (should_arm_opacity_focus)
        arm_opacity_focus_consumers(opacity_trace_id, opacity_path);

    return ok;
}

BOOL WINAPI hook_close_handle(HANDLE handle)
{
    const uintptr_t key = reinterpret_cast<uintptr_t>(handle);
    {
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto it = g_active_handles.find(key);
        if (it != g_active_handles.end())
        {
            const AssetTrace trace = it->second;
            log_line("asset_close trace=%llu handle=0x%08lX image=%s total_read=%zu read_calls=%d resolved=%s",
                trace.trace_id, static_cast<unsigned long>(trace.handle), trace.image.c_str(), trace.total_read, trace.read_calls, trace.resolved.c_str());
            g_active_handles.erase(it);
        }
    }
    return g_real_close_handle(handle);
}

LONG CALLBACK probe_veh(EXCEPTION_POINTERS* info)
{
    if (!info || !info->ExceptionRecord || !info->ContextRecord)
        return EXCEPTION_CONTINUE_SEARCH;

    const DWORD code = info->ExceptionRecord->ExceptionCode;
    CONTEXT& ctx = *info->ContextRecord;

    if (g_tls_in_veh)
        return EXCEPTION_CONTINUE_SEARCH;

    if (code == STATUS_GUARD_PAGE_VIOLATION)
    {
        g_tls_in_veh = true;
        const uintptr_t fault_addr = static_cast<uintptr_t>(info->ExceptionRecord->ExceptionInformation[1]);
        const uintptr_t page_base = fault_addr & ~(static_cast<uintptr_t>(g_system_info.dwPageSize) - 1u);
        const unsigned long access_type = static_cast<unsigned long>(info->ExceptionRecord->ExceptionInformation[0]);

        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto policy_page_it = g_policy_field_pages.find(page_base);
        if (policy_page_it != g_policy_field_pages.end())
        {
            bool any_active = false;
            DWORD restore_protect = PAGE_READONLY;
            PendingPolicyWriteTrace pending {};
            pending.active = true;
            pending.page_base = page_base;
            pending.fault_addr = fault_addr;
            pending.pre_eip = ctx.Eip;
            pending.access_type = access_type;

            for (size_t index : policy_page_it->second)
            {
                if (index >= g_policy_field_watches.size())
                    continue;
                auto& watch = g_policy_field_watches[index];
                if (!watch.active)
                    continue;
                any_active = true;
                restore_protect = watch.original_protect;
                watch.armed = false;
                uint32_t old_value = 0;
                safe_copy_memory(watch.addr, &old_value, sizeof(old_value));
                pending.watch_indices.push_back(index);
                pending.old_values.push_back(old_value);
            }

            if (any_active)
            {
                DWORD old = 0;
                VirtualProtect(reinterpret_cast<void*>(page_base), g_system_info.dwPageSize, restore_protect, &old);
                g_tls_policy_write_trace = std::move(pending);

                log_line(
                    "policy_write_guard_hit tick=%lu access=%s page=0x%08lX fault=0x%08lX eip=0x%08lX watched=%u",
                    static_cast<unsigned long>(GetTickCount()),
                    guard_access_kind(access_type),
                    static_cast<unsigned long>(page_base),
                    static_cast<unsigned long>(fault_addr),
                    ctx.Eip,
                    static_cast<unsigned>(g_tls_policy_write_trace.watch_indices.size()));
                for (size_t i = 0; i < g_tls_policy_write_trace.watch_indices.size(); ++i)
                {
                    const size_t watch_index = g_tls_policy_write_trace.watch_indices[i];
                    if (watch_index >= g_policy_field_watches.size())
                        continue;
                    const auto& watch = g_policy_field_watches[watch_index];
                    log_line(
                        "policy_write_guard_field phase=%s label=%s selector_root=0x%08lX slot=+%d addr=0x%08lX old=0x%08lX arm_tick=%lu delta_from_arm_ms=%lu",
                        watch.phase.c_str(),
                        watch.label.c_str(),
                        static_cast<unsigned long>(watch.selector_root),
                        watch.slot,
                        static_cast<unsigned long>(watch.addr),
                        static_cast<unsigned long>(g_tls_policy_write_trace.old_values[i]),
                        static_cast<unsigned long>(watch.arm_tick),
                        static_cast<unsigned long>(GetTickCount() - watch.arm_tick));
                }
                log_materialization_producer_snapshot("policy_write_guard");
                if (!g_tls_policy_write_trace.watch_indices.empty())
                {
                    const size_t watch_index = g_tls_policy_write_trace.watch_indices[0];
                    if (watch_index < g_policy_field_watches.size())
                    {
                        const auto& watch = g_policy_field_watches[watch_index];
                        log_selector_root_compact_snapshot("policy_write_guard", watch.phase.c_str(), watch.selector_root);
                    }
                }
                {
                    const CallerSelection sel = capture_relevant_caller();
                    log_backtrace_selection(0, sel, "policy_write_guard", "policy_write");
                }
                log_register_block(ctx);
                log_backtrace_frames("policy_write_guard", 0, 12);
                ctx.EFlags |= 0x100u;
                g_tls_in_veh = false;
                return EXCEPTION_CONTINUE_EXECUTION;
            }
        }

        auto page_it = g_touch_pages.find(page_base);
        if (page_it == g_touch_pages.end())
        {
            g_tls_in_veh = false;
            return EXCEPTION_CONTINUE_SEARCH;
        }

        bool any_armed = false;
        DWORD restore_protect = PAGE_READONLY;
        for (size_t index : page_it->second)
        {
            if (index >= g_touch_targets.size())
                continue;
            auto& target = g_touch_targets[index];
            if (!target.armed)
                continue;
            any_armed = true;
            restore_protect = target.original_protect;
            target.armed = false;
            target.hit = true;
        }
        if (!any_armed)
        {
            g_tls_in_veh = false;
            return EXCEPTION_CONTINUE_SEARCH;
        }

        DWORD old = 0;
        VirtualProtect(reinterpret_cast<void*>(page_base), g_system_info.dwPageSize, restore_protect, &old);

        log_line("touch_trace_hit page=0x%08lX fault=0x%08lX eip=0x%08lX targets=%u",
            static_cast<unsigned long>(page_base),
            static_cast<unsigned long>(fault_addr),
            ctx.Eip,
            static_cast<unsigned>(page_it->second.size()));
        bool should_arm_opacity_focus = false;
        bool xanim_focus_hit = false;
        struct ImmediateLiveScan
        {
            std::string label;
            std::string text;
            uintptr_t addr {};
        };
        std::vector<ImmediateLiveScan> immediate_scans;
        for (size_t index : page_it->second)
        {
            if (index >= g_touch_targets.size())
                continue;
            const auto& target = g_touch_targets[index];
            log_line("touch_trace_target_hit label=%s text=%s addr=0x%08lX hit=%d",
                target.label.c_str(),
                target.text.c_str(),
                static_cast<unsigned long>(target.addr),
                target.hit ? 1 : 0);
            if (g_probe_mode == ProbeMode::RenderOpacityFocus && is_opacity_focus_target(target.label, target.text))
                should_arm_opacity_focus = true;
            if (g_probe_mode == ProbeMode::XanimFocus && is_xanim_focus_target(target.label, target.text))
            {
                xanim_focus_hit = true;
                if (target.addr && (target.label == "xmodel" || target.label == "xanim"))
                {
                    const std::string scan_key = target.label + ":" + target.text;
                    if (g_immediate_live_scan_seen.insert(scan_key).second)
                    {
                        ImmediateLiveScan request;
                        request.label = target.label;
                        request.text = target.text;
                        request.addr = target.addr;
                        immediate_scans.push_back(std::move(request));
                    }
                }
            }
        }
        log_register_block(ctx);
        log_bytes_around("touch_trace_eip bytes", ctx.Eip);
        log_backtrace_frames(g_probe_mode == ProbeMode::XanimFocus ? "xanim_touch" : "touch_trace", 0, g_probe_mode == ProbeMode::XanimFocus ? 14 : 10);
        if (xanim_focus_hit)
            log_xanim_focus_context(ctx, page_it->second);
        if (xanim_focus_hit && !g_xanim_asset_census_started.exchange(true))
        {
            HANDLE census_thread = CreateThread(nullptr, 0, xanim_asset_census_thread, nullptr, 0, nullptr);
            if (census_thread)
            {
                log_line("xanim_asset_census_thread_created");
                CloseHandle(census_thread);
            }
            else
            {
                g_xanim_asset_census_started = false;
                log_line("xanim_asset_census_thread_failed gle=%lu", GetLastError());
            }
        }
        if (should_arm_opacity_focus)
        {
            const unsigned long long trace_id = g_next_trace_id++;
            const std::string path = "opacity_focus:" + join_touch_targets(page_it->second);
            arm_opacity_focus_consumers_locked(trace_id, path);
        }
        if (xanim_focus_hit)
        {
            const uintptr_t arm_addr = static_cast<uintptr_t>(ctx.Eip);
            unsigned long arm_rva = 0;
            const char* arm_module = module_name_for_addr(arm_addr, &arm_rva);
            log_line("xanim_focus_touch_only addr=0x%08lX module=%s rva=0x%08lX reason=bootstrap_resolver_active",
                static_cast<unsigned long>(arm_addr),
                arm_module,
                arm_rva);
        }
        for (const auto& scan : immediate_scans)
        {
            log_line("xanim_focus_immediate_scan label=%s name=%s addr=0x%08lX",
                scan.label.c_str(),
                scan.text.c_str(),
                static_cast<unsigned long>(scan.addr));
            if (scan.label == "xmodel")
                scan_live_named_asset_refs("xmodel", scan.text.c_str(), scan.addr);
            else if (scan.label == "xanim")
                scan_live_xanim_asset_candidates(scan.text.c_str(), scan.addr);
        }
        g_tls_in_veh = false;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    if (code == STATUS_BREAKPOINT)
    {
        g_tls_in_veh = true;
        std::lock_guard<std::mutex> lock(g_state_mutex);
        const uintptr_t trap_addr_minus_one = static_cast<uintptr_t>(ctx.Eip - 1);
        const uintptr_t trap_addr_exact = static_cast<uintptr_t>(ctx.Eip);
        auto it = g_exec_traces.find(trap_addr_minus_one);
        if (it == g_exec_traces.end())
            it = g_exec_traces.find(trap_addr_exact);
        if (it == g_exec_traces.end())
        {
            const int seen = g_unhandled_breakpoint_logs.fetch_add(1);
            if (seen < 8)
            {
                unsigned long eip_rva = 0;
                const char* eip_module = module_name_for_addr(ctx.Eip, &eip_rva);
                log_line(
                    "breakpoint_unhandled eip=0x%08lX module=%s%s%08lX",
                    ctx.Eip,
                    eip_module,
                    std::strcmp(eip_module, "<unknown>") ? " rva=0x" : "",
                    eip_rva);
                log_register_block(ctx);
                log_bytes_around("breakpoint_unhandled_eip", ctx.Eip, 16, 32);
                log_pointer_info("breakpoint_eax", ctx.Eax);
                log_pointer_info("breakpoint_esi", ctx.Esi);
                log_pointer_info("breakpoint_edi", ctx.Edi);
                log_backtrace_frames("breakpoint_unhandled", 0, 16);
                log_stack_string_candidates(ctx, 12);
            }
            g_tls_in_veh = false;
            return EXCEPTION_CONTINUE_SEARCH;
        }

        ExecTracePoint& point = it->second;
        const bool late_concurrent_hit = !point.armed;
        if (!late_concurrent_hit)
        {
            patch_byte(point.addr, point.original, nullptr);
            point.armed = false;
        }
        point.hits += 1;
        g_tls_rearm_addr = 0;
        bool should_rearm = point.max_hits > 1 && point.hits < point.max_hits;
        const bool delayed_opacity_rearm =
            g_probe_mode == ProbeMode::RenderOpacityFocus &&
            point.label == "consumer_render_table" &&
            should_rearm;
        const bool delayed_xanim_rearm =
            g_probe_mode == ProbeMode::XanimFocus &&
            point.label == "xanim_resolver_compare" &&
            should_rearm;
        if (delayed_opacity_rearm)
            should_rearm = false;
        if (delayed_xanim_rearm)
            should_rearm = false;
        if (should_rearm)
        {
            g_tls_rearm_addr = point.addr;
            ctx.EFlags |= 0x100;
        }
        ctx.Eip = static_cast<DWORD>(point.addr);

        log_line("exec_trace_hit label=%s hit=%d late=%d eip=0x%08lX addr=0x%08lX trace=%llu path=%s",
            point.label.c_str(), point.hits, late_concurrent_hit ? 1 : 0, static_cast<unsigned long>(point.addr), static_cast<unsigned long>(point.addr), point.trace_id, point.path.c_str());
        const bool compact_viewmodel_focus = g_probe_mode == ProbeMode::ViewmodelRenderFocus &&
            (point.label == "consumer_render_table" || point.label == "consumer_submit_flags");
        if ((is_minimal_consumer_focus_mode() || compact_viewmodel_focus) &&
            is_consumer_trace_label(point.label) &&
            !g_consumer_first_hit_logged.exchange(true))
        {
            log_line("consumer_first_hit label=%s hit=%d addr=0x%08lX trace=%llu path=%s",
                point.label.c_str(),
                point.hits,
                static_cast<unsigned long>(point.addr),
                point.trace_id,
                point.path.c_str());
        }
        if (!compact_viewmodel_focus)
        {
            log_register_block(ctx);
            log_bytes_around("eip bytes", point.addr);
            log_pointer_info("eax", ctx.Eax);
            log_pointer_info("ebx", ctx.Ebx);
            log_pointer_info("ecx", ctx.Ecx);
            log_pointer_info("edx", ctx.Edx);
            log_pointer_info("esi", ctx.Esi);
            log_pointer_info("edi", ctx.Edi);
            log_pointer_info("ebp", ctx.Ebp);
            log_pointer_info("esp", ctx.Esp);
        }
        log_consumer_render_state(point.label.c_str(), ctx);
        if ((is_minimal_consumer_focus_mode() || compact_viewmodel_focus) && point.label == "consumer_render_table")
            log_consumer_render_hit_context(point.hits, ctx);
        if (is_minimal_consumer_focus_mode() && point.label == "consumer_asset_lookup_entry")
            log_consumer_asset_lookup_entry_hit_context(point.hits, ctx, point.trace_id, point.path);
        if (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus &&
            g_producer_compact_override.enabled &&
            g_producer_compact_override.trace_bridge_to_first_producer &&
            point.label == "consumer_asset_lookup_entry" &&
            point.hits == 1 &&
            g_step_traces.find(GetCurrentThreadId()) == g_step_traces.end())
        {
            uint32_t bridge_minus3 = 0;
            uint32_t bridge_minus1 = 0;
            uint32_t bridge_plus3 = 0;
            const bool have_wrapper = capture_entry_wrapper_values(ctx.Edi, &bridge_minus3, &bridge_minus1, &bridge_plus3);
            const bool bucket_ok =
                !g_producer_compact_override.require_bridge_bucket ||
                (have_wrapper &&
                 bridge_minus1 == g_producer_compact_override.bridge_required_minus1 &&
                 bridge_plus3 == g_producer_compact_override.bridge_required_plus3);
            if (bucket_ok)
            {
                const int trace_steps = g_producer_compact_override.bridge_trace_steps > 0
                    ? static_cast<int>(g_producer_compact_override.bridge_trace_steps)
                    : kBridgeToFirstProducerStepTraceInstructions;
                begin_step_trace_locked(
                    GetCurrentThreadId(),
                    "bridge_to_first_producer_flow",
                    point.trace_id,
                    point.path,
                    point.addr,
                    trace_steps);
                auto step_state_it = g_step_traces.find(GetCurrentThreadId());
                if (step_state_it != g_step_traces.end())
                    prime_entry_wrapper_trace_state_locked(step_state_it->second, ctx);
                ctx.EFlags |= 0x100u;
                log_line(
                    "bridge_to_first_producer_trace_armed trace=%llu base=0x%08lX minus3=0x%08lX minus1=0x%08lX plus3=0x%08lX steps=%d path=%s source=entry",
                    point.trace_id,
                    static_cast<unsigned long>(ctx.Edi),
                    static_cast<unsigned long>(bridge_minus3),
                    static_cast<unsigned long>(bridge_minus1),
                    static_cast<unsigned long>(bridge_plus3),
                    trace_steps,
                    point.path.c_str());
            }
        }
        if (is_minimal_consumer_focus_mode() && point.label == "consumer_asset_class_lookup")
            log_consumer_asset_lookup_hit_context(point.hits, point.trace_id, point.path, ctx);
        if (is_minimal_consumer_focus_mode() && point.label == "consumer_image_class_map")
            log_consumer_image_class_map_hit_context(point.hits, ctx);
        if (is_minimal_consumer_focus_mode() && point.label.rfind("consumer_upstream_ret_", 0) == 0)
            log_consumer_upstream_hit_context(point.label, point.hits, ctx);
        if (g_probe_mode == ProbeMode::ProducerCompactOverrideFocus &&
            g_producer_compact_override.enabled &&
            g_producer_compact_override.trace_bridge_to_first_producer &&
            point.label == "consumer_upstream_ret_00341F6C" &&
            point.hits == 1 &&
            g_step_traces.find(GetCurrentThreadId()) == g_step_traces.end())
        {
            uint32_t bridge_minus3 = 0;
            uint32_t bridge_minus1 = 0;
            uint32_t bridge_plus3 = 0;
            const bool have_wrapper = capture_entry_wrapper_values(ctx.Edi, &bridge_minus3, &bridge_minus1, &bridge_plus3);
            const bool bucket_ok =
                !g_producer_compact_override.require_bridge_bucket ||
                (have_wrapper &&
                 bridge_minus1 == g_producer_compact_override.bridge_required_minus1 &&
                 bridge_plus3 == g_producer_compact_override.bridge_required_plus3);
            if (bucket_ok)
            {
                const int trace_steps = g_producer_compact_override.bridge_trace_steps > 0
                    ? static_cast<int>(g_producer_compact_override.bridge_trace_steps)
                    : kBridgeToFirstProducerStepTraceInstructions;
                begin_step_trace_locked(
                    GetCurrentThreadId(),
                    "bridge_to_first_producer_flow",
                    point.trace_id,
                    point.path,
                    point.addr,
                    trace_steps);
                auto step_state_it = g_step_traces.find(GetCurrentThreadId());
                if (step_state_it != g_step_traces.end())
                    prime_entry_wrapper_trace_state_locked(step_state_it->second, ctx);
                ctx.EFlags |= 0x100u;
                log_line(
                    "bridge_to_first_producer_trace_armed trace=%llu base=0x%08lX minus3=0x%08lX minus1=0x%08lX plus3=0x%08lX steps=%d path=%s",
                    point.trace_id,
                    static_cast<unsigned long>(ctx.Edi),
                    static_cast<unsigned long>(bridge_minus3),
                    static_cast<unsigned long>(bridge_minus1),
                    static_cast<unsigned long>(bridge_plus3),
                    trace_steps,
                    point.path.c_str());
            }
            else
            {
                log_line(
                    "bridge_to_first_producer_trace_skip trace=%llu base=0x%08lX have_wrapper=%d minus1=0x%08lX plus3=0x%08lX required_minus1=0x%08lX required_plus3=0x%08lX",
                    point.trace_id,
                    static_cast<unsigned long>(ctx.Edi),
                    have_wrapper ? 1 : 0,
                    static_cast<unsigned long>(bridge_minus1),
                    static_cast<unsigned long>(bridge_plus3),
                    static_cast<unsigned long>(g_producer_compact_override.bridge_required_minus1),
                    static_cast<unsigned long>(g_producer_compact_override.bridge_required_plus3));
            }
        }
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath &&
            point.label == "consumer_asset_class_lookup" &&
            point.hits == 1)
        {
            log_stack_return_candidates("asset_lookup_stack", ctx, 32);
            arm_consumer_upstream_return_traces_from_stack_locked(ctx, point.trace_id, point.path);
        }
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath &&
            point.label == "consumer_asset_lookup_callsite" &&
            g_policy_field_watches.empty())
        {
            const char* phase = "asset_lookup_callsite";
            bool armed = false;
            armed = maybe_arm_selector_root_from_candidate(phase, "callsite_edi", ctx.Edi) || armed;
            armed = maybe_arm_selector_root_from_candidate(phase, "callsite_esi", ctx.Esi) || armed;
            armed = maybe_arm_selector_root_from_candidate(phase, "callsite_eax", ctx.Eax) || armed;
            armed = maybe_arm_selector_root_from_candidate(phase, "callsite_ecx", ctx.Ecx) || armed;
            if (!armed && g_latest_materialization_producer.class_head)
                maybe_arm_selector_root_from_candidate(phase, "callsite_class_head", g_latest_materialization_producer.class_head);
        }
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath &&
            point.label == "consumer_asset_lookup_entry" &&
            g_policy_field_watches.empty())
        {
            probe_entry_selector_root_candidates_locked("asset_lookup_entry", ctx);
            if (point.hits <= 1 && g_step_traces.find(GetCurrentThreadId()) == g_step_traces.end())
            {
                begin_step_trace_locked(
                    GetCurrentThreadId(),
                    "asset_lookup_entry_flow",
                    point.trace_id,
                    point.path,
                    point.addr,
                    kConsumerEntryStepTraceInstructions);
                auto step_state_it = g_step_traces.find(GetCurrentThreadId());
                if (step_state_it != g_step_traces.end())
                    prime_entry_wrapper_trace_state_locked(step_state_it->second, ctx);
                ctx.EFlags |= 0x100u;
                log_line(
                    "branch_trace_request kind=asset_lookup_entry_flow start=0x%08lX steps=%d trace=%llu path=%s",
                    static_cast<unsigned long>(point.addr),
                    kConsumerEntryStepTraceInstructions,
                    point.trace_id,
                    point.path.c_str());
            }
        }
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath &&
            point.label.rfind("consumer_upstream_ret_", 0) == 0 &&
            g_policy_field_watches.empty())
        {
            const char* phase = "asset_lookup_upstream_ret";
            bool armed = false;
            armed = maybe_arm_selector_root_from_candidate(phase, "upstream_edi", ctx.Edi) || armed;
            armed = maybe_arm_selector_root_from_candidate(phase, "upstream_esi", ctx.Esi) || armed;
            armed = maybe_arm_selector_root_from_candidate(phase, "upstream_eax", ctx.Eax) || armed;
            armed = maybe_arm_selector_root_from_candidate(phase, "upstream_ecx", ctx.Ecx) || armed;
            if (!armed && g_latest_materialization_producer.class_head)
                maybe_arm_selector_root_from_candidate(phase, "upstream_class_head", g_latest_materialization_producer.class_head);
        }
        if ((g_probe_mode == ProbeMode::XanimConsumerFocus || g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath) &&
            point.label == "consumer_render_table" &&
            point.hits == 1)
        {
            const uintptr_t owning_base = ctx.Esi >= 0xE0 ? ctx.Esi - 0xE0 : 0;
            arm_consumer_upstream_return_traces_from_stack_locked(ctx, point.trace_id, point.path);
            if (ctx.Edi)
            {
                const char* phase_name = g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath ? "writepath_first_hit" : "first_hit";
                arm_selector_root_policy_watches_locked(phase_name, ctx.Edi);
                if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath)
                {
                    log_materialization_producer_snapshot("render_first_hit");
                    log_selector_root_compact_snapshot("render_first_hit", phase_name, ctx.Edi);
                }
            }
            if (owning_base)
                log_consumer_anchor_snapshot("render_state_esi_minus_e0", "first_hit", owning_base);
            log_consumer_anchor_snapshot("render_state_esi", "first_hit", ctx.Esi);
            log_consumer_anchor_snapshot("render_state_esi_plus_8", "first_hit", ctx.Esi + 8);
            if (ctx.Eax)
                log_consumer_anchor_snapshot("render_state_eax", "first_hit", ctx.Eax);
            if (ctx.Edi)
                try_log_consumer_render_edi_family("first_hit", ctx.Edi, true);

            std::vector<ConsumerAnchorSnapshot> anchors;
            std::unordered_set<std::string> seen_contexts;
            if (owning_base)
            {
                anchors.push_back({"render_state_esi_minus_e0", owning_base, 4, 8});
                seen_contexts.insert("render_state_esi_minus_e0");
            }
            anchors.push_back({"render_state_esi", ctx.Esi, 4, 8});
            anchors.push_back({"render_state_esi_plus_8", ctx.Esi + 8, 4, 8});
            seen_contexts.insert("render_state_esi");
            seen_contexts.insert("render_state_esi_plus_8");
            if (ctx.Eax)
            {
                anchors.push_back({"render_state_eax", ctx.Eax, 4, 8});
                seen_contexts.insert("render_state_eax");
            }
            if (ctx.Edi)
            {
                anchors.push_back({"render_state_edi_policy", ctx.Edi, 16, 8});
                seen_contexts.insert("render_state_edi_policy");
                anchors.push_back({"render_state_edi", ctx.Edi, 4, 8});
                seen_contexts.insert("render_state_edi");
                append_pointer_anchor_from_object_slot_if_valid(anchors, seen_contexts, "render_state_edi_child_2", ctx.Edi, 2);
                append_pointer_anchor_from_object_slot_if_valid(anchors, seen_contexts, "render_state_edi_child_3", ctx.Edi, 3);
                append_pointer_anchor_from_object_slot_if_valid(anchors, seen_contexts, "render_state_edi_child_4", ctx.Edi, 4);
                append_pointer_anchor_from_object_slot_if_valid(anchors, seen_contexts, "render_state_edi_child_7", ctx.Edi, 7);
            }

            char key[160] {};
            std::snprintf(
                key,
                sizeof(key),
                "render_table|0x%08lX|0x%08lX|0x%08lX",
                static_cast<unsigned long>(owning_base),
                static_cast<unsigned long>(ctx.Esi),
                static_cast<unsigned long>(ctx.Eax));
            start_consumer_deferred_snapshots_once_locked(key, point.label.c_str(), point.addr, anchors);
        }
        if (point.label == "xanim_resolver_compare")
            log_xanim_resolver_state(ctx);
        else if (point.label == "xanim_resolver_null_branch_fallthrough" || point.label == "xanim_resolver_null_branch_taken")
            log_xanim_resolver_branch_state(point.label.c_str(), ctx);

        if (point.label == "consumer_render_table")
        {
            if (!is_render_only_focus_mode())
            {
                arm_exec_trace_locked("consumer_render_table_zero_path", rva_to_va(kConsumerRenderTableZeroPathRva), point.trace_id, point.path);
                arm_exec_trace_locked("consumer_render_table_compare", rva_to_va(kConsumerRenderTableCompareRva), point.trace_id, point.path);
                arm_exec_trace_locked("consumer_render_table_match_branch", rva_to_va(kConsumerRenderTableMatchBranchRva), point.trace_id, point.path);
                arm_exec_trace_locked("consumer_render_table_nonzero_branch", rva_to_va(kConsumerRenderTableNonZeroBranchRva), point.trace_id, point.path);
                log_line("branch_trace_request kind=consumer_render_table target1=0x%08lX target2=0x%08lX target3=0x%08lX target4=0x%08lX",
                    static_cast<unsigned long>(rva_to_va(kConsumerRenderTableZeroPathRva)),
                    static_cast<unsigned long>(rva_to_va(kConsumerRenderTableCompareRva)),
                    static_cast<unsigned long>(rva_to_va(kConsumerRenderTableMatchBranchRva)),
                    static_cast<unsigned long>(rva_to_va(kConsumerRenderTableNonZeroBranchRva)));
            }
            else if (delayed_opacity_rearm && !g_opacity_focus_rearm_pending.exchange(true))
            {
                HANDLE rearm_thread = CreateThread(nullptr, 0, opacity_focus_rearm_thread, nullptr, 0, nullptr);
                if (rearm_thread)
                {
                    log_line("opacity_focus_rearm_thread_started hit=%d max_hits=%d", point.hits, point.max_hits);
                    CloseHandle(rearm_thread);
                }
                else
                {
                    g_opacity_focus_rearm_pending = false;
                    log_line("opacity_focus_rearm_thread_failed gle=%lu", GetLastError());
                }
            }
        }
        else if (point.label == "xanim_resolver_compare" && delayed_xanim_rearm && !g_xanim_focus_rearm_pending.exchange(true))
        {
            if (point.hits <= 3)
            {
                begin_step_trace_locked(GetCurrentThreadId(), "xanim_resolver_flow", point.trace_id, point.path, point.addr, kXanimStepTraceInstructions);
                ctx.EFlags |= 0x100u;
                arm_exec_trace_locked("xanim_resolver_null_branch_fallthrough", rva_to_va(kXanimResolverNullBranchFallthroughRva), point.trace_id, point.path, 8);
                arm_exec_trace_locked("xanim_resolver_null_branch_taken", rva_to_va(kXanimResolverNullBranchTakenRva), point.trace_id, point.path, 8);
                log_line("branch_trace_request kind=xanim_resolver_null_gate fallthrough=0x%08lX taken=0x%08lX trace=%llu path=%s",
                    static_cast<unsigned long>(rva_to_va(kXanimResolverNullBranchFallthroughRva)),
                    static_cast<unsigned long>(rva_to_va(kXanimResolverNullBranchTakenRva)),
                    point.trace_id,
                    point.path.c_str());
            }
            HANDLE rearm_thread = CreateThread(nullptr, 0, xanim_focus_rearm_thread, reinterpret_cast<void*>(point.addr), 0, nullptr);
            if (rearm_thread)
            {
                log_line("xanim_focus_rearm_thread_started hit=%d max_hits=%d", point.hits, point.max_hits);
                CloseHandle(rearm_thread);
            }
            else
            {
                g_xanim_focus_rearm_pending = false;
                log_line("xanim_focus_rearm_thread_failed gle=%lu", GetLastError());
            }
        }
        else if (point.label == "xanim_resolver_null_branch_fallthrough")
        {
            if (point.hits <= 1)
            {
                begin_step_trace_locked(GetCurrentThreadId(), "xanim_resolver_fallthrough_flow", point.trace_id, point.path, point.addr, kXanimFallthroughStepTraceInstructions);
                ctx.EFlags |= 0x100u;
                log_line("branch_trace_request kind=xanim_resolver_fallthrough_flow start=0x%08lX steps=%d trace=%llu path=%s",
                    static_cast<unsigned long>(point.addr),
                    kXanimFallthroughStepTraceInstructions,
                    point.trace_id,
                    point.path.c_str());
            }
        }

        if (point.label == "special_open_success_class1_continue")
        {
            log_line("branch_trace_request kind=class1_call target=0x%08lX postcall=0x%08lX trace=%llu path=%s",
                static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessClass1CallTargetRva)),
                static_cast<unsigned long>(rva_to_va(kSpecialOpenSuccessClass1PostCallRva)),
                point.trace_id,
                point.path.c_str());
            arm_exec_trace_locked("special_open_class1_call_entry", rva_to_va(kSpecialOpenSuccessClass1CallTargetRva), point.trace_id, point.path);
            arm_exec_trace_locked("special_open_class1_postcall", rva_to_va(kSpecialOpenSuccessClass1PostCallRva), point.trace_id, point.path);
        }
        else if (point.label == "special_open_success_branch")
        {
            arm_exec_trace_locked("special_open_success_postcall", rva_to_va(kSpecialOpenSuccessPostCallRva), point.trace_id, point.path);
        }
        else if (point.label == "special_open_success_postcall")
        {
            arm_exec_trace_locked("special_open_success_continue", rva_to_va(kSpecialOpenSuccessContinueRva), point.trace_id, point.path);
        }
        else if (point.label == "special_open_success_continue")
        {
            arm_exec_trace_locked("special_open_success_class1_continue", rva_to_va(kSpecialOpenSuccessClass1ContinueRva), point.trace_id, point.path);
        }
        g_tls_in_veh = false;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    if (code == STATUS_SINGLE_STEP)
    {
        g_tls_in_veh = true;
        std::lock_guard<std::mutex> lock(g_state_mutex);
        auto step_it = g_step_traces.find(GetCurrentThreadId());
        bool keep_tracing = false;
        bool chain_post_fallthrough = false;
        unsigned long long chained_trace_id = 0;
        std::string chained_path;
        if (step_it != g_step_traces.end())
        {
            StepTraceState& state = step_it->second;
            log_line("step_trace_hit label=%s trace=%llu step=%d eip=0x%08lX prev=0x%08lX path=%s",
                state.label.c_str(),
                state.trace_id,
                state.total_steps - state.steps_remaining + 1,
                ctx.Eip,
                static_cast<unsigned long>(state.last_eip),
                state.path.c_str());
            log_register_block(ctx);
            log_bytes_around("step_trace_eip bytes", ctx.Eip);
            log_pointer_info("eax", ctx.Eax);
            log_pointer_info("ecx", ctx.Ecx);
            log_pointer_info("edx", ctx.Edx);
            log_pointer_info("esi", ctx.Esi);
            log_pointer_info("edi", ctx.Edi);
            if (state.label == "asset_lookup_entry_flow")
            {
                probe_entry_selector_root_candidates_locked("asset_lookup_entry_step", ctx);
                if (ctx.Edi)
                    log_consumer_anchor_snapshot("asset_lookup_entry_step_edi", "step", ctx.Edi, 4, 8);
                if (ctx.Ecx)
                    log_consumer_anchor_snapshot("asset_lookup_entry_step_ecx", "step", ctx.Ecx, 4, 8);
                if (ctx.Eax)
                    log_consumer_anchor_snapshot("asset_lookup_entry_step_eax", "step", ctx.Eax, 4, 8);
                trace_entry_wrapper_step_locked(state, ctx, state.total_steps - state.steps_remaining + 1);
            }
            if (state.label == "bridge_to_first_producer_flow")
            {
                if (!state.wrapper_initialized && ctx.Edi)
                    prime_entry_wrapper_trace_state_locked(state, ctx);
                trace_entry_wrapper_step_locked(state, ctx, state.total_steps - state.steps_remaining + 1);
                maybe_prime_bridge_producer_candidate_locked(state, ctx, state.total_steps - state.steps_remaining + 1);
                trace_producer_class_step_locked(state, ctx, state.total_steps - state.steps_remaining + 1);
                if (state.force_complete)
                    state.steps_remaining = 1;
            }
            if (state.label == "producer_target_family_flow")
            {
                trace_producer_class_step_locked(state, ctx, state.total_steps - state.steps_remaining + 1);
            }
            state.last_eip = ctx.Eip;
            state.steps_remaining -= 1;
            if (state.steps_remaining > 0)
                keep_tracing = true;
            else
            {
                if (state.label == "asset_lookup_entry_flow" && state.wrapper_initialized)
                {
                    log_line(
                        "entry_wrapper_trace_complete trace=%llu base=0x%08lX any_change=%d minus3_changed=%d minus1_changed=%d plus3_changed=%d final_minus3=0x%08lX final_minus1=0x%08lX final_plus3=0x%08lX",
                        state.trace_id,
                        static_cast<unsigned long>(state.wrapper_base),
                        state.wrapper_any_change ? 1 : 0,
                        state.wrapper_slot_changed[0] ? 1 : 0,
                        state.wrapper_slot_changed[1] ? 1 : 0,
                        state.wrapper_slot_changed[2] ? 1 : 0,
                        static_cast<unsigned long>(state.wrapper_last_values[0]),
                        static_cast<unsigned long>(state.wrapper_last_values[1]),
                        static_cast<unsigned long>(state.wrapper_last_values[2]));
                }
                if (state.label == "producer_target_family_flow" && state.producer_initialized)
                {
                    log_line(
                        "producer_class_trace_complete trace=%llu base=0x%08lX any_change=%d class_head_changed=%d class_plus2_changed=%d class_plus3_changed=%d class_plus4_changed=%d class_plus5_changed=%d class_plus6_changed=%d final_class_head=0x%08lX final_class_plus2=0x%08lX final_class_plus3=0x%08lX final_class_plus4=0x%08lX final_class_plus5=0x%08lX final_class_plus6=0x%08lX",
                        state.trace_id,
                        static_cast<unsigned long>(state.producer_class_ptr),
                        state.producer_any_change ? 1 : 0,
                        state.producer_field_changed[0] ? 1 : 0,
                        state.producer_field_changed[1] ? 1 : 0,
                        state.producer_field_changed[2] ? 1 : 0,
                        state.producer_field_changed[3] ? 1 : 0,
                        state.producer_field_changed[4] ? 1 : 0,
                        state.producer_field_changed[5] ? 1 : 0,
                        static_cast<unsigned long>(state.producer_last_values[0]),
                        static_cast<unsigned long>(state.producer_last_values[1]),
                        static_cast<unsigned long>(state.producer_last_values[2]),
                        static_cast<unsigned long>(state.producer_last_values[3]),
                        static_cast<unsigned long>(state.producer_last_values[4]),
                        static_cast<unsigned long>(state.producer_last_values[5]));
                }
                if (state.label == "bridge_to_first_producer_flow")
                {
                    log_line(
                        "bridge_to_first_producer_trace_complete trace=%llu wrapper_base=0x%08lX wrapper_any_change=%d final_minus3=0x%08lX final_minus1=0x%08lX final_plus3=0x%08lX producer_seen=%d producer_class=0x%08lX producer_any_change=%d final_class_head=0x%08lX final_class_plus2=0x%08lX final_class_plus3=0x%08lX final_class_plus4=0x%08lX final_class_plus5=0x%08lX final_class_plus6=0x%08lX",
                        state.trace_id,
                        static_cast<unsigned long>(state.wrapper_base),
                        state.wrapper_any_change ? 1 : 0,
                        static_cast<unsigned long>(state.wrapper_last_values[0]),
                        static_cast<unsigned long>(state.wrapper_last_values[1]),
                        static_cast<unsigned long>(state.wrapper_last_values[2]),
                        state.producer_initialized ? 1 : 0,
                        static_cast<unsigned long>(state.producer_class_ptr),
                        state.producer_any_change ? 1 : 0,
                        static_cast<unsigned long>(state.producer_last_values[0]),
                        static_cast<unsigned long>(state.producer_last_values[1]),
                        static_cast<unsigned long>(state.producer_last_values[2]),
                        static_cast<unsigned long>(state.producer_last_values[3]),
                        static_cast<unsigned long>(state.producer_last_values[4]),
                        static_cast<unsigned long>(state.producer_last_values[5]));
                }
                log_line("step_trace_end label=%s trace=%llu eip=0x%08lX",
                    state.label.c_str(),
                    state.trace_id,
                    ctx.Eip);
                if (state.label == "xanim_resolver_fallthrough_flow" &&
                    !g_xanim_post_fallthrough_trace_started.exchange(true))
                {
                    chain_post_fallthrough = true;
                    chained_trace_id = state.trace_id;
                    chained_path = state.path;
                }
                g_step_traces.erase(step_it);
            }
        }

        if (g_tls_policy_write_trace.active)
        {
            bool any_changed = false;
            log_line(
                "policy_write_post_step tick=%lu access=%s page=0x%08lX fault=0x%08lX pre_eip=0x%08lX post_eip=0x%08lX watched=%u",
                static_cast<unsigned long>(GetTickCount()),
                guard_access_kind(g_tls_policy_write_trace.access_type),
                static_cast<unsigned long>(g_tls_policy_write_trace.page_base),
                static_cast<unsigned long>(g_tls_policy_write_trace.fault_addr),
                static_cast<unsigned long>(g_tls_policy_write_trace.pre_eip),
                ctx.Eip,
                static_cast<unsigned>(g_tls_policy_write_trace.watch_indices.size()));
            for (size_t i = 0; i < g_tls_policy_write_trace.watch_indices.size(); ++i)
            {
                const size_t watch_index = g_tls_policy_write_trace.watch_indices[i];
                if (watch_index >= g_policy_field_watches.size())
                    continue;
                auto& watch = g_policy_field_watches[watch_index];
                uint32_t new_value = 0;
                safe_copy_memory(watch.addr, &new_value, sizeof(new_value));
                const uint32_t old_value = i < g_tls_policy_write_trace.old_values.size() ? g_tls_policy_write_trace.old_values[i] : 0;
                const bool changed = old_value != new_value;
                if (changed)
                {
                    any_changed = true;
                    watch.last_value = new_value;
                    watch.write_hits += 1;
                }
                log_line(
                    "policy_write_commit tick=%lu phase=%s label=%s selector_root=0x%08lX slot=+%d addr=0x%08lX old=0x%08lX new=0x%08lX changed=%d hits=%u delta_from_arm_ms=%lu",
                    static_cast<unsigned long>(GetTickCount()),
                    watch.phase.c_str(),
                    watch.label.c_str(),
                    static_cast<unsigned long>(watch.selector_root),
                    watch.slot,
                    static_cast<unsigned long>(watch.addr),
                    static_cast<unsigned long>(old_value),
                    static_cast<unsigned long>(new_value),
                    changed ? 1 : 0,
                    watch.write_hits,
                    static_cast<unsigned long>(GetTickCount() - watch.arm_tick));
            }

            if (any_changed)
            {
                log_materialization_producer_snapshot("policy_write_commit");
                if (!g_tls_policy_write_trace.watch_indices.empty())
                {
                    const size_t watch_index = g_tls_policy_write_trace.watch_indices[0];
                    if (watch_index < g_policy_field_watches.size())
                    {
                        const auto& watch = g_policy_field_watches[watch_index];
                        log_selector_root_compact_snapshot("policy_write_commit", watch.phase.c_str(), watch.selector_root);
                    }
                }
                {
                    const CallerSelection sel = capture_relevant_caller();
                    log_backtrace_selection(0, sel, "policy_write_commit", "policy_write");
                }
                log_backtrace_frames("policy_write_commit", 0, 12);
                for (auto& watch : g_policy_field_watches)
                {
                    watch.active = false;
                    watch.armed = false;
                }
                log_line("policy_write_watch_complete reason=first_change_detected");
            }
            else
            {
                arm_policy_field_pages_locked();
            }

            g_tls_policy_write_trace = PendingPolicyWriteTrace {};
        }

        if (chain_post_fallthrough)
        {
            begin_step_trace_locked(
                GetCurrentThreadId(),
                "xanim_resolver_post_fallthrough_flow",
                chained_trace_id,
                chained_path,
                ctx.Eip,
                kXanimPostFallthroughStepTraceInstructions);
            log_line("branch_trace_request kind=xanim_resolver_post_fallthrough_flow start=0x%08lX steps=%d trace=%llu path=%s",
                ctx.Eip,
                kXanimPostFallthroughStepTraceInstructions,
                chained_trace_id,
                chained_path.c_str());
            keep_tracing = true;
        }

        if (g_tls_rearm_addr)
        {
            auto it = g_exec_traces.find(g_tls_rearm_addr);
            if (it != g_exec_traces.end() && it->second.hits < it->second.max_hits)
            {
                patch_byte(it->second.addr, 0xCC, nullptr);
                it->second.armed = true;
            }
            g_tls_rearm_addr = 0;
        }
        if (keep_tracing)
            ctx.EFlags |= 0x100u;
        else
            ctx.EFlags &= ~0x100u;
        g_tls_in_veh = false;
        return EXCEPTION_CONTINUE_EXECUTION;
    }

    if (code == EXCEPTION_ACCESS_VIOLATION)
    {
        g_tls_in_veh = true;
        const uintptr_t fault_addr = static_cast<uintptr_t>(info->ExceptionRecord->ExceptionInformation[1]);
        unsigned long fault_rva = 0;
        const char* fault_module = module_name_for_addr(ctx.Eip, &fault_rva);
        log_line(
            "access_violation eip=0x%08lX module=%s%s%08lX faultAddr=0x%08lX",
            ctx.Eip,
            fault_module,
            std::strcmp(fault_module, "<unknown>") ? " rva=0x" : "",
            fault_rva,
            static_cast<unsigned long>(fault_addr));
        log_register_block(ctx);
        log_bytes_around("access_violation_eip", ctx.Eip, 16, 32);
        log_pointer_info("access_violation_fault", fault_addr);
        log_pointer_info("access_violation_eax", ctx.Eax);
        log_pointer_info("access_violation_esi", ctx.Esi);
        log_pointer_info("access_violation_edi", ctx.Edi);
        log_backtrace_frames("access_violation", 0, 16);
        log_stack_string_candidates(ctx, 16);
        g_tls_in_veh = false;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

DWORD WINAPI init_thread(void*)
{
    GetSystemInfo(&g_system_info);
    g_main_module = GetModuleHandleW(nullptr);
    g_main_base = reinterpret_cast<uintptr_t>(g_main_module);

    const std::string log_path = module_relative_path(L"fx_runtime_probe.log");
    g_log_file = std::fopen(log_path.c_str(), "wb");
    if (!g_log_file)
        return 0;

    log_line("fx_runtime_probe loaded pid=%lu build=%s", GetCurrentProcessId(), PROBE_BUILD_ID);
    char self_path[MAX_PATH] {};
    GetModuleFileNameA(g_self, self_path, MAX_PATH);
    log_line("probe_module=%s", self_path);
    char main_path[MAX_PATH] {};
    GetModuleFileNameA(g_main_module, main_path, MAX_PATH);
    log_line("main_module=%s base=0x%08lX", main_path, static_cast<unsigned long>(g_main_base));
    log_line("system_page_size=0x%08lX", static_cast<unsigned long>(g_system_info.dwPageSize));

    enumerate_modules();
    load_probe_mode();
    load_entry_wrapper_override();
    load_producer_compact_override();
    const bool bootstrap_guard_only = g_probe_mode == ProbeMode::BootstrapGuardOnly;
    const bool minimal_consumer_focus = is_minimal_consumer_focus_mode();
    const bool render_only_focus = is_render_only_focus_mode();
    const bool enable_touch_watchers = !bootstrap_guard_only && !minimal_consumer_focus && !render_only_focus;
    if (enable_touch_watchers)
    {
        seed_guard_message_watch();
        load_watchlist();
        {
            std::lock_guard<std::mutex> lock(g_state_mutex);
            seed_direct_custom_map_guard_touch();
        }
        arm_touch_trace_pages();
        load_xanim_expectations();
        load_xanim_runtime_patches();
    }
    else if (render_only_focus)
    {
        log_line("render_only_focus_init enabled");
        load_watchlist();
        load_xanim_expectations();
    }
    else if (minimal_consumer_focus)
    {
        log_line("consumer_focus_minimal_init enabled");
    }
    else
    {
        log_line("bootstrap_guard_only mode active");
    }

    g_real_create_file_a = reinterpret_cast<decltype(g_real_create_file_a)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "CreateFileA"));
    g_real_create_file_w = reinterpret_cast<decltype(g_real_create_file_w)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "CreateFileW"));
    g_real_read_file = reinterpret_cast<decltype(g_real_read_file)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "ReadFile"));
    g_real_close_handle = reinterpret_cast<decltype(g_real_close_handle)>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "CloseHandle"));
    g_return_trace_thunk = reinterpret_cast<void*>(&return_trace_thunk);

    AddVectoredExceptionHandler(1, probe_veh);
    if (!apply_bootstrap_hash_null_guard() &&
        (g_probe_mode == ProbeMode::BootstrapGuardOnly || g_probe_mode == ProbeMode::XanimFocus))
    {
        HANDLE retry_thread = CreateThread(nullptr, 0, bootstrap_hash_null_guard_retry_thread, nullptr, 0, nullptr);
        if (retry_thread)
        {
            log_line("bootstrap_hash_null_guard_retry_thread_started");
            CloseHandle(retry_thread);
        }
    }
    if (enable_touch_watchers)
    {
        install_file_hooks();
        log_line("guard_watches=disabled");
        HANDLE touch_thread = CreateThread(nullptr, 0, touch_trace_thread, nullptr, 0, nullptr);
        if (touch_thread)
        {
            log_line("touch_trace_thread_started");
            CloseHandle(touch_thread);
        }
        else
        {
            log_line("touch_trace_thread_failed gle=%lu", GetLastError());
        }
        HANDLE late_touch_thread = CreateThread(nullptr, 0, late_touch_rescan_thread, nullptr, 0, nullptr);
        if (late_touch_thread)
        {
            log_line("late_touch_rescan_thread_started");
            CloseHandle(late_touch_thread);
        }
        else
        {
            log_line("late_touch_rescan_thread_failed gle=%lu", GetLastError());
        }
        HANDLE guard_copy_thread = CreateThread(nullptr, 0, guard_copy_scan_thread, nullptr, 0, nullptr);
        if (guard_copy_thread)
        {
            log_line("guard_copy_scan_thread_started");
            CloseHandle(guard_copy_thread);
        }
        else
        {
            log_line("guard_copy_scan_thread_failed gle=%lu", GetLastError());
        }
    }
    else if (render_only_focus)
    {
        log_line("file_hooks_skipped mode=%s reason=render_only_focus", probe_mode_name());
    }
    else if (minimal_consumer_focus)
    {
        log_line("file_hooks_skipped mode=%s reason=minimal_consumer_focus", probe_mode_name());
    }
    else
    {
        log_line("file_hooks_skipped mode=%s", probe_mode_name());
    }
    if (g_probe_mode == ProbeMode::BootstrapGuardOnly)
    {
        log_line("consumer_arm_thread_skipped mode=%s reason=minimal_guard_only", probe_mode_name());
    }
    else if (is_render_only_focus_mode())
    {
        log_line("consumer_arm_thread_skipped mode=%s reason=asset_gated", probe_mode_name());
        HANDLE opacity_thread = CreateThread(nullptr, 0, opacity_focus_fallback_thread, nullptr, 0, nullptr);
        if (opacity_thread)
        {
            log_line("opacity_focus_fallback_thread_started");
            CloseHandle(opacity_thread);
        }
        else
        {
            log_line("opacity_focus_fallback_thread_failed gle=%lu", GetLastError());
        }
    }
    else if (g_probe_mode == ProbeMode::XanimFocus)
    {
        HANDLE consumer_thread = CreateThread(nullptr, 0, consumer_arm_thread, nullptr, 0, nullptr);
        if (consumer_thread)
        {
            log_line("consumer_arm_thread_started mode=%s reason=supplement_xanim_focus", probe_mode_name());
            CloseHandle(consumer_thread);
        }
        else
        {
            log_line("consumer_arm_thread_failed mode=%s reason=supplement_xanim_focus gle=%lu", probe_mode_name(), GetLastError());
        }
        if (!g_xanim_asset_census_started.exchange(true))
        {
            HANDLE census_thread = CreateThread(nullptr, 0, xanim_asset_census_thread, nullptr, 0, nullptr);
            if (census_thread)
            {
                log_line("xanim_asset_census_thread_created source=init");
                CloseHandle(census_thread);
            }
            else
            {
                g_xanim_asset_census_started = false;
                log_line("xanim_asset_census_thread_failed source=init gle=%lu", GetLastError());
            }
        }
        HANDLE xanim_arm_thread = CreateThread(nullptr, 0, xanim_focus_arm_thread, nullptr, 0, nullptr);
        if (xanim_arm_thread)
        {
            log_line("xanim_focus_arm_thread_started");
            CloseHandle(xanim_arm_thread);
        }
        else
        {
            log_line("xanim_focus_arm_thread_failed gle=%lu", GetLastError());
        }
    }
    else if (is_minimal_consumer_focus_mode())
    {
        if (g_probe_mode == ProbeMode::ClassFamilyMaterializationWritepath &&
            !g_selector_root_temporal_started.exchange(true))
        {
            HANDLE temporal_thread = CreateThread(nullptr, 0, selector_root_temporal_thread, nullptr, 0, nullptr);
            if (temporal_thread)
            {
                log_line("selector_root_temporal_thread_created");
                CloseHandle(temporal_thread);
            }
            else
            {
                g_selector_root_temporal_started = false;
                log_line("selector_root_temporal_thread_failed gle=%lu", GetLastError());
            }
        }
        HANDLE consumer_thread = CreateThread(nullptr, 0, consumer_arm_thread, nullptr, 0, nullptr);
        if (consumer_thread)
        {
            log_line("consumer_arm_thread_started mode=%s reason=consumer_focus", probe_mode_name());
            CloseHandle(consumer_thread);
        }
        else
        {
            log_line("consumer_arm_thread_failed mode=%s reason=consumer_focus gle=%lu", probe_mode_name(), GetLastError());
        }
    }
    else
    {
        HANDLE consumer_thread = CreateThread(nullptr, 0, consumer_arm_thread, nullptr, 0, nullptr);
        if (consumer_thread)
        {
            log_line("consumer_arm_thread_started");
            CloseHandle(consumer_thread);
        }
        else
        {
            log_line("consumer_arm_thread_failed gle=%lu", GetLastError());
        }
    }
    log_line("hook_install_complete installed=0");
    return 0;
}

} // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        g_self = module;
        DisableThreadLibraryCalls(module);
        HANDLE thread = CreateThread(nullptr, 0, init_thread, nullptr, 0, nullptr);
        if (thread)
            CloseHandle(thread);
    }
    return TRUE;
}
