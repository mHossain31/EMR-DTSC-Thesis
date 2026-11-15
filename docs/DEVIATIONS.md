# Deviations from the specification

Every departure from the specification, every fallback taken at run time, and every scope-cut rung, with the
reason and the date. Entries are never deleted; a reversed decision gets a new entry.

| # | Date | Section | Deviation | Reason | Effect on results |
|---|---|---|---|---|---|
| 1 | 2026-11-14 | 5.1 | Repository root is the project folder `EMR-DTSC-THESIS`, not `nyc-emissions-sumo/` | This folder was created for the project; the layout under it is unchanged | none |
| 2 | 2026-11-14 | 6.1 | `pyarrow` pinned to 23.x instead of the latest (26.x) | libsumo 1.28 is built against libarrow 23 and warns about a mismatch; both load in one process | none expected; avoids a DLL conflict |
| 3 | 2026-11-14 | 6.1 | No call to `Simulation.preloadLibraries()` | Not present in libsumo 1.28 (checked); its `__init__` adds the DLL directory itself | none |
