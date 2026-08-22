# Historical cricket data

CricEdge uses the official Cricsheet JSON format as the canonical historical
match source for the first model.

The downloader targets the official T20 archive. Raw archives belong outside
Git; use `download_t20_archive()` during data preparation and keep generated
archives in a local ignored data directory.

The parser reads a ZIP archive lazily and can inspect the first match without
loading the full corpus into memory.

See `schema_report.md` for the first schema inspection and the decisions that
follow from it.
