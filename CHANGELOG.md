# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Stats-Only Mode**: Added `--stats-only` command-line argument which runs pure statistics collection without pushing configuration exports or fetching SSH backups.
- **OSPF Map Generation**: Generates an interactive HTML map visualizing the entire OSPF network structure based on parsed areas, routers, links, and interfaces, automatically appending it to `results/stats/ospf_map_<date>.html`.
- **Parallel OSPF Collection**: OSPF logic is now queried directly inside the parallel execution thread alongside general interface/neighbor logic.
- **Individual Stat Files**: Refactored the core saving module to store individual `[component]-info.json` files for system, interfaces, neighbors, IPs, PPPoE Active, Schedulers, and OSPF instead of clumping them into one gigantic file.

### Changed
- **Unified Export Directory Structure**: Files such as `.backup` and `.rsc` are now placed directly in `results/backups/[IDENTITY]` rather than nesting redundantly in `results/backups/[IDENTITY]/backups`.
- **Global Markdown Export**: Consolidated Markdown summary for OSPF data is automatically timestamped for clean historic logging.
- **Map Visualizations**: Links on the interactive OSPF HTML map now display IP addresses along the edges instead of crowding the node titles.
- **Simplified OSPF Output**: Cleaned up excessive OSPF console terminal outputs into progress updates and a single end-of-run summary.

### Removed
- **PPPoE Secrets Extraction**: Complete removal of `pppoe_secrets` (`/ppp/secret`) querying logic for data privacy.
- **--ospf-export Command**: Replaced entirely by the faster, more flexible parallel `--stats-only` mode.
