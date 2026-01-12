# 6. Core Workflows

## Workflow 1: File Load → First Trigger → Baseline

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │DataInput │     │ AppState │     │  Core    │
│          │     │   Tab    │     │          │     │ Engines  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ Select File    │                │                │
     │───────────────▶│                │                │
     │                │                │                │
     │                │ Check Cache    │                │
     │                │───────────────▶│                │
     │                │                │ get_cached()   │
     │                │                │───────────────▶│
     │                │◀───────────────│                │
     │                │ Cache Miss     │                │
     │                │                │                │
     │                │ Load File      │                │
     │                │───────────────▶│                │
     │                │                │ FileLoader     │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │ raw_df         │
     │                │                │                │
     │                │ Auto-detect    │                │
     │                │ Columns        │                │
     │                │───────────────▶│                │
     │                │                │ ColumnMapper   │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │◀───────────────│ mapping        │
     │                │                │                │
     │ [If mapping    │                │                │
     │  incomplete]   │                │                │
     │◀───────────────│                │                │
     │ Show Config    │                │                │
     │ Panel          │                │                │
     │───────────────▶│                │                │
     │ Complete       │                │                │
     │ Mapping        │                │                │
     │                │                │                │
     │                │ Apply First    │                │
     │                │ Trigger        │                │
     │                │───────────────▶│                │
     │                │                │ FirstTrigger   │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │ baseline_df    │
     │                │                │                │
     │                │ Calculate      │                │
     │                │ Metrics        │                │
     │                │───────────────▶│                │
     │                │                │ Metrics        │
     │                │                │ Calculator     │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │ Emit Signals   │                │
     │                │                │                │
     │                │  data_loaded ──┼───────────────▶│
     │                │  baseline_calculated ──────────▶│
     │                │                │                │
     │ Display        │                │                │
     │ Baseline       │                │                │
     │◀───────────────│                │                │
     │                │                │                │
     ▼                ▼                ▼                ▼

Performance: < 3 seconds for 100k rows (NFR1)
```

## Workflow 2: Filter Apply → Metrics Update

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Feature  │     │ AppState │     │  Core    │
│          │     │ Explorer │     │          │     │ Engines  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ Add Filter     │                │                │
     │───────────────▶│                │                │
     │                │                │                │
     │                │ Validate       │                │
     │                │ Criteria       │                │
     │                │───────────────▶│                │
     │                │                │ FilterEngine   │
     │                │                │ .validate()    │
     │                │◀───────────────│                │
     │                │                │                │
     │ [If invalid]   │                │                │
     │◀───────────────│                │                │
     │ Show Error     │                │                │
     │                │                │                │
     │ Click Apply    │                │                │
     │───────────────▶│                │                │
     │                │                │                │
     │                │ apply_filter() │                │
     │                │───────────────▶│                │
     │                │                │                │
     │                │                │ Take Snapshot  │
     │                │                │ (for rollback) │
     │                │                │                │
     │                │                │ FilterEngine   │
     │                │                │ .apply()       │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │ filtered_df    │
     │                │                │                │
     │                │                │ [If FT toggle] │
     │                │                │ FirstTrigger   │
     │                │                │ .apply()       │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │                │ Calculate      │
     │                │                │ Filtered       │
     │                │                │ Metrics        │
     │                │                │───────────────▶│
     │                │                │◀───────────────│
     │                │                │                │
     │                │ Emit Signals   │                │
     │                │                │                │
     │                │  filters_changed ─────────────▶│
     │                │  filtered_data_updated ───────▶│
     │                │  metrics_updated ─────────────▶│
     │                │                │                │
     │ Update Chart   │                │                │
     │ Update Count   │                │                │
     │◀───────────────│                │                │
     │                │                │                │
     ▼                ▼                ▼                ▼

Performance: < 500ms (NFR2)
```

## Workflow 3: First-Trigger Toggle

```
User toggles switch
       │
       ▼
┌─────────────┐    first_trigger_toggled(bool)    ┌─────────────┐
│   Feature   │ ─────────────────────────────────▶│  AppState   │
│  Explorer   │                                   └──────┬──────┘
└─────────────┘                                          │
                                                         │
                              ┌───────────────────────────┤
                              │                           │
                              ▼                           ▼
                   [If enabled]                  [If disabled]
                   Apply FirstTrigger            Return raw filtered
                   to filtered_df                 │
                              │                   │
                              ▼                   ▼
                        filtered_data_updated + metrics_updated
                              │
                              ▼
                   Update chart + row count

Performance: < 200ms
```

## Workflow 4: Export

```
User clicks Export
       │
       ▼
┌─────────────┐    Show save dialog    ┌─────────────┐
│   Tab       │ ──────────────────────▶│    OS       │
└─────────────┘                        └──────┬──────┘
                                              │
                                    User selects path
                                              │
       ┌──────────────────────────────────────┘
       │
       ▼
┌─────────────┐    export()    ┌─────────────┐
│   Tab       │ ──────────────▶│ExportManager│
└─────────────┘                └──────┬──────┘
                                      │
                               [Try write]
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
        [Success]               [Permission]            [Disk Full]
        Show Toast              Show Error              Show Error
        (success)               Toast                   Toast
```

## Workflow 5: Window State Restore

```
Application Launch
       │
       ▼
┌─────────────┐    Load window_state.json    ┌─────────────┐
│ MainWindow  │ ────────────────────────────▶│   Cache     │
└─────────────┘                              └──────┬──────┘
                                                    │
                              ┌─────────────────────┤
                              │                     │
                              ▼                     ▼
                    [State exists]          [No state / Error]
                              │                     │
                              ▼                     ▼
                    Validate position       Use defaults
                    (on-screen check)       (centered, 1280x720)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        [Valid]         [Off-screen]    [Maximized]
        Restore         Reset to        Restore
        position        center          maximized
```

---
