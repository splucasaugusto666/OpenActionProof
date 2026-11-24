# Evidence protocol (development)

Run the demonstration locally to generate JSON receipts at evidence/generated/. This directory is gitignored because each receipt has a timestamp and checksum.

Receipts are locally reproducible structurally but NOT bit-identical because timestamps differ. Never treat receipts as signed, independently attested, or proof of third-party-agent execution.
