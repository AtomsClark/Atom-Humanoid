# Humanoid Robot Startup — Business Case

## Vision

Build the first consumer humanoid robot designed around the owner, not the cloud.
Privacy, quality, and ecosystem — the Apple of home robotics.

---

## Market Positioning

Every other robotics company is building surveillance infrastructure that happens to move.
A robot in your home sees your family, your routines, your home layout, your conversations.
The data hunger of Figure, 1X, and Amazon's Astro is a real vulnerability that nobody is attacking.

**The gap:** All serious humanoid competitors are building expensive robots ($150k+) for industrial use.
The consumer market is wide open.

**The wedge:** "The robot that works for you, not for us."

Apple proved that privacy can be a premium product feature people pay for — not just a regulatory checkbox.

---

## Competitive Landscape

| Company | Focus | Est. Price | Status |
|---|---|---|---|
| Figure AI | Industrial (BMW) | $150k+ | ~$700M raised |
| Agility Robotics (Digit) | Warehouse (Amazon) | $150k+ | Acquired by Amazon |
| Apptronik (Apollo) | Industrial (Google) | $150k+ | Series A |
| 1X Technologies | Home (early) | TBD | OpenAI backed |
| Tesla Optimus | TBD | TBD | Long-term threat |
| Unitree H1 | Research / industrial | ~$90k | Chinese, scaling fast |

No credible privacy-first consumer humanoid robot exists. The field is wide open at this level.

---

## Business Model

### Hardware — Sell Outright

Customers own their robot. No mandatory subscription, no data ransom.

| Phase | Price Target | Timeline |
|---|---|---|
| Developer Edition | $20,000 | Year 1–2 |
| Early Adopter | $15,000 | Year 2–3 |
| Mass Market | $8,000–12,000 | Year 4+ |

Hardware gross margin target: **35–45%** (Apple-like, not commodity).

### Software — Optional Subscription

| Tier | Price/month | What You Get |
|---|---|---|
| **Base** | Free | On-device AI, core capabilities, full offline operation |
| **Connected** | ~$30–50 | Cloud-enhanced AI, OTA updates, new skills |
| **Family** | ~$80 | Multi-robot, enhanced home integration, priority support |

Opting out of Connected means the robot stays capable but static — no new skills, no cloud features.
A fair and honest trade.

### Ecosystem — Long-Term Revenue

- **Skill store** — third-party developers build capabilities, 15–30% revenue share
- **Hardware accessories** — end effectors, charging docks, add-ons
- **Developer SDK / API** — paid tiers for commercial developers

---

## Privacy Architecture

To credibly hold the Apple position this must be technically real, not marketing.

- **On-device inference** for all sensitive processing — home layout, face recognition, audio
- **Federated learning** — model improves from user behavior, but only gradient updates leave the device, never raw data
- **Opt-in data sharing with tangible reward** — users who share get free Connected tier or credits. Purely voluntary, clearly explained
- **Local-first** — robot functions fully offline. Cloud enhances but never gatekeeps
- **No third-party data sales, ever** — founding charter commitment
- **Open audit** — publish transparency reports, invite security researchers

This isn't just ethics — it's a moat. It is very hard for a company that built its culture around data extraction to credibly reverse course.

---

## Solving the Data Problem Without Coercion

The privacy stance creates a data challenge. Mitigation strategies:

| Method | Description |
|---|---|
| **Internal test fleet** | 50–100 robots in employee and beta user homes, fully consented |
| **Teleoperation corpus** | Humans operate robots remotely — every session is labeled training data |
| **Simulation** | Isaac Sim / MuJoCo generates massive synthetic datasets, real-world fine-tuned on top |
| **Incentivized sharing** | Opt-in users get free Connected subscription — many will say yes willingly |
| **Research partnerships** | CMU, Stanford, MIT have manipulation datasets and simulation environments |
| **Federated learning** | Aggregate model improvements from opted-in users without accessing raw data |

Physical Intelligence (Pi) has built impressive manipulation capabilities largely through teleoperation and sim-to-real, without coercive data collection. This is a solvable problem.

---

## Go-To-Market

Follow the Tesla Roadster / early iPhone playbook. Don't launch to everyone — launch to believers.

### Phase 1: Developer Edition (Year 1–2)
- 500–1,000 units at $20,000
- Sell to robotics enthusiasts, hackers, researchers, content creators
- Open SDK from day one — build community
- These users tolerate rough edges and provide invaluable feedback
- Their content markets the next tier for free

### Phase 2: Early Adopter (Year 2–3)
- 5,000–20,000 units at $15,000
- Waitlist creates demand signal and press coverage
- One or two killer use cases polished to near-perfection (laundry, dishes, fetch tasks)
- Underpromise, overdeliver — do not oversell general capability

### Phase 3: Mass Market (Year 4+)
- Price at $8,000–12,000
- Broad direct-to-consumer and retail
- Full skill ecosystem established
- Financing / lease-to-own option available (unit is still sold, just financed)

---

## Path to Profitability

| Phase | Timeline | Milestone | Revenue |
|---|---|---|---|
| **Prototype** | Year 1 | Working robot, core use cases | Grants, pre-seed |
| **Developer launch** | Year 2 | 500–1,000 units shipped | ~$10M |
| **Early adopter** | Year 3–4 | 10,000+ units, ecosystem growing | ~$50M ARR |
| **Scale** | Year 4–5 | Price drops, software margin grows | ~$150M ARR |
| **Profitable** | Year 6–8 | Hardware cost down, services ~30% of revenue | Profitable |

Hardware gross margins start at 35%. Software/ecosystem margins reach 60–70%.
The business becomes compelling when services revenue grows alongside the installed base.

---

## Funding Strategy

### Pre-Seed ($500k–$2M)
- Angels with hardware or consumer tech background
- Y Combinator — strong credibility signal, robotics-friendly
- Non-dilutive grants:
  - NSF SBIR Phase I: ~$275k
  - NSF SBIR Phase II: ~$2M

### Seed ($10–20M)
Target hardware-fluent funds with long time horizons:
- Lux Capital
- Playground Global
- Khosla Ventures
- DCVC

### Series A ($40–80M)
- Once 500–1,000 Developer Edition units are deployed and data/community is growing
- Consumer-focused funds become attractive: Forerunner, Benchmark
- Strategic angels: ex-Apple hardware executives add credibility and connections

### Framing for Investors
Frame as a **platform company**, not a hardware company.
Hardware companies get 1–3× revenue multiples. Platform companies get 10–20×.
The robot is the iPhone. The real business is the ecosystem.

---

## Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Consumer support costs at scale | Robust hardware design, Apple-style support infrastructure |
| Home liability exposure | Strong e-stop, geofenced safe modes, consumer liability insurance partnerships |
| $15–20k is a high bar | Financing options, waitlist demand signal, developer edition creates aspiration |
| Data disadvantage vs. coercive competitors | Federated learning + teleoperation + sim-to-real closes the gap |
| Tesla Optimus long-term | Be 5 years ahead in consumer UX, privacy, and ecosystem before they arrive |

---

## One-Line Pitch

*"We're building the first humanoid robot designed around the owner — not the cloud — bringing the privacy, quality, and ecosystem of Apple to the home robotics category."*
