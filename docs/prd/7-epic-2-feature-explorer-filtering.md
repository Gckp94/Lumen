# 7. Epic 2: Feature Explorer & Filtering

## Epic Goal

Enable interactive data exploration with bounds-based filtering, filtered first-trigger logic, and GPU-accelerated charting. Upon completion, users can select columns to analyze, apply range filters, toggle between raw and first-trigger views, and see instant visual feedback.

## Stories

### Story 2.1: Feature Explorer Layout & Basic Chart

**As a** user,
**I want** to see my data visualized by column,
**so that** I can explore patterns and distributions.

**Acceptance Criteria:**

1. Tab layout: left sidebar (25%), main chart area (75%), bottom bar
2. Column selector dropdown with all numeric columns
3. PyQtGraph scatter plot showing selected column values
4. Chart styled with Observatory theme (space-dark background, plasma-cyan points)
5. Chart renders baseline first-trigger data by default
6. Bottom bar: "Showing {n:,} data points"
7. Chart updates < 200ms on column change
8. Handles 83k+ points without lag

---

### Story 2.2: Bounds Filtering

**As a** user,
**I want** to filter data by value ranges,
**so that** I can focus on specific subsets of my trades.

**Acceptance Criteria:**

1. "Add Filter" button with filter row (column, operator, min, max, remove)
2. Operators: "between", "not between"
3. Filter validation (min ≤ max, numeric values)
4. "Apply Filters" updates chart and row count
5. Applied filters shown as styled chips (nova-amber)
6. "Clear All Filters" resets to baseline
7. Filter applied in < 500ms for 100k rows

---

### Story 2.3: First-Trigger Toggle

**As a** user,
**I want** to apply first-trigger logic to my filtered data,
**so that** I see only the first qualifying signal per ticker-date.

**Acceptance Criteria:**

1. "First Trigger Only" toggle switch in filter controls
2. Toggle ON: apply filtered first trigger algorithm, show first trigger count
3. Toggle OFF: show all rows matching filters
4. Chart updates immediately on toggle (< 200ms)
5. Visual indicator when toggle ON (stellar-blue highlight)
6. Edge cases handled (no matches, no first triggers)

---

### Story 2.4: Filtered Data Export (Validation Checkpoint)

**As a** user,
**I want** to export my filtered dataset,
**so that** I can validate results and continue analysis elsewhere.

**Acceptance Criteria:**

1. "Export Filtered Data" button in bottom bar
2. Save dialog with suggested filename
3. Export all columns, only filtered rows, CSV format
4. Include metadata comment with filter summary
5. Success toast notification
6. Export completes in < 2 seconds for 100k rows

---

### Story 2.5: Multi-Filter Logic & Date Range

**As a** user,
**I want** to combine multiple filters and restrict by date,
**so that** I can test complex hypotheses.

**Acceptance Criteria:**

1. Support up to 10 simultaneous filters with AND logic
2. No duplicate columns (replace existing)
3. Active filters displayed as chips with remove button
4. Date range filter: start/end date pickers, "All Dates" checkbox
5. Filter summary in bottom bar
6. Filter chain applied in < 500ms for 100k rows

---

### Story 2.6: Interactive Chart Controls

**As a** user,
**I want** to pan, zoom, and inspect my chart,
**so that** I can examine data points in detail.

**Acceptance Criteria:**

1. Scroll wheel zoom, left-click drag pan, right-click drag zoom selection
2. Double-click to reset view
3. Crosshair with coordinate display (moon-gray dashed lines)
4. Axis controls: Y/X min/max inputs, "Auto Fit" button
5. "Show Grid" toggle
6. Pan/zoom at 60fps for 83k points

---

## Epic 2 Definition of Done

- [ ] Feature Explorer tab displays interactive scatter chart
- [ ] User can select any numeric column to visualize
- [ ] Bounds filters (BETWEEN/NOT BETWEEN) work correctly
- [ ] First-trigger toggle switches between all matches and first triggers only
- [ ] Export confirms filter results match expectations
- [ ] Multiple filters combine with AND logic
- [ ] Date range filter restricts data by date
- [ ] Chart supports pan, zoom, and crosshair inspection
- [ ] All operations complete in < 500ms for 100k rows

---
