# Project 02 research protocol

**Status:** Data intake only. No analysis or causal design has been approved by this scaffold.

## Questions to resolve before building the panel

- Define the outcome: origin outflows, destination inflows, or another measure; specify how missing reports and zero reports differ.
- Verify the unit, period, administrative boundary vintage, and crosswalk before any spatial join. Preserve source coordinates and source administrative labels in derived metadata.
- Specify which ACLED event types and geographic precision levels count as exposure, how dates are assigned to months, and how reporting bias is assessed.
- Verify whether price observations represent the same commodity, unit, currency, market, and collection method over time.
- Define the climate anomaly baseline and raster aggregation rule. Record coverage and missing grid cells for each district-month.
- Treat transfer presence and placement as potentially endogenous. Do not present descriptive patterns as treatment effects.
- Predefine missingness checks, source disagreements, sensitivity analyses, and disclosure limits before interpreting results.

## Decision log

Record each substantive decision with date, author, evidence, alternatives considered, and affected outputs. Keep rejected or revised specifications visible rather than silently replacing them. Add preregistration or a dated analysis plan if confirmatory claims are pursued.

## Verification states

Mark results explicitly as **proposed**, **source-verified**, **fixture-tested**, **run on acquired data**, or **independently reproduced**. A checksum alone establishes byte identity, not validity of the source, join, measurement, or inference.
