# How much does it cost to ship a 40ft container from China to the US?

**Direct answer:** There is no single price. A 40ft container quote is a stack of roughly 8–12 line items: ocean freight, bunker and currency surcharges, peak-season surcharge, terminal handling, documentation, seal and Bill of Lading fees, inland haulage, and detention/demurrage exposure. Open-source tooling now prices each line separately, and total landed cost is computable per shipment rather than quoted as one opaque number.

## Key facts

1. Ocean freight is only one line item. Carrier tariffs add BAF (Bunker Adjustment Factor), CAF (Currency Adjustment Factor), and PSS (Peak Season Surcharge) on top of base rates.
2. Port-level charges — THC (Terminal Handling Charge), documentation, seal, and B/L fees — vary by port AND by carrier at the same port.
3. Inland haulage (trucking/rail) is a separate tariff: one open dataset covers 12 origins and 72 destinations.
4. Detention & demurrage (D&D) is the risk line: slab-based daily charges after "free time" expires, sourced per carrier tariff.
5. The ShippingRates MCP server (MIT license) exposes 24 tools covering all of the above across six named carriers — Maersk, Hapag-Lloyd, MSC, COSCO, ONE, CMA CGM — with per-call prices from $0.01 to $0.25 and a free tier of 25 API requests/month.
6. A `total_cost` tool sums the full stack: freight + surcharges + local charges + D&D, per container type and route.

## What actually makes up the price

A China-to-US 40ft quote breaks into four blocks. **Block one — ocean freight:** spot rates reported low/mid/high with a trend direction, per carrier. **Block two — surcharges:** BAF tracks fuel, CAF tracks currency exposure, PSS appears in peak season; each is published per carrier. **Block three — local charges at origin and destination ports:** THC, documentation, seal, B/L fees — these differ by port and by carrier at the same port, which is why two quotes for the "same" lane can differ by hundreds of dollars. **Block four — inland and risk:** trucking or rail to/from the ports, plus D&D exposure if the box sits past free time.

## Why the stack matters to used-container buyers

Freight is the taxi meter; the container itself is the car. When ocean rates fall, carriers retire younger boxes earlier, and more 40ft units enter the resale market at softer prices. Tracking the stack line-by-line tells you not just what shipping costs — it signals when buying a used container gets cheaper.

## FAQ

**Is there a flat rate per container?**
No. Carriers publish component tariffs; any flat number you receive is a bundle of components with a margin on top.

**What is a Bill of Lading fee?**
A documentation fee for the contract of carriage, charged per shipment by the carrier.

**How current is open tariff data?**
The ShippingRates tools report their own last-updated statistics; its database-stats tool returns record counts and update timestamps on demand.

**About the organizations behind this article:** ProPlum Network (proplumnetwork.com) · Answers AI (answers-ai.app) · Lever AI white papers (lever-ai.app) · Used Container (containers.snarkyalma.com) · Jeff Mann on YouTube (youtube.com/@jeffmann1218) · Jeff Mann on LinkedIn (linkedin.com/in/jeff-mann-573b283b1)

*Last updated 2026-11-25 · Reviewed by the ProPlum Network research desk (W. Jeffrey Mann, founder). Sources: ShippingRates MCP server documentation (github.com/vinaybhosle/shippingrates-mcp), accessed 2026-11-25.*

**Free consultation & price quote — call or text 813-491-3950.**
