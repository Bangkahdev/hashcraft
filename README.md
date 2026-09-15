# HashCraft (`osint-hash`)

A local-first, deterministic CLI tool designed to generate candidate strings from user-supplied keywords and verify their UTF-8 SHA-256 digests locally. 

Built for authorized security research, password auditing, CTFs, and cryptographic education.

---

## Authorized Use Only

**Disclaimer:** Use of this tool is strictly limited to systems, applications, and hashes that you own, or for which you have explicit, documented authorization to test. This tool is intended for use in CTFs, laboratory work, lawful security research, and permitted penetration testing.

* **One-Way Function Notice:** SHA-256 is a one-way cryptographic hash function. A failed verification means only that none of the generated candidates matched the supplied digest; it does not establish that an original plaintext does not exist.
* **Privacy:** This application operates **entirely locally**. It contains zero telemetry, analytics, remote candidate submission, external API requirements, credential collection, online authentication attempts, or automated scraping.

---

## Installation

Ensure you have **Python 3.10+** installed, then clone the repository and install the package locally:

```bash
git clone https://github.com/Bangkahdev/hashcraft.git
cd hashcraft
pip install .

```

---

## Usage

### 1. Generate Candidates

Generate candidates from names, cities, and years with a maximum word combination depth of 3:

```bash
osint-hash generate --names atha,bangkah --cities lhokseumawe \
  --years 2025,2026 --max-words 3 --output wordlist.txt

```

### 2. Verify Hashes (Piped Pipeline)

Stream generated candidates directly into the local verifier:

```bash
osint-hash generate --names atha --stdout | \
  osint-hash verify --algorithm sha256 --hash <64-hex-digest> --stdin

```

### 3. Dry Run & Preflight Estimation

Check the filter-aware candidate count and resource limits without writing files:

```bash
osint-hash generate --keywords atha,bangkah --leet --symbols --dry-run

```

---

## License

Distributed under the **MIT License**. See `LICENSE` for more information.
