<p align="center">
  <img src="assets/banner.png" alt="OffensIA" width="100%">
</p>

# OffensIA

[![CI](https://github.com/borbollanetwork/OffensIA/actions/workflows/ci.yml/badge.svg)](https://github.com/borbollanetwork/OffensIA/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[Português](#português) · [English](#english)

## Português

**Plataforma model-agnostic de orchestration para offensive security, orientada
por evidências e destinada a pentests autorizados. Scope is law (`default-deny`),
findings protegidos por evidence gates e uma validation state machine, além de um
audit ledger encadeado por hash — safety enforced in code, not prompts. MCP-native
para Kimi e GLM. Criada por Renato Borbolla.**

O OffensIA transforma uma metodologia disciplinada de offensive security em uma
plataforma governada e model-agnostic, operada por um LLM (Kimi / GLM) por meio de
uma única interface MCP. O projeto é construído sobre três garantias aplicadas em
código, não por prompt:

1. **Scope is law** — `default-deny`; nada é executado contra um target que não
   esteja explicitamente autorizado.
2. **Evidence over assertion** — um finding só é confirmado por meio de um
   validation lifecycle sustentado por artifacts reais; o modelo nunca pode
   autodeclarar impacto.
3. **Auditability** — um ledger `append-only` e `hash-chained` registra cada ação;
   o operador cita referências, nunca a memória do modelo.

O OffensIA não é um "scanner + resumo por LLM". A inteligência está em planning,
adaptive testing, coverage control, evidence correlation, validation e eliminação
de false positives. As ferramentas funcionam como sensores e atuadores.

> **Somente para uso autorizado.** O OffensIA aplica o scope, mas não concede
> autorização. Use-o apenas contra sistemas para os quais você possui autorização
> de teste.

### Arquitetura

Três planos deliberadamente desacoplados:

- **Control plane** — scope, policy, estado da assessment, coverage, capability
  registry, providers e knowledge retrieval (`offensia/core`,
  `offensia/providers`, `offensia/knowledge`).
- **Execution plane** — o MCP gateway e os adapters que acessam tool engines
  externos por trás de uma interface neutra de capabilities
  (`offensia/core/server.py`, `offensia/adapters`).
- **Evidence plane** — ledger `hash-chained`, evidence store content-addressed,
  finding state machine, attack graph e reporting (`offensia/core/ledger.py`,
  `evidence.py`, `finding.py`, `attack_graph.py`, `offensia/reporting`).

Engines externos são consumidos como **dependencies** declaradas em
`deps/engines.yaml` e acessados somente por meio de adapters — nunca são vendored
neste repositório.

### Instalação com um comando

```bash
git clone https://github.com/borbollanetwork/OffensIA
cd OffensIA
./install.sh kimi          # ou: ./install.sh glm
```

O installer executa o preflight → cria uma `venv` → instala o package → provisiona
os engines a partir do manifest com versões fixadas → registra o servidor MCP do
OffensIA na configuração do agent, com backup, atomic write e
`abort-on-malformed` → executa health check e self-test. Depois, basta iniciar o
agent: as ferramentas `offensia_*` estarão disponíveis.

### Configuração

- **Kimi / GLM:** os presets ficam em `offensia/presets/kimi/` e
  `offensia/presets/glm/` (configuração MCP + hardened system prompt). Os model
  identifiers são configuráveis por `OFFENSIA_MODEL_ID` / `KIMI_MODEL_ID` /
  `GLM_MODEL_ID` — o OffensIA nunca inventa um identifier. Consulte `.env.example`.
- **Registro manual do MCP:**
  `offensia agent register --agent-config <caminho>`; desfaça com
  `offensia agent unregister --agent-config <caminho>`.

### Uso

```bash
offensia scope add app.authorized.example --auth CONTRACT-2026-001  # autorize primeiro
offensia assessment create eng-42
# ...conduza o engagement pelo seu LLM agent usando as ferramentas offensia_*...
offensia coverage show eng-42
offensia ledger verify eng-42
offensia report technical eng-42
offensia resume eng-42            # estado retomável
offensia knowledge index ./doctrine
offensia doctor                   # diagnósticos acionáveis
```

### Ligar e desligar

Depois de instalado, controle o OffensIA com dois scripts:

```bash
./start.sh              # liga: sobe a engine stack (Docker/pip) + health check
./start.sh --reference  # liga usando o reference engine (sem Docker/dependências)
./stop.sh               # desliga: encerra as engines e o reference engine
```

Equivalentes via CLI: `offensia engines up`, `offensia engines status`,
`offensia engines down`. O `start.sh` é idempotente e, se nenhuma engine do
manifesto responder, sobe o reference engine como fallback.

#### Como funciona a evidence validation

Um finding começa em um estado não confirmatório, ancorado a um `evidence_id`
armazenado. `offensia_validate_finding` executa checks de reproduction e
negative control pelo execution adapter protegido pelo scope. A promoção para
`VALIDATED` / `EXPLOITABLE` / `CONFIRMED_IMPACT` é aplicada em código com base nos
checks que realmente passaram — o modelo não pode promover um finding apenas por
afirmá-lo.

### Extensão

- **Adicionar um adapter:** implemente um módulo em
  `offensia/adapters/<classe>/` que exponha as capability functions; depois,
  associe sua `PROVIDER_KEY` no capability registry.
- **Adicionar um provider:** crie uma subclasse de `BaseModelProvider` em
  `offensia/providers/` com seu `ProviderMetadata`; mantenha a metodologia de
  offensive security fora do código do provider.

### Documentação

Consulte `docs/` — architecture, installation, configuration, providers, MCP,
scope, evidence, validation, coverage, knowledge, threat model e development.

### Status

Primeiro build orientado a produção. O autonomous engagement engine foi adiado
para um milestone posterior; sua interface já existe por meio do capability
registry. Consulte `docs/LIMITATIONS.md` para distinguir o que está totalmente
implementado do que ainda é apenas interface.

### Autor e créditos

Criado por **Renato Borbolla** — https://renatoborbolla.com

Se você melhorar, clonar ou criar um fork deste projeto, atribua os devidos
créditos ao autor, Renato Borbolla, mantendo esta atribuição e um link para
https://renatoborbolla.com em sua cópia ou trabalho derivado.

---

## English

**Evidence-driven, model-agnostic offensive-security orchestration platform for
authorized pentests. Scope-is-law (default-deny), evidence-gated findings with a
validation state machine, and a hash-chained audit ledger — safety enforced in
code, not prompts. MCP-native for Kimi & GLM. Created by Renato Borbolla.**

OffensIA turns a disciplined offensive-security methodology into a governed,
model-agnostic platform an LLM operator (Kimi / GLM) drives through a single MCP
interface. It is built around three guarantees enforced in code, not by prompt:

1. **Scope is law** — default-deny; nothing runs against a target that is not
   explicitly authorized.
2. **Evidence over assertion** — a finding is confirmed only through a validation
   lifecycle backed by real artifacts; the model can never self-declare impact.
3. **Auditability** — an append-only, hash-chained ledger records every action; the
   operator cites references, never model memory.

OffensIA is not a "scanner + LLM summary." The intelligence lives in planning,
adaptive testing, coverage control, evidence correlation, validation, and
false-positive elimination. Tools are sensors and actuators.

> **Authorized use only.** OffensIA enforces scope; it does not grant permission.
> Use it only against systems you are authorized to test.

### Architecture

Three planes, deliberately decoupled:

- **Control plane** — scope, policy, assessment state, coverage, capability
  registry, providers, knowledge retrieval (`offensia/core`, `offensia/providers`,
  `offensia/knowledge`).
- **Execution plane** — the MCP gateway and adapters that reach external tool
  engines behind a neutral capability interface (`offensia/core/server.py`,
  `offensia/adapters`).
- **Evidence plane** — hash-chained ledger, content-addressed evidence store,
  finding state machine, attack graph, reporting (`offensia/core/ledger.py`,
  `evidence.py`, `finding.py`, `attack_graph.py`, `offensia/reporting`).

External engines are consumed as **dependencies** declared in `deps/engines.yaml`
and reached only through adapters — never vendored into this repository.

### Install (one command)

```bash
git clone https://github.com/borbollanetwork/OffensIA
cd OffensIA
./install.sh kimi          # or: ./install.sh glm
```

The installer runs preflight → creates a venv → installs the package → provisions
the engines from the pinned manifest → registers the OffensIA MCP server into your
agent config (with backup, atomic write, and abort-on-malformed) → runs health and
self-test. Then start your agent — the `offensia_*` tools are available.

### Configure

- **Kimi / GLM:** presets live in `offensia/presets/kimi/` and `offensia/presets/glm/`
  (MCP config + hardened system prompt). Model identifiers are configurable via
  `OFFENSIA_MODEL_ID` / `KIMI_MODEL_ID` / `GLM_MODEL_ID` — OffensIA never invents an
  identifier. See `.env.example`.
- **Register MCP manually:** `offensia agent register --agent-config <path>`
  (undo with `offensia agent unregister --agent-config <path>`).

### Use

```bash
offensia scope add app.authorized.example --auth CONTRACT-2026-001  # authorize first
offensia assessment create eng-42
# ...drive the engagement from your LLM agent via offensia_* tools...
offensia coverage show eng-42
offensia ledger verify eng-42
offensia report technical eng-42
offensia resume eng-42            # resumable state
offensia knowledge index ./doctrine
offensia doctor                   # actionable diagnostics
```

### Start and stop

Once installed, control OffensIA with two scripts:

```bash
./start.sh              # start: bring the engine stack up (Docker/pip) + health check
./start.sh --reference  # start using the dependency-free reference engine
./stop.sh               # stop: shut down engines and the reference engine
```

CLI equivalents: `offensia engines up`, `offensia engines status`,
`offensia engines down`. `start.sh` is idempotent and, if no manifest engine
answers, brings up the reference engine as a fallback.

#### How evidence validation works
A finding starts in a non-confirming state anchored to a stored `evidence_id`.
`offensia_validate_finding` runs reproduction and negative-control checks through
the scope-guarded execution adapter. Promotion to `VALIDATED` / `EXPLOITABLE` /
`CONFIRMED_IMPACT` is code-enforced from the checks that actually pass — the model
cannot promote a finding by asserting it.

### Extending

- **Add an adapter:** implement a module under `offensia/adapters/<class>/` exposing
  the capability functions, then bind its `PROVIDER_KEY` in the capability registry.
- **Add a provider:** subclass `BaseModelProvider` in `offensia/providers/` with its
  `ProviderMetadata`; keep offensive methodology out of provider code.

### Documentation

See `docs/` — architecture, installation, configuration, providers, MCP, scope,
evidence, validation, coverage, knowledge, threat model, development.

### Status

First production-oriented build. The autonomous engagement engine is deferred to a
later milestone; its interface exists via the capability registry. See
`docs/LIMITATIONS.md` for what is fully implemented versus interface-only.

### Author & Credits

Created by **Renato Borbolla** — https://renatoborbolla.com

If you improve, clone, or fork this project, please give due credit to the author
(Renato Borbolla), keeping this attribution and a link to https://renatoborbolla.com
in your copy or derivative work.
